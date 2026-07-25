#!/usr/bin/env bash
# T2: simulate N HLS viewers against Owncast. Run from the LOCAL machine (or any box
# with enough download bandwidth: N * ~1.2 Mbps).
# Usage: bash t2-owncast-viewers.sh <N> <duration_seconds> [master_playlist_url]
# A stream must be live (OBS or the VPS loop) or every fetch 404s.
set -u
LOCKFILE="/tmp/t2-owncast-viewers.lock"
exec 9>"$LOCKFILE"
if ! flock -n 9; then
  echo "T2: another instance is already running (lock held on $LOCKFILE) — exiting" >&2
  exit 1
fi
N="${1:-10}"
DUR="${2:-300}"
MASTER="${3:-https://owncast.432bleu.com/hls/stream.m3u8}"
# results persist (RESULTS_DIR overrides); old trap's `kill 0` killed this shell
# before rm ran, and deleting results loses the run if the summary never prints
TMPDIR="${RESULTS_DIR:-$(mktemp -d)}"
mkdir -p "$TMPDIR"
trap 'pkill -P $$ 2>/dev/null' EXIT INT TERM

# resolve media playlist (master may point at variant playlists)
MEDIA=$(curl -sf "$MASTER" | grep -v '^#' | grep -m1 'm3u8' || true)
if [ -n "$MEDIA" ]; then
  case "$MEDIA" in http*) PL="$MEDIA" ;; *) PL="$(dirname "$MASTER")/$MEDIA" ;; esac
else
  PL="$MASTER"
fi
BASE=$(dirname "$PL")
# a fetch only counts as a stall if it's slower than real-time, i.e. takes longer
# than one segment duration — read it from the playlist (Owncast uses 10s, not 4s)
SEGDUR=$(curl -sf --max-time 5 "$PL" | grep -m1 '^#EXT-X-TARGETDURATION' | grep -oE '[0-9]+' || echo 4)
echo "T2: $N viewers, ${DUR}s, playlist: $PL (segment=${SEGDUR}s)"

viewer() {
  local id=$1 end=$(( $(date +%s) + DUR )) last=""
  while [ "$(date +%s)" -lt "$end" ]; do
    seg=$(curl -sf --max-time 5 "$PL" | grep -v '^#' | grep -v m3u8 | tail -1)
    if [ -n "$seg" ] && [ "$seg" != "$last" ]; then
      last="$seg"
      case "$seg" in http*) u="$seg" ;; *) u="$BASE/$seg" ;; esac
      t=$(curl -sf --max-time $((SEGDUR * 2)) -o /dev/null -w '%{time_total} %{size_download}' "$u" || echo "FAIL 0")
      echo "$t" >> "$TMPDIR/v$id"
    fi
    sleep 2
  done
}

for i in $(seq 1 "$N"); do viewer "$i" & sleep 0.05; done
echo "viewers launched; running ${DUR}s..."
wait

# summarize: fetches, failures, stalls (fetch time > segment duration), GB pulled
awk -v segdur="$SEGDUR" '
  $1=="FAIL" {fail++; next}
  {n++; bytes+=$2; if ($1+0 > segdur) stall++; sum+=$1}
  END {
    printf "fetches=%d  failures=%d  stalls(>%ss)=%d (%.2f%%)  avg_fetch=%.2fs  pulled=%.2f GB\n",
      n, fail, segdur, stall, (n?stall*100/n:0), (n?sum/n:0), bytes/1e9
    exit (fail+stall > n*0.01) ? 1 : 0
  }' "$TMPDIR"/v* 2>/dev/null
RC=$?
[ $RC -eq 0 ] && echo "T2 PASS (stall+failure rate < 1%)" || echo "T2 FAIL (stall/failure rate over threshold)"
echo "raw per-viewer results kept in $TMPDIR"
exit $RC
