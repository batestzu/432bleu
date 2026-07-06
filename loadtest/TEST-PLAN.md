# 432 BLEU — 150-Guest Capacity Test Plan

Goal: prove (or disprove) that one show with **150 concurrent guests** survives on the
current VPS, and if not, identify *which* resource fails first so the upgrade is targeted
instead of guesswork.

## The machine under test (YABS 2026-07-06)

| Resource | Value | Verdict for 150 guests |
|---|---|---|
| CPU | 3 vCPU AMD EPYC-Rome 2.4GHz | **Suspect #2** — Owncast ffmpeg alone eats ~1 core |
| RAM | 3.7 GiB + 2 GiB swap | **Suspect #1** — whole stack + 150 WS sessions is tight |
| Disk | NVMe, 232 MB/s mixed 4k | Non-issue |
| Network | iperf results pending | Need ≥ ~400 Mbps TX headroom (150 × 1.2 Mbps HLS ≈ 180 Mbps steady + LiveKit) |

Predicted steady-state load at 150 guests: Owncast egress ~180 Mbps ≈ **81 GB/hour**
(Hetzner 20 TB/mo allowance → fine, but confirm TX speed when iperf finishes).

## Test matrix

| # | Test | What it isolates | Pass criteria |
|---|---|---|---|
| T0 | Smoke (2 bots) | Harness works against prod | 2 bots join lab room, receive moves, clean exit |
| T1 | Presence: 150 avatar bots, 10 min | pusher/back CPU+RAM, WS fan-out | ≥95% bots connect & stay; combined `play`+`back` CPU < 200% (of 300%); no container restart |
| T2 | Stream: 150 HLS viewers, 20 min | Owncast CPU + network egress | Stall rate < 1% of segment fetches; TX ≈ 180 Mbps sustained; host load1 < 3 |
| T3 | Proximity: LiveKit 20 pub / 40 sub, 10 min | SFU CPU, UDP relay | lk-reported packet loss < 2%; `livekit` CPU < 150% |
| T4 | **Soak: T1+T2+T3 together, 60 min** | The real show; RAM & swap under everything | No OOM-kills (`dmesg`), swap I/O ~0 after warmup, no restarts, stall rate < 2% |
| T5 | Doors burst: 150 gate checks in 60s | Caddy forward_auth + boxoffice + postgres | All 200/302 within 2s; no 5xx |

Run in order. T4 is the verdict; T1–T3 exist so that when T4 degrades you already know
which component owns the failure.

## Safety rails (prod is live — obey these)

- **Bots go to the lab room only** (`maps.432bleu.com/lab/test-map.json`), never the
  concert map. Requires `maps/lab/` pushed + pulled on VPS first.
- Bot names are `LOADTEST-<n>` so anyone who wanders in understands.
- Run off-hours. The WS endpoint bypasses the Caddy ticket gate (forward_auth covers `/`
  only), so bots don't consume ticket codes.
- **Abort test if:** sustained swap-in/out in monitor CSV, load1 > 6, or any container
  restarts — collect the CSV and stop; that's a result, not a failure of the test.
- `MAX_PER_GROUP` ships as 100 in `.env.template` — check the VPS `.env` value before T3.
  For a concert, cap it (4–6) or one giant proximity blob can form and melt LiveKit.

## How to run

Every VPS command is single-line (paste-safe). Start the monitor on the VPS before each
test, Ctrl-C after; it writes `~/loadtest-<label>-<ts>.csv`.

**VPS (before any test):**
`cd ~/workadventure && git pull origin master && bash loadtest/monitor.sh t1 5`

**T0/T1 — from the local machine (32 GB box handles 150 bots easily).**
No Node on this host — run via the WA dev image (deps already installed 2026-07-06;
offline `smoke-imports.ts` passes). One-time prep if node_modules ever vanish:
`npm install` in `messages/` (+ `npm run ts-proto`), `libs/messages/`, and `loadtest/t1-wa-bots/`,
each via the docker wrapper below.
```bash
# T0 smoke (2 bots, 60s) — requires maps/lab pushed + pulled on VPS first
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e BOTS=2 -e DURATION_S=60 \
  -v $HOME/vspot/432bleu-local:/repo -w /repo/loadtest/t1-wa-bots \
  --entrypoint bash thecodingmachine/nodejs:v2-22-bullseye -c "npm run t1"

# T1 (150 bots, ramp 1/s, 10 min): same command with
#   -e BOTS=150 -e RAMP_MS=1000 -e DURATION_S=600
```

**T2 — from the local machine** (needs OBS or the VPS loop feeding Owncast first;
~180 Mbps download locally — if your home line can't, run at N=75 and double the math):
```bash
bash ~/vspot/432bleu-local/loadtest/t2-owncast-viewers.sh 150 1200
```

**T3 — from the local machine** (install `lk` CLI once: https://github.com/livekit/livekit-cli;
keys are in VPS `~/workadventure/.env`):
```bash
lk load-test --url wss://livekit.432bleu.com --api-key <KEY> --api-secret <SECRET> \
  --video-publishers 20 --subscribers 40 --duration 10m
```

**T4 — soak:** start monitor with label `t4`, then T1 (DURATION_S=3600) + T2 (3600) +
T3 (--duration 60m) together. Afterwards on VPS:
`dmesg -T | grep -i oom; docker compose -f docker-compose.yaml -f docker-compose.livekit.yaml ps`

**T5 — doors burst, from local machine:**
```bash
seq 150 | xargs -P 50 -I{} curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" https://play.432bleu.com/
seq 150 | xargs -P 50 -I{} curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" https://boxoffice.432bleu.com/api/events
```

## Reading the results → upgrade decision

| Symptom in T4 | Owner | Cheapest fix |
|---|---|---|
| swap churn, OOM kills, containers restarting | RAM | CPX31 (4 vCPU / 8 GB, ~€2/mo more) — likely needed regardless |
| Owncast CPU pegged, stalls climb with viewers | CPU (transcode) | Set Owncast to passthrough (no re-encode) and send a stream OBS already encoded at 1.2 Mbps; else CPX31 |
| `livekit` CPU pegged, packet loss in T3 | CPU (SFU) | Lower MAX_PER_GROUP; CPX41 only if groups must be big |
| TX plateaus below ~250 Mbps | Network | Confirm with iperf; Hetzner is normally 1 Gbps+ — check for in-VM limits |
| back/play CPU pegged in T1 alone | WA presence | CPX31/41 — but at <200% on 3 cores WA handles 150 walkers fine in practice |

Known caveat: the WA-shipped `benchmark/` bot targets an older code layout and does not
compile against this tree — `t1-wa-bots/` here speaks the current `/ws/room` protobuf
protocol instead. If WA is upgraded upstream, re-smoke T0 before trusting T1.
