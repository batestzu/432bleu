# Surviving a reboot

Written 2026-08-01, after an unattended security upgrade rebooted the VPS and took
`play`, `boxoffice`, `maps` and Traefik down for ~25 minutes without anyone noticing.
Only `livekit`, `redis` and `owncast` came back, because they are the only containers
with a restart policy.

Same failure class as the 3-day silent LiveKit outage in July 2026.

---

## Part A — restart policies (APPLIED 2026-08-02)

`docker-compose.yaml` originally set **no** `restart:` policy on any service — which is why
a reboot left only livekit/redis/owncast running. `restart: unless-stopped` is now set on
the ten production-critical services below.

`redis` is deliberately set in **both** `docker-compose.yaml` and
`docker-compose.livekit.yaml`. That is not redundant: bringing the stack up without the
override file has happened before and caused a multi-day proximity-chat outage, so the base
file must be safe on its own.

| Service | Add policy? | Why |
|---|---|---|
| `reverse-proxy` | **yes** | Traefik — everything except Owncast routes through it. Its absence is what turns a reboot into a site-wide 502. |
| `play` | **yes** | The venue itself. |
| `back` | **yes** | Game state / presence. |
| `boxoffice` | **yes** | Ticketing — takes real money. |
| `postgres` | **yes** | boxoffice's database. |
| `maps` | **yes** | Serves the map JSON. |
| `map-storage` | **yes** | WA map storage API. |
| `uploader` | **yes** | User uploads. |
| `icon` | yes | Cheap, harmless. |
| `redis`, `livekit` | already set | In `docker-compose.livekit.yaml` (commit `3371d3e`). |
| `messages` | no | Build-only container, exits on purpose. |
| `redisinsight` | no | Dev tool, not needed in prod. |
| `oidc-server-mock` | no | Placeholder for a real IdP, not used. |
| `synapse` | **yes** (added 2026-08-02) | Matrix chat. But see the warning below — it is not reachable in prod as configured. |

`unless-stopped` (not `always`) is the right choice: it restores containers on boot and
after crashes, but respects a deliberate `docker compose stop` — so it will not fight you
during maintenance.

### Warning: Matrix chat is not actually reachable in production

`synapse` now restarts, but that only guarantees the container runs — it does not make
in-world chat work. Matrix is still wired to the upstream **dev** domain
`matrix.workadventure.localhost`, hardcoded in six places in `docker-compose.yaml`:
`MATRIX_PUBLIC_URI` (141), `MATRIX_DOMAIN` (144), the Traefik router rule (~492),
`VIRTUAL_HOST` / `LETSENCRYPT_HOST` / `SYNAPSE_SERVER_NAME` (501-504), plus play's allowed
host list (32). Confirmed 2026-08-02 that neither `matrix.432bleu.com` nor
`chat.432bleu.com` resolves in DNS.

`MATRIX_PUBLIC_URI` is the URL the **browser** connects to, so as configured it cannot work
for a real user: the hostname does not resolve, and it is plain `http` on an `https` page,
which browsers block as mixed content regardless.

Making Matrix chat real would need: a subdomain (`matrix.432bleu.com`) in DNS, a Caddy route
and cert for it, those six values changed to the real domain, and `SYNAPSE_SERVER_NAME` set
before first user registration — **it is baked into user IDs and painful to change later.**
Same hardcoded-dev-domain class of problem as `PUBLIC_MAP_STORAGE_URL` in the megaphone
thread. Treat it as a project, not a config tweak.

**Before pulling on the VPS**, check for prod drift — this compose file has had
uncommitted VPS-local edits before, which blocked a `git pull` in June 2026:

```
cd ~/workadventure && git status --short docker-compose.yaml
```

Apply, then verify the policy is actually live on the running containers:

```
cd ~/workadventure && docker compose -f docker-compose.yaml -f docker-compose.livekit.yaml up -d && docker inspect -f '{{.Name}} {{.HostConfig.RestartPolicy.Name}}' $(docker compose ps -q)
```

A real reboot test is the only true verification, but that costs a few minutes of downtime —
worth doing once, deliberately, rather than discovering it during a show.

---

## Part B — systemd unit for the Owncast house loop

The loop is a bare backgrounded ffmpeg started by `start_loop.sh`. It is not a container
and nothing restarts it, so **every reboot leaves Owncast live with no source**. It was
dead for ~40 minutes on 2026-08-01 before anyone looked.

### The trap: a naive unit will break stream switching

The RTMP pipeline deliberately kills and restarts the loop:

- `on_publish.sh` kills the loop so the performer's relay can take the Owncast slot.
- `on_publish_done.sh` restarts the loop when the performer disconnects.

If the loop becomes a systemd service with `Restart=always` while those scripts still kill
it by PID, systemd will see the main process die and **restart the loop right back on top
of the performer's relay**. That is worse than today's bug — it turns an occasional race
into a guaranteed fight every single time someone goes live.

So Part B is all-or-nothing: adopting systemd means the scripts must stop managing the
loop by PID and start using `systemctl`. Do not do half of it.

### The upside

`systemctl stop` is **synchronous** — it blocks until the process is actually gone. That
is exactly the race that `on_publish.sh` currently hand-rolls with a `kill` + poll loop
(commit `ec7d483`). Moving to systemd lets that logic be deleted rather than maintained.

### The unit

`/etc/systemd/system/owncast-loop.service`:

```ini
[Unit]
Description=Owncast house loop (fallback video when no performer is live)
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/home/vspot/owncast.conf
ExecStart=/usr/bin/ffmpeg -re -stream_loop -1 -i /home/vspot/loop.mp4 -c copy -f flv ${OWNCAST_RTMP}/${STREAM_KEY}
Restart=always
RestartSec=5
StandardOutput=append:/home/vspot/loop.log
StandardError=append:/home/vspot/loop.log

[Install]
WantedBy=multi-user.target
```

Then:

```
sudo systemctl daemon-reload && sudo systemctl enable --now owncast-loop && sleep 3 && systemctl is-active owncast-loop
```

Note `EnvironmentFile` requires `owncast.conf` to be plain `KEY=value` lines with no
`export` and no shell quoting. Check it first — it is currently `source`d by bash, which
is more permissive than systemd's parser.

### Script changes that must land at the same time

In `on_publish.sh`, the entire kill-and-wait block becomes:

```bash
systemctl stop owncast-loop
```

In `on_publish_done.sh`, the loop-restart retry block becomes:

```bash
systemctl start owncast-loop
```

The relay retry loop in `on_publish.sh` should stay — it guards against Owncast being slow
to free the RTMP slot, which is a separate concern from loop shutdown.

### Privilege check — do this before committing to Part B

`exec_publish` runs these scripts as whatever user nginx's worker runs as. They currently
get away with killing processes and writing to `/home/vspot/`, which suggests root, but
`systemctl stop` is a stricter bar. Verify:

```
ps -o user= -C nginx | sort -u
```

If the workers are not root, add a sudoers rule for exactly these two verbs rather than
loosening anything broadly:

```
vspot ALL=(root) NOPASSWD: /bin/systemctl start owncast-loop, /bin/systemctl stop owncast-loop
```

and call `sudo systemctl ...` in the scripts.

---

## Part C — the gap neither part closes

Both parts fix *recovery*. Neither tells you an outage happened. Today's 25-minute outage
was found by accident, and July's LiveKit outage went unnoticed for three days.

An uptime check on `play.432bleu.com`, `boxoffice.432bleu.com` and the Owncast
`/api/status` endpoint — even a free external pinger — would have caught all three
incidents in under a minute. That is the highest-value item on this page and the cheapest.

---

## Part D — monitoring (implemented 2026-08-01: `scripts/vps/healthcheck.sh`)

### Why a dead-man's switch, not just an external pinger

An outside-in HTTP monitor tells you the site is unreachable. It does **not** tell you the
house loop died while Owncast stayed up — which is a silent, show-ruining failure, and it
happened for ~40 minutes on 2026-08-01 without anyone noticing.

Inverting it covers both: cron runs `healthcheck.sh` on the VPS every 5 minutes, and the
script pings an external URL **only when every check passes**. The external service alerts
on the *absence* of a ping, so:

| Failure | What happens | Caught? |
|---|---|---|
| Services down, box alive | checks fail → no ping | yes |
| Whole box down / rebooting | cron never runs → no ping | yes |
| Owncast up but no source | `online=false` → no ping | yes — an external HTTP check would miss this |
| Container exited | compose ps shows it → no ping | yes |

No inbound access or open ports required, and it costs nothing.

### What it checks

`play` (200/302 — a 302 is the healthy gate redirect), `boxoffice /api/events`, Owncast's
API, **whether Owncast actually has a live source**, and whether any container has exited
(ignoring `messages`, `redisinsight`, `oidc-server-mock`, which exit by design).

Being unable to run a check counts as a **failure**, never a pass. A monitor that reports
healthy because it couldn't look is worse than none.

### Setup

1. Create a free check at healthchecks.io (or any equivalent) and copy its ping URL.
   **This step needs a human — it requires an account.** Period 5m, grace 15m gives an
   alert roughly 20 minutes after a failure; tighten both before a show.
2. On the VPS:

```
cd ~/workadventure && git pull && sudo cp scripts/vps/healthcheck.sh /home/vspot/healthcheck.sh && sudo chmod +x /home/vspot/healthcheck.sh
```
```
echo 'HEALTHCHECK_PING_URL=https://hc-ping.com/YOUR-UUID' | sudo tee /home/vspot/healthcheck.conf
```
```
/home/vspot/healthcheck.sh
```

That last line prints the report and exits non-zero if anything is wrong — run it once by
hand before trusting it. Then add the cron entry with `crontab -e`:

```
*/5 * * * * /home/vspot/healthcheck.sh >> /home/vspot/healthcheck.log 2>&1
```

### Deliberately verify it fires

Stop something harmless and confirm an alert actually arrives. An untested alarm is an
assumption, and this whole document exists because of assumptions that went untested.

### Optional complement

The script curls the public HTTPS URLs, so it already exercises DNS, certs, Caddy, Traefik
and the containers. An external prober (UptimeRobot free tier) adds only the
outside-the-datacenter view — worth adding eventually, but the dead-man's switch is the
higher-value half and should go first.
