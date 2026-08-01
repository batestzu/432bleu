#!/usr/bin/env bash
# T5 — doors burst. Ramps concurrency and aborts on any 5xx.
set -u
OUT=$(mktemp -d)
FAIL=0

burst() {
  local label=$1 url=$2 conc=$3 n=$4; shift 4
  local f="$OUT/$label"
  local t0=$(date +%s)
  seq "$n" | xargs -P "$conc" -I{} curl -s -o /dev/null \
      -w "%{http_code} %{time_total}\n" --max-time 20 "$@" "$url" > "$f"
  local t1=$(date +%s)
  echo "--- $label : $n reqs @ P$conc -> $url"
  echo -n "    codes: "; awk '{print $1}' "$f" | sort | uniq -c | awk '{printf "%s×%s ", $1, $2}'; echo
  awk -v lbl="$label" '{s+=$2; if($2>m)m=$2; if($2>2)slow++}
       END {printf "    time: avg=%.3fs max=%.3fs over-2s=%d/%d\n", s/NR, m, slow+0, NR}' "$f"
  echo "    wall: $((t1-t0))s"
  if awk '{print $1}' "$f" | grep -qE '^5'; then
    echo "    *** 5xx DETECTED — ABORTING ***"; FAIL=1
  fi
}

EVENTS=https://boxoffice.432bleu.com/api/events
GATE=https://play.432bleu.com/

echo "=== T5 doors burst — $(date) ==="
burst events-p5   "$EVENTS" 5  150
[ $FAIL -eq 1 ] && exit 1
burst gate-p5     "$GATE"   5  150 -b "bleu_pass=T5PROBE"
[ $FAIL -eq 1 ] && exit 1
echo "--- low concurrency clean, ramping to plan spec (P50) ---"
burst events-p50  "$EVENTS" 50 150
[ $FAIL -eq 1 ] && exit 1
burst gate-p50    "$GATE"   50 150 -b "bleu_pass=T5PROBE"
[ $FAIL -eq 1 ] && exit 1
echo "=== T5 complete, no 5xx ==="
