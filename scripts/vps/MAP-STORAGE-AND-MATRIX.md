# Map-storage + Matrix subdomain build-out

Written 2026-08-03. Prerequisite for the WA megaphone / speaker-zone feature.

Both jobs are the same shape — a WorkAdventure subsystem is still wired to an upstream **dev**
domain (`*.workadventure.localhost`) that does not resolve for real users. Doing them together
means one DNS pass, one Caddy pass, one cert pass, one stack restart.

All commands are written as **single lines** — this terminal mangles multi-line pastes.

---

## 0. Why this is required at all (the actual gate)

The megaphone is not blocked by a missing setting. It is blocked by the **room URL prefix**.

`play/src/pusher/services/LocalAdmin.ts:90-103`:

```js
const match = /\/~\/(.+)/.exec(roomUrl.pathname);
if (match && ENABLE_MAP_EDITOR && (MAP_EDITOR_ALLOW_ALL_USERS || MAP_EDITOR_ALLOWED_USERS.includes(userIdentifier) || tags?.includes("admin") || tags?.includes("editor"))) {
    canEdit = true;
}
```

The regex **requires** the path to start with `/~/`. Today the venue runs on
`/_/global/maps.432bleu.com/concert.json`, so `canEdit` is `false` no matter what any environment
variable says. `RoomConnection.ts:574` then does `mapEditorActivated.set(ENABLE_MAP_EDITOR && this.canEdit)`,
so the map-editor UI never appears.

And the audience half of the megaphone is WAM-gated two separate ways:

- **Listener zone** — `GameMapPropertiesListener.ts:772` resolves the speaker zone through
  `getGameMap().getWamFile()?.getGameMapAreas().getAreas()`. No WAM → `undefined` → silent no-op.
- **Global megaphone button** — `GameScene.ts:2228-2248` reads `getWamFile()?.getWam()?.settings`.
  No WAM → no button.

(The *speaker* half does fire on a plain Tiled map — `GameMapPropertiesListener.ts:499` is reached
via `onEnterLayer`/`onEnterTiledArea`. But a speaker broadcasting into a space nobody can join is
useless. Don't be misled by this into thinking a Tiled-only shortcut exists.)

**Therefore: `/~/` room + a WAM file + a reachable map-storage. No shortcuts.**

---

## 1. DNS

Add two A records pointing at the prod VPS (`5.78.195.138`):

- `mapstorage.432bleu.com`
- `matrix.432bleu.com`

Verify before touching anything else — this is the cheapest possible failure to catch early:

`dig +short mapstorage.432bleu.com matrix.432bleu.com`

Both must return `5.78.195.138`. Neither resolves today (verified 2026-08-02).

---

## 2. Caddy

The Caddyfile is **VPS-only and has never been committed** — hand-edited in place. Back it up first:

`sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak-$(date +%F)`

Traefik publishes `8080:80` (docker-compose.yaml:10) — host port **8080** → its `web` entryPoint.
That is where every non-Owncast host goes. (Owncast is the exception, proxied straight to `:8085`,
bypassing Traefik — which is why "Owncast up but everything else 502" diagnoses a Docker/Traefik
failure rather than a Caddy one.)

Add these two blocks. Match the surrounding style of the existing `play`/`maps`/`boxoffice` blocks
if it differs — in particular, reuse whatever `tls` / email directive is already in the file.

```
mapstorage.432bleu.com {
	encode zstd gzip

	reverse_proxy localhost:8080 {
		header_up Host {host}
		header_up X-Forwarded-Proto {scheme}
		header_up X-Forwarded-Host {host}
	}
}

matrix.432bleu.com {
	encode zstd gzip

	reverse_proxy localhost:8080 {
		header_up Host {host}
		header_up X-Forwarded-Proto {scheme}
		header_up X-Forwarded-Host {host}
	}
}
```

`header_up Host {host}` is the load-bearing line — **Traefik routes by Host header**, so the real
hostname must survive the hop. This is also why the Traefik router rules in §3a must be changed to
match the new hostnames; changing only Caddy gets you a 404 from Traefik.

No request-body size limit is needed. Caddy v2 and Traefik both default to unlimited, and the map
bundle is ~69 MB.

### The two-proxy X-Forwarded-Proto trap

`map-storage/src/index.ts:84` sets `app.set("trust proxy", true)`, so Express derives `req.protocol`
from `X-Forwarded-Proto`. But **Traefik does not trust inbound `X-Forwarded-*` by default** — with
an empty `forwardedHeaders.trustedIPs` it overwrites them from its own entryPoint, which is plain
`http`. So Caddy's `https` gets clobbered on the second hop.

Consequence: `UploadController.ts:221` builds the WAM URL as
`` `${req.protocol}://${req.hostname}...` `` and hands it to `back` over gRPC. It would come out as
`http://mapstorage.432bleu.com/...` while `PUBLIC_MAP_STORAGE_URL` is `https://...`. Not fatal —
the map still uploads and still loads, because `back` rewrites public→internal via
`fetchWamFile(wamUrl, INTERNAL_MAP_STORAGE_URL, ...)` (`GameRoom.ts:182`) — but the
"map was just re-uploaded, refresh live rooms" signal can fail to match, so edits appear only after
a manual reload.

Fix, in the Traefik `command:` block in docker-compose.yaml:

```
      - --entryPoints.web.forwardedHeaders.insecure=true
```

Safe here because Traefik is only reachable through Caddy — `8080:80` binds the host port, and
nothing external routes to it. Verify with a scheme check after deploy rather than assuming.

Reload and confirm certs issue:

`sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy`

`curl -sI https://mapstorage.432bleu.com/ping` — expect a 200 (that route is unauthenticated,
`map-storage/src/Upload/PingController.ts:9`).

**While you are in here, commit the Caddyfile.** Its absence from git has been a standing risk
since the region-scoping review. `sudo cp /etc/caddy/Caddyfile ~/workadventure/scripts/vps/Caddyfile`
and commit it, with any secrets stripped.

---

## 3. map-storage wiring

### 3a. docker-compose.yaml diff

```diff
@@ reverse-proxy, command:
       - --entryPoints.web.address=:80
       - --providers.docker.exposedbydefault=false
+      # Trust X-Forwarded-* from Caddy (see §2 — Traefik is not externally reachable)
+      - --entryPoints.web.forwardedHeaders.insecure=true

@@ play, environment (L80)
-      PUBLIC_MAP_STORAGE_URL: "http://map-storage.workadventure.localhost"
+      PUBLIC_MAP_STORAGE_URL: "https://mapstorage.432bleu.com"
       INTERNAL_MAP_STORAGE_URL: "http://map-storage:3000"

@@ play, environment (L148)
-      MAP_EDITOR_ALLOW_ALL_USERS: "false"
+      MAP_EDITOR_ALLOW_ALL_USERS: "false"
+      MAP_EDITOR_ALLOWED_USERS: "$MAP_EDITOR_ALLOWED_USERS"

@@ back, environment (L230)
-      PUBLIC_MAP_STORAGE_URL: "http://map-storage.workadventure.localhost"
+      PUBLIC_MAP_STORAGE_URL: "https://mapstorage.432bleu.com"
       INTERNAL_MAP_STORAGE_URL: "http://map-storage:3000"

@@ map-storage, labels (L285-292)
-      - "traefik.http.routers.map-storage.rule=Host(`map-storage.workadventure.localhost`)"
+      - "traefik.http.routers.map-storage.rule=Host(`mapstorage.432bleu.com`)"
       - "traefik.http.routers.map-storage.entryPoints=web"
       - "traefik.http.routers.map-storage.service=map-storage"
       - "traefik.http.services.map-storage.loadbalancer.server.port=3000"
-      - "traefik.http.routers.map-storage-ui.rule=Host(`map-storage.workadventure.localhost`) && PathPrefix(`/ui/`)"
+      - "traefik.http.routers.map-storage-ui.rule=Host(`mapstorage.432bleu.com`) && PathPrefix(`/ui/`)"

@@ synapse, labels (L493)
-      - "traefik.http.routers.matrix.rule=Host(`matrix.workadventure.localhost`)"
+      - "traefik.http.routers.matrix.rule=Host(`matrix.432bleu.com`)"

@@ synapse, volumes (L500)
-      - ./synapse/federation:/etc/nginx/vhost.d/matrix.workadventure.localhost
+      - ./synapse/federation:/etc/nginx/vhost.d/matrix.432bleu.com

@@ synapse, environment (L502-505)
-      VIRTUAL_HOST: "matrix.workadventure.localhost"
+      VIRTUAL_HOST: "matrix.432bleu.com"
       VIRTUAL_PORT: 8008
-      LETSENCRYPT_HOST: "matrix.workadventure.localhost"
-      SYNAPSE_SERVER_NAME: "matrix.workadventure.localhost"
+      LETSENCRYPT_HOST: "matrix.432bleu.com"
+      SYNAPSE_SERVER_NAME: "matrix.432bleu.com"

@@ play, environment (L141, L144)
-      MATRIX_PUBLIC_URI: http://matrix.workadventure.localhost
+      MATRIX_PUBLIC_URI: https://matrix.432bleu.com
       MATRIX_API_URI: http://synapse:8008/
-      MATRIX_DOMAIN: matrix.workadventure.localhost
+      MATRIX_DOMAIN: matrix.432bleu.com
```

Plus two files outside compose:

```diff
@@ synapse/homeserver.template.yaml:12-13
-server_name: "matrix.workadventure.localhost"
-public_baseurl: http://matrix.workadventure.localhost/
+server_name: "matrix.432bleu.com"
+public_baseurl: https://matrix.432bleu.com/
```

`git mv synapse/matrix.workadventure.localhost.log.config synapse/matrix.432bleu.com.log.config`
— the filename encodes the domain. Check `synapse/start.sh` for a reference to it before renaming.

**Notes on the diff:**

- `PUBLIC_MAP_STORAGE_URL` and `MATRIX_PUBLIC_URI` **must be https**. Both are fetched by the
  *browser* on an https page. Leaving either `http://` reproduces exactly the mixed-content failure
  that makes Matrix unusable today.
- `INTERNAL_MAP_STORAGE_URL` and `MATRIX_API_URI` are container-to-container — leave them `http`.
- **The `networks.default.aliases` list at L24-32 does NOT need editing.** It is a Docker network
  alias list, not an allowed-hosts list, and it contains no `*.432bleu.com` entry today — the prod
  stack works without them. `back` never resolves the public hostname: `GameRoom.ts:182` rewrites
  public→internal before fetching. (An earlier note called L30/L32 "allowed hosts"; that was wrong.)
- `MAP_EDITOR_ALLOWED_USERS` is added because it is currently **not passed through at all** — see §3c.

### 3b. VPS .env

These are all blank in `.env.template` (L193-197) and must be filled with real values:

- `MAP_STORAGE_AUTH_USER`
- `MAP_STORAGE_AUTH_PASSWORD`
- `MAP_STORAGE_AUTH_TOKEN`
- `MAP_STORAGE_API_TOKEN`

Generate each with `openssl rand -hex 32`, same as the existing secrets pattern.

Also confirm `ENABLE_MAP_EDITOR` — template default is `true` (L135) but the VPS `.env` has never
been read from a Claude session:

`grep ENABLE_MAP_EDITOR ~/workadventure/.env`

### 3c. Edit permission — one gotcha

`MAP_EDITOR_ALLOWED_USERS` exists in `.env.template:138` and is read by the pusher
(`play/src/pusher/enums/EnvironmentVariable.ts:136`) — but it is **never passed through in
docker-compose.yaml**. Setting it in `.env` today does nothing.

Two options:

1. **Simplest:** flip `MAP_EDITOR_ALLOW_ALL_USERS` to `"true"` at L148. Every user who can reach
   the room can edit the map. Acceptable only because the room is already behind the ticket gate.
2. **Tighter, one extra line:** add `MAP_EDITOR_ALLOWED_USERS: "$MAP_EDITOR_ALLOWED_USERS"` to the
   `play` service env block, keep `ALLOW_ALL_USERS: "false"`, and list your own identifier.

Option 2 is the right long-term answer for a public venue — a paying attendee should not be able to
repaint the stage. Option 1 is fine for the initial import if you flip it back after.

### 3d. Storage persistence

`STORAGE_DIRECTORY` defaults to `./public` (`map-storage/src/Enum/EnvironmentVariableValidator.ts:69-73`),
resolved against `working_dir: /usr/src/app/map-storage`. The only volume on the service is
`- .:/usr/src/app` — the whole repo. So **uploaded maps land in `~/workadventure/map-storage/public/`
on the VPS, inside the git working tree.**

`map-storage/.gitignore:40-41` ignores `/public/*` (keeping `.gitkeep`), so this will *not* pollute
`git status`. The real risks are narrower but worth knowing:

- **`git clean -xfd` in that repo destroys every uploaded map.** Do not run it there.
- There is no backup of this directory. Once concert.wam holds your placed megaphone areas, it is
  the only copy. Add it to whatever backup you keep, or at minimum
  `tar czf ~/mapstorage-backup-$(date +%F).tgz -C ~/workadventure/map-storage public` before edits.

Optionally point `STORAGE_DIRECTORY` at `/home/vspot/map-storage-data` with a matching bind mount to
get it out of the repo entirely. Cleaner, but it is one more moving part during a cutover — fine to
defer.

---

## 4. Importing concert.json — keeping every asset

### 4a. The rename

`UploadController.ts:139-152` explicitly rejects any `.json` file that looks like a map:
*"Invalid file extension. Maps should end with the .tmj extension."*

So `concert.json` → `concert.tmj`.

**Considered and rejected 2026-08-03: patching out the rejection instead.** It is technically a
small change, but `.tmj` is not one validation check — it is the key the WAM-pairing logic runs on,
assumed at 10+ sites across three files:

- `UploadController.ts:146, 177, 200, 216, 338, 358` — validation and the "does this .tmj need a
  .wam generated" branch
- `UploadController.ts:504` — `tmjKey.replace(".tmj", ".wam")` derives the WAM filename
- `DiskFileSystem.ts:34` and `S3FileSystem.ts:105` — derive it back the other way, and this is
  precisely the code that **preserves your placed megaphone areas across a re-upload** (§4d)

So the patch would land in the file-preservation path, in a fork we want to keep pulling upstream
fixes into. Against that, the rename costs three edits in `setup-prod.py` and one docs line.

`.tmj` is also Tiled's own official JSON map extension, not a WorkAdventure invention — set Tiled's
Save As to `.tmj` and the friction is gone permanently. Rename, don't patch.

### 4b. What goes in the zip — and what must NOT

**Do not zip the whole `maps/` directory.** It contains ~130 upstream test maps under `maps/tests/`,
plus `maps/starter/`, `maps/lab/test-map.json` and `maps/Tuto/tutoV3.json`, every one of which is a
Tiled map in `.json` form. Each would trip the rejection above and fail the upload.

The correct bundle, which preserves everything the venue actually uses:

- `concert.tmj`
- the entire `maps/assets/` tree (69 MB — the limit is `MAX_UNCOMPRESSED_SIZE`, default **1 GB**,
  so this is not close to a problem)

All 13 of concert's tilesets are **embedded** in the map JSON, so there are no `.tsx` files to
resolve. Their images total only 0.2 MB, but shipping the full `assets/` tree costs nothing and
means future edits in Tiled can reference anything already in the folder without a re-import dance.

Relative paths must be preserved — the map references e.g.
`assets/Pixel Art Top Down - Basic v1.2.3/Texture/TX Tileset Wall.png`. Build the zip from inside
`maps/` so those paths survive.

Note: files and directories whose names start with `.` are silently dropped
(`UploadController.ts:582`). Nothing in `assets/` depends on that, but don't rely on a dotfile.

### 4c. Upload

`POST /upload`, multipart, field name **`file`**, optional `directory` field, behind basic auth
(`UploadController.ts:70`). Let curl prompt for the password rather than inlining it — this
terminal mangles special characters, the same lesson as the Owncast admin API.

`curl -u <MAP_STORAGE_AUTH_USER> -F "file=@/absolute/path/concert-bundle.zip" -F "directory=" https://mapstorage.432bleu.com/upload`

The `.wam` is generated for you — `createWAMFileIfMissing` (`UploadController.ts:499`) writes a
fresh `concert.wam` alongside `concert.tmj` whenever one is absent.

### 4d. Re-upload semantics — the sharp edge

**Upload is a full directory replace, not a merge.** `deleteFilesExceptWAM`
(`map-storage/src/Upload/DiskFileSystem.ts:26`) wipes the target directory before writing. Ship a
zip containing only `concert.tmj` and every tileset image is gone.

The one carve-out works in your favour. `DiskFileSystem.ts:36-38`:

```js
// do not delete existing .wam file if there's no new version in zip and .tmj file with the same name exists
if (filesFromZip.includes(tmjKey) && !filesFromZip.includes(file)) { continue; }
```

So an existing `concert.wam` **survives** a re-upload as long as the zip contains `concert.tmj` and
**no** `concert.wam`. That is the workflow you want:

- Keep editing tiles, collisions and layout in **Tiled**, re-upload the `.tmj` + `assets/`.
- Place and edit megaphone zones in the **in-browser map editor**, which writes the `.wam`.
- **Never put a `.wam` in the zip** — that overwrites your placed areas.

---

## 5. Room URL cutover

The room moves from `/_/global/maps.432bleu.com/concert.json` to `/~/concert.tmj`.

Places that reference the old URL:

- **VPS `.env` → `START_ROOM_URL`** — the live value.
- **`setup-prod.py:120-121`** — regenerates `START_ROOM_URL=/_/global/maps.{DOMAIN}/concert.json`.
  If this is ever re-run after the cutover it silently reverts the room. Fix it in the same commit.
- **`maps/lab/README.md:8`** — the lab room URL, same `/_/global/` shape.
- **Ticket / gate links** wherever boxoffice hands out a room URL.

Standing gotcha that will bite during testing: **WorkAdventure remembers your last visited room per
browser**, so bare `play.432bleu.com` will send you back to the *old* room even after the cutover.
Always test with the explicit `/~/concert.tmj` URL, and expect to explain this to anyone helping test.

The Caddy ticket gate is `forward_auth` on `/` only, and WebSocket traffic bypasses it — so the path
change does not break the gate. But re-verify a real ticketed arrival lands correctly before a show.

---

## 6. Matrix subdomain

Same treatment, `matrix.432bleu.com`. Memory recorded six places; there are **eight** — two of them
are encoded in *filenames*, which is easy to miss:

| Location | Current value |
|---|---|
| `docker-compose.yaml:32` | allowed-hosts entry |
| `docker-compose.yaml:141` | `MATRIX_PUBLIC_URI: http://matrix.workadventure.localhost` |
| `docker-compose.yaml:144` | `MATRIX_DOMAIN: matrix.workadventure.localhost` |
| `docker-compose.yaml:493` | `traefik.http.routers.matrix.rule=Host(...)` |
| `docker-compose.yaml:502` | `VIRTUAL_HOST` |
| `docker-compose.yaml:504` | `LETSENCRYPT_HOST` |
| `docker-compose.yaml:505` | `SYNAPSE_SERVER_NAME` |
| `docker-compose.yaml:500` | volume mount `./synapse/federation:/etc/nginx/vhost.d/matrix.workadventure.localhost` |
| `synapse/homeserver.template.yaml:12-13` | `server_name` + `public_baseurl` |
| `synapse/matrix.workadventure.localhost.log.config` | **filename** encodes the domain |

Two things that are easy to get wrong:

1. **`MATRIX_PUBLIC_URI` must become `https://`.** It is browser-facing on an https page. Plain
   `http://` is blocked as mixed content even once DNS resolves — this is the actual reason chat is
   dead today, independent of the domain.
2. **`SYNAPSE_SERVER_NAME` is baked into every Matrix user ID** (`@user:server_name`). It must be
   correct *before the first registration*. Changing it later orphans every account. Since nobody
   has ever registered, this is free right now and expensive forever after.

`server_name` in `homeserver.template.yaml` must match `SYNAPSE_SERVER_NAME` exactly.

---

## 7. Deploy

`ENABLE_MAP_EDITOR` and the compose edits both need the play/pusher containers rebuilt, not just
recreated — env changes alone would only need a recreate, but the room-URL logic lives in the image.

**Always use both compose files.** Bringing the stack up without the livekit override has caused a
multi-day outage before:

`cd ~/workadventure && git pull && docker compose -f docker-compose.yaml -f docker-compose.livekit.yaml up -d --force-recreate play back map-storage synapse`

Note `/home/vspot/*.sh` is **not** covered by `git pull` — irrelevant here, but the reflex matters.

---

## 8. Verification

Run in order; each one gates the next.

1. `dig +short mapstorage.432bleu.com matrix.432bleu.com` → both `5.78.195.138`
2. `curl -sI https://mapstorage.432bleu.com/ping` → 200, valid cert
3. `curl -su <user> https://mapstorage.432bleu.com/maps` → lists `concert.tmj` after the upload
4. `docker inspect -f '{{.Name}} {{.HostConfig.RestartPolicy.Name}}' $(docker compose ps -q)` →
   map-storage and synapse still `unless-stopped`
5. Open `https://play.432bleu.com/~/concert.tmj` — map renders, all tilesets present (a missing
   tileset shows as blank/black tiles, so this is a visual check worth doing carefully)
6. Map-editor entry point appears — see below
7. Place a `speakerMegaphone` area and a `listenerMegaphone` area, then test with two browsers

**Accessing the map editor** (asked 2026-08-03, never used before): there is no separate app or URL.
It is built into the room UI and appears **only** when `canEdit` is true — i.e. all three of the
`/~/` path, `ENABLE_MAP_EDITOR`, and an edit permission from §3c are satisfied. It surfaces as the
map-editor sidebar (`play/src/front/Components/MapEditor/MapEditorSideBar.svelte`), driven by the
`mapEditorActivated` store set at `RoomConnection.ts:574`. If the sidebar is absent, the fault is
one of those three conditions — check them in that order rather than hunting through the UI.

Area properties are added from the sidebar's area editor; the megaphone ones are
`speakerMegaphone` (name, chatEnabled, seeAttendees) and `listenerMegaphone` (speakerZoneName
pointing at the speaker area, chatEnabled, waitingLink) — `libs/map-editor/src/types.ts:136-145`.

---

## 9. Rollback

Cheap, because the old path never goes away. `/_/global/maps.432bleu.com/concert.json` keeps working
throughout — the Tiled map stays served from `maps.432bleu.com` regardless of what map-storage holds.

To revert: put `START_ROOM_URL` back and restart `play`. Nothing else has to be undone, and no
attendee data lives in map-storage. Do the cutover well before a show, not on show day.

---

## Open items deliberately not covered here

- **Megaphone publishes a *browser* camera**, so OBS scenes and overlays are lost. Fix is to select
  **OBS Virtual Camera** as the browser's camera input. Worth testing at the same time as the zones.
- **Never load-tested at 1 publisher → ~150 subscribers.** T3 only did 40 subs, and the Helsinki
  load VM was deleted 2026-08-01 — a new cloud vantage is required. Encouraging arithmetic: T3
  sustained ~240 outbound tracks at 98.65% of a core, and a megaphone show is only ~150 outbound
  tracks, so the shape is more favourable than T3 was. It still has to be measured.
- Owncast and the megaphone are independent subsystems (Owncast is not even in the compose project),
  sharing only CPU and the pipe. Running both side by side is both the safe migration path and the
  real load test.
