#!/bin/bash
# Exercises stream_lib.sh against fake processes whose command lines are copied
# verbatim from the VPS: both the OLD form (what is running right now, started
# by the previous scripts) and the NEW form this change introduces. A deploy has
# to be able to kill the old ones, so every pattern must match both.
# Runs anywhere: it only spawns fake processes named ffmpeg and talks to ports
# nothing is listening on. Safe to run on the VPS; it never touches the real legs.
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export VSPOT_HOME=$(mktemp -d)
source "$HERE/stream_lib.sh"
LOG=$VSPOT_HOME/test.log
: > "$LOG"

pass=0; fail=0
ok()   { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }
check(){ if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (got '$2', want '$3')"; fi; }

K=KKMlLkUPYDOq5IInal0m9Y4i9X9UtX
NEW='-nostdin -nostats -loglevel warning'

# OLD command lines — copied from ps on the VPS during the 2026-09-03 incident.
OLD_LOOP_VIDEO="ffmpeg -re -stream_loop -1 -i /home/vspot/loop.mp4 -c copy -f flv rtmp://localhost:1936/live/$K"
OLD_LOOP_AUDIO="ffmpeg -re -stream_loop -1 -i /home/vspot/loop.mp4 -vn -c:a libmp3lame -b:a 128k -content_type audio/mpeg -f mp3 icecast://source:pw@127.0.0.1:8005/live.mp3"
OLD_RELAY_VIDEO="ffmpeg -i rtmp://localhost:1935/live/$K -map 0:v -map 0:a -c copy -f flv rtmp://localhost:1936/live/$K"
OLD_RELAY_AUDIO="ffmpeg -i rtmp://localhost:1935/live/$K -vn -c:a libmp3lame -b:a 128k -content_type audio/mpeg -f mp3 icecast://source:pw@127.0.0.1:8005/live.mp3"
# NEW command lines — what the rewritten scripts launch.
NEW_LOOP_VIDEO="ffmpeg $NEW -re -stream_loop -1 -i /home/vspot/loop.mp4 -c copy -f flv rtmp://localhost:1936/live/$K"
NEW_LOOP_AUDIO="ffmpeg $NEW -re -stream_loop -1 -i /home/vspot/loop.mp4 -vn -c:a libmp3lame -b:a 128k -content_type audio/mpeg -f mp3 icecast://source:pw@127.0.0.1:8005/live.mp3"
NEW_RELAY_VIDEO="ffmpeg $NEW -i rtmp://localhost:1935/live/$K -map 0:v -map 0:a -c copy -f flv rtmp://localhost:1936/live/$K"
NEW_RELAY_AUDIO="ffmpeg $NEW -i rtmp://localhost:1935/live/$K -vn -c:a libmp3lame -b:a 128k -content_type audio/mpeg -f mp3 icecast://source:pw@127.0.0.1:8005/live.mp3"
# Owncast's own internal transcoder — must never be matched by any pattern.
CMD_OWNCAST='/usr/bin/ffmpeg -hide_banner -loglevel warning -fflags +genpts -flags +cgop -i pipe:0 -map v:0 -c:v:0 libx264 -b:v:0 2308k'

# Fakes must be named ffmpeg, because pids_matching filters on /proc/pid/comm.
# Copying sleep to a file called ffmpeg gives the fake the right process name
# while argv carries the command line we want to match.
FAKE=$VSPOT_HOME/bin/ffmpeg
mkdir -p "$VSPOT_HOME/bin" && cp /bin/sleep "$FAKE"
SPAWNED=()
spawn() { setsid bash -c "exec -a \"$1\" \"$FAKE\" 120" & SPAWNED+=($!); disown 2>/dev/null; sleep 0.1; }
cleanup() {
    [ ${#SPAWNED[@]} -gt 0 ] && kill -9 "${SPAWNED[@]}" 2>/dev/null
    rm -rf "$VSPOT_HOME"
}
trap cleanup EXIT

echo "== spawning old and new forms of all four legs, plus Owncast's transcoder"
for c in "$OLD_LOOP_VIDEO" "$OLD_LOOP_AUDIO" "$OLD_RELAY_VIDEO" "$OLD_RELAY_AUDIO" \
         "$NEW_LOOP_VIDEO" "$NEW_LOOP_AUDIO" "$NEW_RELAY_VIDEO" "$NEW_RELAY_AUDIO" \
         "$CMD_OWNCAST"; do spawn "$c"; done
sleep 0.5

echo "== each pattern matches both forms of its own leg, and nothing else"
check "PAT_LOOP_VIDEO  count"  "$(pids_matching "$PAT_LOOP_VIDEO"  | wc -l)" 2
check "PAT_LOOP_AUDIO  count"  "$(pids_matching "$PAT_LOOP_AUDIO"  | wc -l)" 2
check "PAT_RELAY_VIDEO count"  "$(pids_matching "$PAT_RELAY_VIDEO" | wc -l)" 2
check "PAT_RELAY_AUDIO count"  "$(pids_matching "$PAT_RELAY_AUDIO" | wc -l)" 2

echo "== matched processes are the intended ones"
matches() {  # matches <pattern> <expected substring> <label>
    local n=0 pid
    for pid in $(pids_matching "$1"); do
        tr '\0' ' ' < /proc/"$pid"/cmdline 2>/dev/null | grep -qF -- "$2" && n=$((n+1))
    done
    check "$3" "$n" 2
}
matches "$PAT_LOOP_VIDEO"  "loop.mp4 -c copy"              "loop video legs carry -c copy"
matches "$PAT_LOOP_AUDIO"  "loop.mp4 -vn"                  "loop audio legs carry -vn"
matches "$PAT_RELAY_VIDEO" "live/$K -map 0:v"              "relay video legs read 1935 and map video"
matches "$PAT_RELAY_AUDIO" "live/$K -vn"                   "relay audio legs read 1935 and drop video"

echo "== Owncast's transcoder is never matched by any pattern"
hits=0
for p in "$PAT_LOOP_VIDEO" "$PAT_LOOP_AUDIO" "$PAT_RELAY_VIDEO" "$PAT_RELAY_AUDIO"; do
    for pid in $(pids_matching "$p"); do
        tr '\0' ' ' < /proc/"$pid"/cmdline 2>/dev/null | grep -q 'pipe:0' && hits=$((hits+1))
    done
done
check "owncast transcoder untouched" "$hits" 0

echo "== record_pid writes a pid that is really running"
record_pid "$PAT_LOOP_VIDEO" "$VSPOT_HOME/loop.pid"
if kill -0 "$(cat "$VSPOT_HOME/loop.pid")" 2>/dev/null; then ok "loop.pid names a live process"; else bad "loop.pid names a dead process"; fi

echo "== the 2026-09-03 bug: a stale pidfile must not shield an orphan"
echo 999999 > "$VSPOT_HOME/loop.pid"
kill_pattern "$PAT_LOOP_VIDEO" "loop video" "$LOG"
check "both orphaned loop legs killed" "$(pids_matching "$PAT_LOOP_VIDEO" | wc -l)" 0
check "loop audio untouched"           "$(pids_matching "$PAT_LOOP_AUDIO" | wc -l)" 2
check "relays untouched"               "$(pids_matching "$PAT_RELAY_VIDEO" | wc -l)" 2

echo "== kill_pattern is a no-op when nothing matches, and returns success"
if kill_pattern "$PAT_LOOP_VIDEO" "loop video" "$LOG"; then ok "no-op returns 0"; else bad "no-op returned non-zero"; fi

echo "== record_pid clears the pidfile once the process is gone"
record_pid "$PAT_LOOP_VIDEO" "$VSPOT_HOME/loop.pid"
if [ -f "$VSPOT_HOME/loop.pid" ]; then bad "stale pidfile left behind"; else ok "stale pidfile removed"; fi

echo "== service probes fail safe, and within their timeout, when nothing answers"
check "owncast_status when down" "$(OWNCAST_API=http://127.0.0.1:9 owncast_status)" "unknown -"
if ICECAST_PORT=9 icecast_has_source; then bad "icecast_has_source true with no server"; else ok "icecast_has_source false when down"; fi
t0=$(date +%s)
if OWNCAST_API=http://127.0.0.1:9 wait_owncast_publisher "$(utc_mark)" 5; then bad "wait_owncast_publisher true with no server"; else ok "wait_owncast_publisher false when down"; fi
el=$(( $(date +%s) - t0 ))
if [ "$el" -le 15 ]; then ok "wait honours its timeout (${el}s for a 5s budget)"; else bad "wait overran: ${el}s for a 5s budget"; fi

echo "== utc_mark format and ordering"
m=$(utc_mark)
if [[ $m =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then ok "utc_mark format"; else bad "utc_mark format: $m"; fi
if [[ "$(utc_mark 0)" > "$(utc_mark 600)" ]]; then ok "timestamps compare lexicographically"; else bad "timestamp comparison broken"; fi


echo "== regression: pids_matching reports failure when nothing matches"
# A bare `for` loop over no items returns 0, which reads as "found" and made
# start_loop.sh believe a loop was running when none was.
if pids_matching 'no-such-process-anywhere' >/dev/null; then
    bad "pids_matching returned success with no match"
else
    ok "pids_matching returns non-zero with no match"
fi
spawn "$NEW_LOOP_AUDIO"
if pids_matching "$PAT_LOOP_AUDIO" >/dev/null; then ok "pids_matching returns zero on a match"; else bad "pids_matching returned failure on a match"; fi

echo "== regression: a background child must not inherit the lock on fd 9"
# The first build of this rewrite launched ffmpeg without 9>&-, so every relay
# held the lock for its whole life and on_publish_done blocked behind the very
# process it was trying to kill.
LOCKFILE=$VSPOT_HOME/stream.lock
(
    exec 9> "$LOCKFILE"
    flock -n 9 || exit 1
    setsid bash -c "exec -a \"$NEW_RELAY_VIDEO\" \"$FAKE\" 60" 9>&- &
    echo $! > "$VSPOT_HOME/child.pid"
    sleep 0.5
)
CHILD=$(cat "$VSPOT_HOME/child.pid"); SPAWNED+=("$CHILD")
if [ -e /proc/"$CHILD"/fd/9 ]; then bad "child inherited fd 9"; else ok "child did not inherit fd 9"; fi
if flock -n "$LOCKFILE" true; then ok "lock is free once the script exits"; else bad "lock still held by the child"; fi

echo "== wait_mount_live reports the process exiting rather than waiting it out"
# Exit code 2 means "died immediately, retry now" and is what turns a 90-second
# relay startup into a few seconds.
# Clear the relay-audio fakes spawned earlier, so exactly one leg is in play.
kill_pattern "$PAT_RELAY_AUDIO" "relay audio" "$LOG"
spawn "$NEW_RELAY_AUDIO"
RPID=$(pids_matching "$PAT_RELAY_AUDIO" | head -1)
( sleep 2; kill -9 "$RPID" 2>/dev/null ) &
t0=$(date +%s)
ICECAST_PORT=9 wait_mount_live "$PAT_RELAY_AUDIO" 30; rc=$?
el=$(( $(date +%s) - t0 ))
check "wait_mount_live returns 2 on process death" "$rc" 2
if [ "$el" -le 12 ]; then ok "it noticed within ${el}s instead of waiting 30"; else bad "took ${el}s to notice"; fi

echo "== a shell that merely mentions the pattern is never a target"
setsid bash -c "sleep 60 # $NEW_LOOP_VIDEO" & DECOY=$!; SPAWNED+=("$DECOY"); sleep 0.4
spawn "$NEW_LOOP_VIDEO"
kill_pattern "$PAT_LOOP_VIDEO" "loop video" "$LOG"
if kill -0 "$DECOY" 2>/dev/null; then ok "decoy shell survived"; else bad "decoy shell was killed"; fi
check "the real leg was still killed" "$(pids_matching "$PAT_LOOP_VIDEO" | wc -l)" 0

cleanup
echo
echo "passed: $pass   failed: $fail"
[ "$fail" = 0 ]
