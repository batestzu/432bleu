#!/usr/bin/env bash
# VPS-side metrics collector for load tests. Run before each test, Ctrl-C to stop.
# Usage: bash loadtest/monitor.sh <label> [interval_seconds]
# Output: ~/loadtest-<label>-<timestamp>.csv
set -u
LABEL="${1:-run}"
INT="${2:-5}"
OUT="$HOME/loadtest-${LABEL}-$(date +%Y%m%d-%H%M%S).csv"
IFACE=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'dev \K\S+' | head -1)
IFACE="${IFACE:-eth0}"

echo "ts,load1,mem_used_mb,mem_avail_mb,swap_used_mb,swap_in_kb,swap_out_kb,rx_mbps,tx_mbps,containers" > "$OUT"
echo "monitor: writing to $OUT (iface $IFACE, every ${INT}s) — Ctrl-C to stop"

read_net() { awk -v i="$IFACE" '$1 == i":" {print $2, $10}' /proc/net/dev; }

PREV=$(read_net)
PREV_SI=$(awk '/pswpin/ {print $2}' /proc/vmstat)
PREV_SO=$(awk '/pswpout/ {print $2}' /proc/vmstat)

while true; do
  sleep "$INT"
  TS=$(date +%H:%M:%S)
  LOAD1=$(cut -d' ' -f1 /proc/loadavg)
  read -r MEM_USED MEM_AVAIL SWAP_USED <<< "$(free -m | awk 'NR==2{u=$3; a=$7} NR==3{s=$3} END{print u, a, s}')"
  CUR=$(read_net)
  RX_MBPS=$(awk -v p="$(echo "$PREV" | cut -d' ' -f1)" -v c="$(echo "$CUR" | cut -d' ' -f1)" -v t="$INT" 'BEGIN{printf "%.1f", (c-p)*8/t/1000000}')
  TX_MBPS=$(awk -v p="$(echo "$PREV" | cut -d' ' -f2)" -v c="$(echo "$CUR" | cut -d' ' -f2)" -v t="$INT" 'BEGIN{printf "%.1f", (c-p)*8/t/1000000}')
  PREV=$CUR
  SI=$(awk '/pswpin/ {print $2}' /proc/vmstat); SO=$(awk '/pswpout/ {print $2}' /proc/vmstat)
  DSI=$(( (SI - PREV_SI) * 4 )); DSO=$(( (SO - PREV_SO) * 4 ))   # pages -> KB
  PREV_SI=$SI; PREV_SO=$SO
  # top 6 containers by CPU: name:cpu%:mem
  CONT=$(docker stats --no-stream --format '{{.Name}}:{{.CPUPerc}}:{{.MemUsage}}' 2>/dev/null \
        | sed 's/ \/.*//' | sort -t: -k2 -rn | head -6 | paste -sd'|' -)
  echo "$TS,$LOAD1,$MEM_USED,$MEM_AVAIL,$SWAP_USED,$DSI,$DSO,$RX_MBPS,$TX_MBPS,$CONT" >> "$OUT"
done
