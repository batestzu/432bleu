#!/usr/bin/env bash
# T2: simulate N HLS viewers against Owncast. Run from the LOCAL machine (or any box
# with enough download bandwidth: N * ~1.2 Mbps).
# Usage: bash t2-owncast-viewers.sh <N> <duration_seconds> [master_playlist_url]
# A stream must be live (OBS or the VPS loop) or every fetch 404s.
set -u
N="${1:-10}"
DUR="${2:-300}"
MASTER="${3:-https://owncast.432bleu.com/hls/stream.m3u8}"
TMPDIR=$(mktemp -d)
trap 'kill 0 2>/dev/null; rm -rf "$TMPDIR"' EXIT INT TERM

# resolve media playlist (master may point at variant playlists)
MEDIA=$(curl -sf "$MASTER" | grep -v '^#' | grep -m1 'm3u8' || true)
if [ -n "$MEDIA" ]; then
  case "$MEDIA" in http*) PL="$MEDIA" ;; *) PL="$(dirname "$MASTER")/$MEDIA" ;; esac
else
  PL="$MASTER"
fi
BASE=$(dirname "$PL")
echo "T2: $N viewers, ${DUR}s, playlist: $PL"

viewer() {
  local id=$1 end=$(( $(date +%s) + DUR )) last=""
  while [ "$(date +%s)" -lt "$end" ]; do
    seg=$(curl -sf --max-time 5 "$PL" | grep -v '^#' | grep -v m3u8 | tail -1)
    if [ -n "$seg" ] && [ "$seg" != "$last" ]; then
      last="$seg"
      case "$seg" in http*) u="$seg" ;; *) u="$BASE/$seg" ;; esac
      t=$(curl -sf --max-time 10 -o /dev/null -w '%{time_total} %{size_download}' "$u" || echo "FAIL 0")
      echo "$t" >> "$TMPDIR/v$id"
    fi
    sleep 2
  done
}

for i in $(seq 1 "$N"); do viewer "$i" & sleep 0.05; done
echo "viewers launched; running ${DUR}s..."
wait

# summarize: fetches, failures, stalls (fetch time > 4s segment duration), GB pulled
awk '
  $1=="FAIL" {fail++; next}
  {n++; bytes+=$2; if ($1+0 > 4) stall++; sum+=$1}
  END {
    printf "fetches=%d  failures=%d  stalls(>4s)=%d (%.2f%%)  avg_fetch=%.2fs  pulled=%.2f GB\n",
      n, fail, stall, (n?stall*100/n:0), (n?sum/n:0), bytes/1e9
    exit (fail+stall > n*0.01) ? 1 : 0
  }' "$TMPDIR"/v* 2>/dev/null
RC=$?
[ $RC -eq 0 ] && echo "T2 PASS (stall+failure rate < 1%)" || echo "T2 FAIL (stall/failure rate over threshold)"
exit $RC
