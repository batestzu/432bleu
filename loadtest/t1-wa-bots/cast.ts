/**
 * Cast driver: a room full of plausible-looking people, for screenshots and video.
 *
 *   BOTS=32 DURATION_S=900 MAP_TMJ=./concert.tmj npm run cast
 *
 * This is a FORK of bot.ts, not a replacement. bot.ts is the calibrated T1 instrument and
 * its numbers are reproducible; leave it alone. The differences here are all cosmetic —
 * the wire protocol is identical:
 *
 *   - each bot gets a name and its own composed WOKA instead of LOADTEST-n in male1
 *   - bots stand on walkable tiles read out of concert.tmj, clustered toward the stage
 *   - idle bots send one moving:false instead of going silent (silence leaves the last
 *     moving:true on screen forever, and the avatar moonwalks in place)
 *   - idle bots face the stage
 *
 * Env: BOTS (32) | RAMP_MS (1500) | DURATION_S (900) | SEED (1) | PLAY_URL | ROOM_ID
 *      MAP_TMJ (unset)  — path to a concert.tmj copy; without it, placement is collision-blind
 *      CROWD_X/CROWD_Y/SPREAD — where the crowd gathers, in px
 *      STATIONARY ("18,6 22,6 19,2 13,6") — EXTRA bots that never move, at these TILE pairs.
 *        Exempt from the row band, so they may stand on the stage side. "" places none.
 *      MIN_TILE_Y/MAX_TILE_Y (11/29) — confine the cast to these TILE rows, any column. Default is
 *        the audience floor: concert.tmj rows 9-10 are the wall under the stage, row 29 the bottom
 *        wall. Keep CROWD_Y inside the band.
 *      API_VERSION — override if a play rebuild changes the hash
 *
 * ⚠ Bots reach /ws/room, which is OUTSIDE the Caddy ticket matcher — the gate will not stop
 *   you pointing this at a live show. Off-hours only. Confirm the room is empty afterwards.
 */
import fs from "fs";
import WebSocket from "ws";
import {
    ClientToServerMessage,
    ServerToClientMessage,
    PositionMessage_Direction,
    AvailabilityStatus,
    apiVersionHash,
} from "@workadventure/messages";

const PLAY_URL = process.env.PLAY_URL ?? "https://play.432bleu.com";
const ROOM_ID = process.env.ROOM_ID ?? `${PLAY_URL}/~/concert.wam`;
const BOTS = parseInt(process.env.BOTS ?? "32", 10);
const RAMP_MS = parseInt(process.env.RAMP_MS ?? "1500", 10);
const DURATION_S = parseInt(process.env.DURATION_S ?? "900", 10);
const SEED = parseInt(process.env.SEED ?? "1", 10);
const MAP_TMJ = process.env.MAP_TMJ;

// See the note in bot.ts: the checked-in hash is "dev"; images bake the real one in at build
// time. Verified still current 2026-09-05 against bundle index-CtjJtiXT.js. Re-derive after a
// play rebuild:  curl .../assets/index-<hash>.js | grep -oE '"[0-9a-f]{8}"'
const API_VERSION = process.env.API_VERSION ?? (apiVersionHash === "dev" ? "17672b86" : apiVersionHash);

// concert.wam geometry, in px. The speakerMegaphone area is the stage — leave it empty for the
// performer; the crowd gathers in front of it and thins out toward the back of the room.
const STAGE = { x: 303, y: 46, w: 79, h: 54 };
const STAGE_CX = STAGE.x + STAGE.w / 2;
const STAGE_CY = STAGE.y + STAGE.h / 2;
const CROWD_X = parseFloat(process.env.CROWD_X ?? String(STAGE_CX));
// Default is row 12 (py 400), just inside the audience floor nearest the stage, so the gaussian
// falls off backwards across the floor. It MUST sit inside [MIN_TILE_Y, MAX_TILE_Y] — a centre
// outside the band makes every bot pile against the band's nearest edge.
const CROWD_Y = parseFloat(process.env.CROWD_Y ?? "400");
const SPREAD = parseFloat(process.env.SPREAD ?? "220");

// Fallback bounds when no map is supplied — concert.tmj is 40x30 @32px, same as the lab map.
const MAP_W = 1280, MAP_H = 960, MARGIN = 120;

// Confine the cast to the audience floor, in TILE rows (inclusive), any column.
// concert.tmj rows 9-10 are a solid wall dividing the stage side (rows 1-8) from the floor,
// and row 29 is the bottom wall — so 11..29 is "everything below the divider". Row 29 has zero
// walkable tiles and drops out via the collision filter anyway; it is kept as the bound so the
// range reads as the whole floor.
const MIN_TILE_Y = parseInt(process.env.MIN_TILE_Y ?? "11", 10);
const MAX_TILE_Y = parseInt(process.env.MAX_TILE_Y ?? "29", 10);
const TILE_W = 32, TILE_H = 32;
const BAND_TOP_PX = MIN_TILE_Y * TILE_H;               // inclusive upper edge
const BAND_BOTTOM_PX = (MAX_TILE_Y + 1) * TILE_H;      // exclusive lower edge
function inBand(y: number): boolean {
    return y >= BAND_TOP_PX && y < BAND_BOTTOM_PX;
}

/**
 * Fixed bots that never move — the band above does not apply to them, so they can stand on the
 * stage side of the wall. Space-separated TILE pairs, "x,y"; set STATIONARY="" to place none.
 * These are EXTRA, on top of BOTS.
 */
const STATIONARY_KEEPALIVE_S = 15;
function parseStationary(spec: string): [number, number][] {
    return spec.split(/[\s;]+/).filter(Boolean).map((pair) => {
        const m = /^(\d+),(\d+)$/.exec(pair);
        if (!m) {
            console.error(`STATIONARY: cannot parse "${pair}" — expected tile pairs like "18,6"`);
            process.exit(1);
        }
        return [
            parseInt(m[1], 10) * TILE_W + TILE_W / 2,
            parseInt(m[2], 10) * TILE_H + TILE_H / 2,
        ] as [number, number];
    });
}
const STATIONARY = parseStationary(process.env.STATIONARY ?? "18,6 22,6 19,2 13,6");
const TOTAL = BOTS + STATIONARY.length;

const WALK_PERIOD_S = 20, WALK_DUTY_S = 4;
const ORBIT_R = 26;

/** Plainly fictional. Never seed this from the mailing list — these names are visible in-room. */
const NAMES = [
    "Ada", "Bo", "Cleo", "Dez", "Eli", "Fern", "Gus", "Hana", "Ines", "Jonah",
    "Kit", "Lena", "Milo", "Nadia", "Omar", "Pia", "Quinn", "Rosa", "Sam", "Tovah",
    "Uma", "Vic", "Wren", "Xochitl", "Yuri", "Zeke", "Bex", "Cass", "Dov", "Edda",
    "Flo", "Gil", "Hex", "Ira", "Jubi", "Kai", "Lux", "Moss", "Nix", "Otto",
];

function mulberry(seed: number): () => number {
    return () => {
        seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
        let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

// ---------------------------------------------------------------- wardrobe

type WokaJson = Record<string, { required?: boolean; collections: { textures: { id: string }[] }[] }>;

let wokaIds: Record<string, string[]> = {};
try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const woka: WokaJson = require("../../play/src/pusher/data/woka.json");
    for (const [part, def] of Object.entries(woka)) {
        wokaIds[part] = def.collections.flatMap((c) => c.textures).map((t) => t.id);
    }
} catch (e) {
    console.error(`could not load woka.json (${e}) — falling back to the stock male1 skin`);
    wokaIds = {};
}

/**
 * body, eyes and accessory are flagged required in woka.json, so always include them.
 * hair and clothes carry most of the visual variety; hat is occasional.
 * Layered textures and the 24 stock "woka" skins are alternatives — don't mix the two.
 */
function look(rand: () => number): string[] {
    const pick = (part: string): string | null => {
        const ids = wokaIds[part];
        return ids?.length ? ids[Math.floor(rand() * ids.length)] : null;
    };
    const layers = ["body", "eyes", "hair", "clothes", "accessory"]
        .map(pick)
        .filter((id): id is string => id !== null);
    if (layers.length < 3) return ["male1"];          // woka.json missing — stock skin
    const hat = rand() < 0.35 ? pick("hat") : null;
    if (hat) layers.push(hat);
    return layers;
}

// ---------------------------------------------------------------- placement

/**
 * Read the collision layers out of concert.tmj so nobody stands inside the bar or the PA
 * stacks. The map has BOTH "collisions" and "Collisions" — match case-insensitively, and
 * treat any non-zero gid as blocked. The server does not validate movement, so this is the
 * only thing keeping the cast out of the walls.
 */
function walkableTiles(path: string): [number, number][] {
    const tmj = JSON.parse(fs.readFileSync(path, "utf8"));
    const tw: number = tmj.tilewidth ?? 32, th: number = tmj.tileheight ?? 32;
    const blocked = new Set<number>();
    for (const layer of tmj.layers ?? []) {
        if (!/^collisions$/i.test(layer.name ?? "") || !Array.isArray(layer.data)) continue;
        layer.data.forEach((gid: number, i: number) => { if (gid !== 0) blocked.add(i); });
    }
    const out: [number, number][] = [];
    for (let i = 0; i < tmj.width * tmj.height; i++) {
        if (blocked.has(i)) continue;
        out.push([(i % tmj.width) * tw + tw / 2, Math.floor(i / tmj.width) * th + th / 2]);
    }
    return out;
}

/** Crowd density falls off with distance from the gathering point — dense at the front, stragglers at the back. */
function weightAt(x: number, y: number): number {
    const dx = x - CROWD_X, dy = y - CROWD_Y;
    return Math.exp(-(dx * dx + dy * dy) / (2 * SPREAD * SPREAD));
}

function insideStage(x: number, y: number): boolean {
    return x >= STAGE.x - 16 && x <= STAGE.x + STAGE.w + 16
        && y >= STAGE.y - 16 && y <= STAGE.y + STAGE.h + 16;
}

let anchorPool: [number, number][] | null = null;
let walkableSet: Set<string> | null = null;
if (MAP_TMJ) {
    const all = walkableTiles(MAP_TMJ);
    walkableSet = new Set(all.map(([x, y]) => `${x},${y}`));
    const tiles = all.filter(([x, y]) => !insideStage(x, y) && inBand(y));
    anchorPool = tiles;
    console.log(`placement: ${tiles.length} walkable tiles from ${MAP_TMJ}, stage excluded, rows ${MIN_TILE_Y}-${MAX_TILE_Y} only`);
    if (tiles.length === 0) {
        console.error(`placement: NO walkable tiles in rows ${MIN_TILE_Y}-${MAX_TILE_Y} — check MIN_TILE_Y/MAX_TILE_Y against the map.`);
        process.exit(1);
    }
} else {
    console.warn("placement: MAP_TMJ not set — collision-blind, bots may stand in walls.");
    console.warn("           scp root@432bleu.com:/home/vspot/workadventure/map-storage/public/concert.tmj .");
}

// A fixed position is a deliberate choice, so a collision is a warning rather than a hard stop —
// but it is worth saying out loud, because the server does not validate movement and the bot will
// simply stand inside whatever is there.
if (STATIONARY.length) {
    const where = STATIONARY.map(([x, y]) => `(${(x - TILE_W / 2) / TILE_W},${(y - TILE_H / 2) / TILE_H})`).join(" ");
    console.log(`stationary: ${STATIONARY.length} fixed bot(s) at tiles ${where} — exempt from the row band`);
    if (walkableSet) {
        for (const [x, y] of STATIONARY) {
            if (!walkableSet.has(`${x},${y}`)) {
                console.warn(`stationary: ⚠ tile (${(x - TILE_W / 2) / TILE_W},${(y - TILE_H / 2) / TILE_H}) is a COLLISION tile — that bot will stand inside scenery`);
            }
        }
    }
}

/** Rejection-sample the gathering point so the crowd clusters without ever leaving the floor. */
function anchorFor(rand: () => number): [number, number] {
    for (let attempt = 0; attempt < 240; attempt++) {
        const [x, y] = anchorPool
            ? anchorPool[Math.floor(rand() * anchorPool.length)]
            : [MARGIN + rand() * (MAP_W - 2 * MARGIN), BAND_TOP_PX + rand() * (BAND_BOTTOM_PX - BAND_TOP_PX)];
        if (rand() < weightAt(x, y)) return [Math.floor(x), Math.floor(y)];
    }
    // Dense centre, if sampling gets unlucky — clamped into the band so an out-of-band CROWD_Y
    // can never park a bot on the stage side of the wall.
    const cy = Math.min(Math.max(CROWD_Y, BAND_TOP_PX), BAND_BOTTOM_PX - 1);
    return [Math.floor(CROWD_X), Math.floor(cy)];
}

/** Which way an idle bot looks: toward the stage, on whichever axis dominates. */
function facing(x: number, y: number): PositionMessage_Direction {
    const dx = STAGE_CX - x, dy = STAGE_CY - y;
    if (Math.abs(dy) >= Math.abs(dx)) {
        return dy < 0 ? PositionMessage_Direction.UP : PositionMessage_Direction.DOWN;
    }
    return dx < 0 ? PositionMessage_Direction.LEFT : PositionMessage_Direction.RIGHT;
}

function isWalking(n: number): boolean {
    return (Date.now() / 1000 + n * 1.7) % WALK_PERIOD_S < WALK_DUTY_S;
}

// ---------------------------------------------------------------- wire

const stats = { connected: 0, joined: 0, failed: 0, dropped: 0, msgsIn: 0, movesSent: 0 };
const sockets: WebSocket[] = [];

async function anonymLogin(): Promise<string | null> {
    try {
        const res = await fetch(`${PLAY_URL}/anonymLogin`, { method: "POST" });
        if (!res.ok) return null;
        const data: any = await res.json();
        return data?.authToken ?? null;
    } catch {
        return null;
    }
}

function wsUrl(n: number, name: string, textures: string[], x: number, y: number): string {
    const u = new URL("ws/room", PLAY_URL);
    u.protocol = u.protocol.replace("http", "ws");
    const p = u.searchParams;
    p.set("roomId", ROOM_ID);
    p.set("name", name);
    for (const id of textures) p.append("characterTextureIds", id);   // repeated = layered WOKA
    p.set("x", String(x));
    p.set("y", String(y));
    p.set("top", String(y - 300));
    p.set("bottom", String(y + 300));
    p.set("left", String(x - 480));
    p.set("right", String(x + 480));
    p.set("availabilityStatus", String(AvailabilityStatus.ONLINE));
    p.set("version", API_VERSION);
    p.set("chatID", "");
    p.set("roomName", "");
    p.set("cameraState", "false");        // no media: the cast forms proximity groups but
    p.set("microphoneState", "false");    // opens no LiveKit tracks
    p.set("screenSharingState", "false");
    p.set("tabId", `cast-${n}-${Date.now()}`);
    return u.toString();
}

function moveMsg(x: number, y: number, direction: PositionMessage_Direction, moving: boolean): Uint8Array {
    return ClientToServerMessage.encode({
        message: {
            $case: "userMovesMessage",
            userMovesMessage: {
                position: { x, y, direction, moving },
                viewport: { left: x - 480, top: y - 300, right: x + 480, bottom: y + 300 },
            },
        },
    }).finish();
}

async function startBot(n: number, token: string | null, fixed?: [number, number]): Promise<void> {
    const rand = mulberry(SEED * 7919 + n + 1);
    const name = NAMES[n % NAMES.length] + (n >= NAMES.length ? String(Math.floor(n / NAMES.length) + 1) : "");
    const textures = look(rand);
    const [ax, ay] = fixed ?? anchorFor(rand);
    const rest = facing(ax, ay);

    let angle = rand() * Math.PI * 2;
    const ws = new WebSocket(wsUrl(n, name, textures, ax, ay), token ? [token] : undefined);
    ws.binaryType = "arraybuffer";
    sockets.push(ws);
    let alive = false;
    let wasWalking = true;   // force one moving:false on the first idle tick

    ws.on("open", () => {
        stats.connected++;
        alive = true;

        if (fixed) {
            // Never walks. One settled frame so every client renders it standing and facing the
            // stage, then the same frame on a slow keepalive — a socket that goes completely
            // silent for the whole session is a good way to get reaped by an idle timeout.
            const settle = () => {
                if (ws.readyState !== WebSocket.OPEN) return;
                ws.send(moveMsg(ax, ay, rest, false));
                stats.movesSent++;
            };
            setTimeout(settle, 500);
            const keep = setInterval(() => {
                if (ws.readyState !== WebSocket.OPEN) { clearInterval(keep); return; }
                settle();
            }, STATIONARY_KEEPALIVE_S * 1000);
            return;
        }

        const timer = setInterval(() => {
            if (ws.readyState !== WebSocket.OPEN) { clearInterval(timer); return; }
            const walking = isWalking(n);
            if (!walking) {
                // Going silent would leave the last moving:true on every other client, and the
                // avatar walks on the spot indefinitely. Send one settled frame instead.
                if (wasWalking) {
                    const x = Math.floor(ax + ORBIT_R * Math.sin(angle));
                    const y = Math.floor(ay + ORBIT_R * Math.cos(angle));
                    ws.send(moveMsg(x, y, rest, false));
                    stats.movesSent++;
                    wasWalking = false;
                }
                return;
            }
            wasWalking = true;
            angle += 0.15;
            const x = Math.floor(ax + ORBIT_R * Math.sin(angle));
            const y = Math.floor(ay + ORBIT_R * Math.cos(angle));
            ws.send(moveMsg(x, y, facing(x, y), true));
            stats.movesSent++;
        }, 200);
    });
    ws.on("message", (data: ArrayBuffer) => {
        stats.msgsIn++;
        try {
            const msg = ServerToClientMessage.decode(new Uint8Array(data));
            const kind = msg.message?.$case;
            if (kind === "roomJoinedMessage") stats.joined++;
            if (kind === "errorMessage") console.error(`${name}: server error`, JSON.stringify(msg.message));
        } catch (e) { if (process.env.DEBUG) console.error(`${name}: undecodable message: ${e}`); }
    });
    ws.on("error", (e) => { if (!alive) stats.failed++; console.error(`${name}: ${e.message}`); });
    ws.on("close", (code, reason) => {
        if (alive && !shuttingDown) {
            stats.dropped++;
            console.error(`${name}: dropped (code ${code}${reason?.length ? `, ${reason.toString()}` : ""})`);
        }
    });
}

let shuttingDown = false;
(async () => {
    console.log(`cast: ${BOTS} roaming + ${STATIONARY.length} stationary = ${TOTAL} -> ${ROOM_ID}`);
    console.log(`      ramp ${RAMP_MS}ms, ${DURATION_S}s, seed ${SEED}, crowd (${CROWD_X},${CROWD_Y}) spread ${SPREAD}`);
    if (!/\/~\//.test(ROOM_ID)) {
        console.warn(`      ⚠ ROOM_ID has no /~/ segment — map-storage rooms live under /~/. Is this the room you meant?`);
    }

    const token = await anonymLogin();
    console.log(token ? "anonymLogin ok" : "anonymLogin unavailable — connecting without token");

    for (let i = 0; i < BOTS; i++) {
        void startBot(i, token);
        await new Promise((r) => setTimeout(r, RAMP_MS));
    }
    for (let i = 0; i < STATIONARY.length; i++) {
        void startBot(BOTS + i, token, STATIONARY[i]);
        await new Promise((r) => setTimeout(r, RAMP_MS));
    }
    const report = setInterval(() => {
        console.log(
            `[${new Date().toISOString().slice(11, 19)}] connected=${stats.connected}/${TOTAL} ` +
            `joined=${stats.joined} failed=${stats.failed} dropped=${stats.dropped} moves=${stats.movesSent}`
        );
    }, 5000);

    await new Promise((r) => setTimeout(r, DURATION_S * 1000));
    shuttingDown = true;
    clearInterval(report);
    for (const ws of sockets) { try { ws.close(); } catch { /* already closed */ } }
    await new Promise((r) => setTimeout(r, 2000));

    console.log(`\ncast down: stayed=${stats.connected - stats.dropped}/${TOTAL} failed=${stats.failed} dropped=${stats.dropped}`);
    console.log("Reload the room and confirm the player list is empty before the next real show.");
    process.exit(0);
})();
