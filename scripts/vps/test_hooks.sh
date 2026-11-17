#!/bin/bash
# Runs the REAL on_publish_done.sh against fake ffmpeg processes in a temp
# VSPOT_HOME. Each scenario below is a case that has gone wrong, or could,
# during a show. Runs anywhere and touches nothing real: no Owncast, no Icecast,
# no nginx, and start_loop.sh is a stub that only records that it was called.
#
#   bash scripts/vps/test_hooks.sh
#
# Never run it while a real relay is up on the same machine: the patterns would
# match the real legs too. On the VPS that means never during a show.
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
T=$(mktemp -d)
export VSPOT_HOME=$T
export OWNCAST_API=http://127.0.0.1:9 ICECAST_PORT=9

K=TESTKEYdoNotUseAnywhere0123456789
cp "$HERE/stream_lib.sh" "$T/stream_lib.sh"
printf 'STREAM_KEY=%s\nOWNCAST_RTMP=rtmp://127.0.0.1:9/live\n' "$K" > "$T/owncast.conf"

FAKE=$T/bin/ffmpeg
mkdir -p "$T/bin" && cp /bin/sleep "$FAKE"
NEW='-nostdin -nostats -loglevel warning'
RELAY_VIDEO="ffmpeg $NEW -i rtmp://localhost:1935/live/$K -map 0:v -map 0:a -c copy -f flv rtmp://127.0.0.1:9/live/$K"
RELAY_AUDIO="ffmpeg $NEW -i rtmp://localhost:1935/live/$K -vn -c:a libmp3lame -b:a 128k -content_type audio/mpeg -f mp3 icecast://source:pw@127.0.0.1:9/live.mp3"
LOOP_VIDEO="ffmpeg $NEW -re -stream_loop -1 -i $T/loop.mp4 -c copy -f flv rtmp://127.0.0.1:9/live/$K"

# spawn <cmdline> [deaf]  — deaf fakes ignore SIGTERM, like a relay blocked on a
# dead input. Ignored signals survive exec.
spawn() {
    local trap=""
    [ "${2:-}" = deaf ] && trap="trap '' TERM;"
    setsid bash -c "$trap exec -a \"$1\" \"$FAKE\" 300" 8>&- 9>&- &
    echo $! >> "$T/spawned"
    disown 2>/dev/null
    sleep 0.15
}
export -f spawn; export FAKE T

# The stub stands in for start_loop.sh: it records the call and puts a fake loop up.
cat > "$T/start_loop.sh" <<EOF
#!/bin/bash
echo called >> "$T/start_loop.called"
spawn "$LOOP_VIDEO"
exit 0
EOF
chmod +x "$T/start_loop.sh"

source "$T/stream_lib.sh"
pass=0; fail=0
ok()   { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }
check(){ if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (got '$2', want '$3')"; fi; }
count(){ pids_matching "$1" | wc -l; }

reset() {
    [ -f "$T/spawned" ] && kill -9 $(cat "$T/spawned") 2>/dev/null
    cat "$T/loop.log" >> "$T/all_runs.log" 2>/dev/null
    rm -f "$T/spawned" "$T/start_loop.called" "$T/loop.log" "$T/last_publish"
    sleep 0.3
}
trap 'reset; rm -rf "$T"' EXIT

# A stand-in for 432bleu-houseloop.service: once the relays are gone and the
# lock is free, start the loop.
fake_supervisor() {
    (
        for _ in $(seq 1 100); do
            relay_running || break
            sleep 0.2
        done
        sleep 1
        flock -w 20 "$T/stream.lock" true
        spawn "$LOOP_VIDEO"
    ) &
}

hook() { bash "$HERE/on_publish_done.sh" "$@"; }

echo "== 1. mid-show drop, supervisor up: relays gone fast, loop started ONCE, by the supervisor"
reset
spawn "$RELAY_VIDEO" deaf; spawn "$RELAY_AUDIO" deaf
fake_supervisor
t0=$(date +%s)
HANDOFF_WAIT=15 hook; rc=$?
el=$(( $(date +%s) - t0 ))
check "exit code" "$rc" 0
check "relays gone" "$(count "$PAT_RELAY_VIDEO")$(count "$PAT_RELAY_AUDIO")" 00
check "exactly one loop" "$(count "$PAT_LOOP_VIDEO")" 1
if [ -f "$T/start_loop.called" ]; then bad "hook started the loop itself"; else ok "hook left the loop to the supervisor"; fi
grep -q "house loop handed to the supervisor" "$T/loop.log" && ok "logged the hand-off" || bad "no hand-off line in log"
if [ "$el" -le 8 ]; then ok "whole hand-off took ${el}s (was ~45s before the rework)"; else bad "hand-off took ${el}s"; fi

echo "== 2. supervisor down: the hook falls back to starting the loop itself"
reset
spawn "$RELAY_VIDEO" deaf; spawn "$RELAY_AUDIO" deaf
HANDOFF_WAIT=3 hook; rc=$?
check "exit code" "$rc" 0
check "start_loop.sh called once" "$(cat "$T/start_loop.called" 2>/dev/null | wc -l)" 1
check "loop up" "$(count "$PAT_LOOP_VIDEO")" 1
grep -q "WARNING: no house loop 3s after the drop" "$T/loop.log" && ok "logged the fallback warning" || bad "no fallback warning in log"

echo "== 3. OBS reconnected and its on_publish won the lock: the NEW relay is left alone"
reset
spawn "$RELAY_VIDEO" deaf; spawn "$RELAY_AUDIO" deaf      # the old, dead relays
exec 8> "$T/stream.lock"; flock 8                          # on_publish holds the lock...
HANDOFF_WAIT=3 hook 8>&- & HOOK=$!
sleep 0.5
stamp_publish                                              # ...stamped after the drop fired...
kill -9 $(cat "$T/spawned"); rm -f "$T/spawned"            # ...killed the stale relays...
spawn "$RELAY_VIDEO"; spawn "$RELAY_AUDIO"                 # ...and brought the new one up
flock -u 8; exec 8>&-
wait $HOOK; rc=$?
check "exit code" "$rc" 0
check "new relay still up" "$(count "$PAT_RELAY_VIDEO")$(count "$PAT_RELAY_AUDIO")" 11
check "no loop over the live show" "$(count "$PAT_LOOP_VIDEO")" 0
grep -q "OBS already reconnected" "$T/loop.log" && ok "logged the stand-down" || bad "no stand-down line in log"

echo "== 4. a publisher with the WRONG key leaves: the show on air is untouched"
reset
spawn "$RELAY_VIDEO"; spawn "$RELAY_AUDIO"
HANDOFF_WAIT=3 hook "not-the-key-xyz"; rc=$?
check "exit code" "$rc" 0
check "show relay untouched" "$(count "$PAT_RELAY_VIDEO")$(count "$PAT_RELAY_AUDIO")" 11
grep -q "unknown publisher (key #" "$T/loop.log" && ok "logged by fingerprint" || bad "no unknown-publisher line"
if grep -q "not-the-key-xyz" "$T/loop.log"; then bad "the raw key reached the log"; else ok "the raw key is not in the log"; fi

echo "== 5. the RIGHT key, passed by nginx, still tears down as normal"
reset
spawn "$RELAY_VIDEO" deaf; spawn "$RELAY_AUDIO" deaf
HANDOFF_WAIT=3 hook "$K"; rc=$?
check "relays gone" "$(count "$PAT_RELAY_VIDEO")$(count "$PAT_RELAY_AUDIO")" 00
check "fallback loop up" "$(count "$PAT_LOOP_VIDEO")" 1

echo "== 6. OBS comes back before the supervisor starts the loop: nothing to do"
reset
spawn "$RELAY_VIDEO" deaf; spawn "$RELAY_AUDIO" deaf
( for _ in $(seq 1 50); do relay_running || break; sleep 0.2; done; sleep 0.5
  spawn "$RELAY_VIDEO"; spawn "$RELAY_AUDIO" ) &
HANDOFF_WAIT=10 hook; rc=$?
check "exit code" "$rc" 0
check "no loop started" "$(count "$PAT_LOOP_VIDEO")" 0
if [ -f "$T/start_loop.called" ]; then bad "fallback ran anyway"; else ok "no fallback"; fi
grep -q "OBS came back before the loop started" "$T/loop.log" && ok "logged it" || bad "no line in log"

echo "== no scenario wrote the real key to any log"
cat "$T/loop.log" >> "$T/all_runs.log" 2>/dev/null
if grep -qF "$K" "$T/all_runs.log"; then bad "key found in a log"; else ok "no key in any log"; fi

echo
echo "passed: $pass   failed: $fail"
[ "$fail" = 0 ]
