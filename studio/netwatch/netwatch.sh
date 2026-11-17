#!/bin/bash
# netwatch.sh: where did the network freeze?
#
# Pings three places once a second each and logs every reply and every miss:
#   router    the venue's router        -> the WiFi between Zoltan and the router
#   internet  1.1.1.1 (Cloudflare)      -> the building's internet connection
#   vps       432bleu.com (Oregon)      -> the whole path the stream takes
# When it stops, it lists every outage and says which link it was in. That
# answer picks the fix: a cable (WiFi) or a separate uplink (building internet).
# Written after show #23, 2026-11-11: five uplink freezes, cause unknown.
# See brain: Incidents/2026-11-11 Five Drops on Venue WiFi.
#
#   ./netwatch.sh               run until Ctrl-C, then print the report
#   ./netwatch.sh 120           run for 120 seconds, then print the report
#   ./netwatch.sh report FILE   print the report for an earlier log again
#
# Start it before doors and leave the terminal open. It uses a few hundred
# bytes a second, which is nothing next to the stream. Logs: ./logs/*.csv
#
# Limit: these are pings, not the video stream. A firewall that throttles
# long-running uploads could freeze OBS while pings look fine. If OBS drops
# and all three stay clean, that points at such a firewall.

set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPORT=$HERE/netwatch_report.py

if [ "${1:-}" = "report" ]; then
    exec python3 "$REPORT" "${2:?usage: netwatch.sh report FILE}"
fi

DURATION=${1:-0}
case "$DURATION" in ''|*[!0-9]*) echo "usage: netwatch.sh [seconds] | report FILE" >&2; exit 2;; esac

ROUTER=$(ip -4 route show default 2>/dev/null | awk '{print $3; exit}')
INTERNET=1.1.1.1
VPS=$(getent ahostsv4 432bleu.com 2>/dev/null | awk '{print $1; exit}')
VPS=${VPS:-5.78.195.138}      # if DNS is down at start, still watch the VPS
[ -n "$ROUTER" ] || { echo "No default route: is Zoltan on a network?" >&2; exit 1; }

mkdir -p "$HERE/logs"
LOG=$HERE/logs/netwatch-$(date +%F_%H%M%S).csv
echo "epoch,target,seq,rtt_ms" > "$LOG"

# One ping per target. -D stamps each line with the epoch time, and -O prints
# "no answer yet" for a ping that got no reply before the next one went out.
# That miss line is what turns silence into data. A reply that arrives late is
# still logged, and the report keeps the reply over the miss.
pinger() {
    local name=$1 ip=$2
    ping -D -O -n -i 1 -W 2 "$ip" 2>&1 | gawk -v t="$name" '
        function seq() { return match($0, /icmp_seq=([0-9]+)/, m) ? m[1] : "" }
        function ts()  { return match($0, /^\[([0-9.]+)\]/, m) ? m[1] : systime() }
        /time=/          { match($0, /time=([0-9.]+)/, r); printf "%s,%s,%s,%s\n", ts(), t, seq(), r[1]; fflush(); next }
        /no answer yet/  { printf "%s,%s,%s,LOST\n", ts(), t, seq(); fflush(); next }
        /unreachable|sendmsg|failure/ { printf "%s,%s,,DOWN\n", ts(), t; fflush() }
    ' >> "$LOG"
}

PIDS=()
pinger router   "$ROUTER"   & PIDS+=($!)
pinger internet "$INTERNET" & PIDS+=($!)
pinger vps      "$VPS"      & PIDS+=($!)

finish() {
    trap - INT TERM
    # Each pinger is a subshell whose CHILDREN are the ping and its parser.
    # Killing only the subshell orphans them, and an orphaned ping keeps
    # appending to this log forever (the first version did exactly that).
    local p
    for p in "${PIDS[@]}"; do pkill -TERM -P "$p" 2>/dev/null; kill "$p" 2>/dev/null; done
    wait 2>/dev/null
    echo
    python3 "$REPORT" "$LOG"
    exit 0
}
trap finish INT TERM

echo "netwatch: router $ROUTER, internet $INTERNET, vps $VPS"
echo "log: $LOG"
if [ "$DURATION" -gt 0 ]; then echo "running for ${DURATION}s"; else echo "running until Ctrl-C"; fi
echo "every 10 s: average reply time per target, and misses in brackets"

START=$(date +%s)
while :; do
    sleep 10
    now=$(date +%s)
    gawk -F, -v since=$((now - 10)) '
        NR > 1 && $1 >= since {
            if ($4 == "LOST" || $4 == "DOWN") lost[$2]++; else { sum[$2] += $4; n[$2]++ }
        }
        END {
            line = strftime("%H:%M:%S")
            split("router internet vps", ts, " ")
            for (i = 1; i <= 3; i++) {
                t = ts[i]
                v = n[t] ? sprintf("%5.0f ms", sum[t] / n[t]) : "   --   "
                line = line sprintf("   %s %s [%d]", t, v, lost[t] + 0)
            }
            print line
        }' "$LOG"
    if [ "$DURATION" -gt 0 ] && [ $((now - START)) -ge "$DURATION" ]; then finish; fi
done
