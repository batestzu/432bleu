/**
 * T1 driver: N avatar bots connect to the prod pusher and walk circles in the lab map.
 *
 *   BOTS=150 RAMP_MS=1000 DURATION_S=600 npm run t1
 *
 * Env: BOTS (10) | RAMP_MS between joins (500) | DURATION_S (300)
 *      PLAY_URL (https://play.432bleu.com) | ROOM_ID (lab test map) | TEXTURE (male1)
 *
 * Bots join the LAB room only — never point ROOM_ID at concert.json during a show.
 * Exit code 0 = >=95% of bots connected and stayed connected.
 */
import WebSocket from "ws";
import {
    ClientToServerMessage,
    ServerToClientMessage,
    PositionMessage_Direction,
    AvailabilityStatus,
    apiVersionHash,
} from "@workadventure/messages";

const PLAY_URL = process.env.PLAY_URL ?? "https://play.432bleu.com";
const ROOM_ID = process.env.ROOM_ID ?? `${PLAY_URL}/_/global/maps.432bleu.com/lab/test-map.json`;
const BOTS = parseInt(process.env.BOTS ?? "10", 10);
const RAMP_MS = parseInt(process.env.RAMP_MS ?? "500", 10);
const DURATION_S = parseInt(process.env.DURATION_S ?? "300", 10);
const TEXTURE = process.env.TEXTURE ?? "male1";

// lab map is 40x30 tiles of 32px; walk a circle around the center
const CX = 640, CY = 480, R = 300;

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

function wsUrl(n: number, x: number, y: number): string {
    const u = new URL("ws/room", PLAY_URL);
    u.protocol = u.protocol.replace("http", "ws");
    const p = u.searchParams;
    p.set("roomId", ROOM_ID);
    p.set("name", `LOADTEST-${n}`);
    p.append("characterTextureIds", TEXTURE);
    p.set("x", String(x));
    p.set("y", String(y));
    p.set("top", String(y - 300));
    p.set("bottom", String(y + 300));
    p.set("left", String(x - 480));
    p.set("right", String(x + 480));
    p.set("availabilityStatus", String(AvailabilityStatus.ONLINE));
    p.set("version", apiVersionHash);
    p.set("chatID", "");
    p.set("roomName", "");
    p.set("cameraState", "false");
    p.set("microphoneState", "false");
    p.set("screenSharingState", "false");
    p.set("tabId", `loadtest-${n}-${Date.now()}`);
    return u.toString();
}

function moveMsg(x: number, y: number): Uint8Array {
    return ClientToServerMessage.encode({
        message: {
            $case: "userMovesMessage",
            userMovesMessage: {
                position: { x, y, direction: PositionMessage_Direction.DOWN, moving: true },
                viewport: { left: x - 480, top: y - 300, right: x + 480, bottom: y + 300 },
            },
        },
    }).finish();
}

async function startBot(n: number, token: string | null): Promise<void> {
    let angle = (n / BOTS) * Math.PI * 2;
    const x0 = Math.floor(CX + R * Math.sin(angle));
    const y0 = Math.floor(CY + R * Math.cos(angle));
    const ws = new WebSocket(wsUrl(n, x0, y0), token ? [token] : undefined);
    ws.binaryType = "arraybuffer";
    sockets.push(ws);
    let alive = false;

    ws.on("open", () => {
        stats.connected++;
        alive = true;
        const timer = setInterval(() => {
            if (ws.readyState !== WebSocket.OPEN) { clearInterval(timer); return; }
            angle += 0.05;
            const x = Math.floor(CX + R * Math.sin(angle));
            const y = Math.floor(CY + R * Math.cos(angle));
            ws.send(moveMsg(x, y));
            stats.movesSent++;
        }, 200);
    });
    ws.on("message", (data: ArrayBuffer) => {
        stats.msgsIn++;
        try {
            const msg = ServerToClientMessage.decode(new Uint8Array(data));
            const kind = msg.message?.$case;
            if (kind === "roomJoinedMessage") stats.joined++;
            if (kind === "errorMessage") console.error(`bot ${n}: server error`, JSON.stringify(msg.message));
        } catch { /* non-fatal decode noise */ }
    });
    ws.on("error", (e) => { if (!alive) stats.failed++; console.error(`bot ${n}: ${e.message}`); });
    ws.on("close", (code) => { if (alive && !shuttingDown) { stats.dropped++; console.error(`bot ${n}: dropped (code ${code})`); } });
}

let shuttingDown = false;
(async () => {
    console.log(`T1: ${BOTS} bots -> ${ROOM_ID} (ramp ${RAMP_MS}ms, ${DURATION_S}s)`);
    const token = await anonymLogin();
    console.log(token ? "anonymLogin ok" : "anonymLogin unavailable — connecting without token");

    for (let i = 0; i < BOTS; i++) {
        void startBot(i, token);
        await new Promise((r) => setTimeout(r, RAMP_MS));
    }
    const report = setInterval(() => {
        console.log(
            `[${new Date().toISOString().slice(11, 19)}] connected=${stats.connected}/${BOTS} joined=${stats.joined} ` +
            `failed=${stats.failed} dropped=${stats.dropped} msgsIn=${stats.msgsIn} movesSent=${stats.movesSent}`
        );
    }, 5000);

    await new Promise((r) => setTimeout(r, DURATION_S * 1000));
    shuttingDown = true;
    clearInterval(report);
    for (const ws of sockets) { try { ws.close(); } catch { /* already closed */ } }
    await new Promise((r) => setTimeout(r, 2000));

    const ok = stats.connected - stats.dropped;
    console.log(`\nRESULT: stayed=${ok}/${BOTS} failed=${stats.failed} dropped=${stats.dropped} msgsIn=${stats.msgsIn}`);
    const pass = ok >= BOTS * 0.95;
    console.log(pass ? "T1 PASS" : "T1 FAIL (need >=95% connected & stable)");
    process.exit(pass ? 0 : 1);
})();
