#!/bin/bash
# Fired by nginx-rtmp when OBS disconnects (including when
# drop_idle_publisher cuts a stalled uplink loose).
# Tears down the relay legs and hands the venue back to the house loop.
#
# Reworked 2026-11-16, after show #23 lost its uplink five times on venue WiFi.
# Every drop spent ~45 s before the house loop was even up:
#   * 24 s waiting on two relays that never act on SIGTERM, one after the other;
#   * a fixed 5 s sleep, then ~13 s for the loop to reach Owncast;
#   * then the supervisor killed that loop and started it again (~14 s of
#     black), because a loop started here lives in nginx's cgroup.
# Now the relays get 2 s, both at once, and the loop is started ONCE, by the
# supervisor, in its own cgroup. Starting it here survives only as a fallback
# for when the supervisor does not do it.

VSPOT_HOME=${VSPOT_HOME:-/home/vspot}
source "$VSPOT_HOME/owncast.conf"
source "$VSPOT_HOME/stream_lib.sh"

LOG=$VSPOT_HOME/loop.log
FIRED=$(now_ns)
NAME=${1:-}     # nginx passes $name once rtmp.conf asks it to; empty before that
HANDOFF_WAIT=${HANDOFF_WAIT:-45}

slog "$LOG" "on_publish_done fired"

# on_publish refuses a wrong key and never relays it. When that publisher
# leaves, the show that IS on air must not be torn down.
if [ -n "$NAME" ] && [ -n "${STREAM_KEY:-}" ] && [ "$NAME" != "$STREAM_KEY" ]; then
    slog "$LOG" "unknown publisher (key #$(key_tag "$NAME")) left, show untouched"
    exit 0
fi

# Serialize against on_publish.sh, start_loop.sh and the supervisor.
#
# on_publish gives itself a 120s budget to establish a relay, so wait longer
# than that. If the lock is still held after all of it something is wedged, and
# then we go ahead anyway: this script is the venue's recovery path, and a
# missed restart leaves Owncast dark and the bed silent until a human notices.
exec 9> "$VSPOT_HOME/stream.lock"
flock -w 150 9 || slog "$LOG" "WARNING: lock still held after 150s, proceeding without it"

# OBS reconnected and its on_publish got the lock first. The relays running now
# are the NEW ones. See published_since in stream_lib.sh.
if published_since "$FIRED"; then
    slog "$LOG" "OBS already reconnected, leaving its relay alone"
    exit 0
fi

# The publisher is gone, so the relays have nothing left to flush, and a relay
# blocked on a stalled input can hold Owncast's publisher slot and Icecast's
# mount for minutes. Two seconds, then SIGKILL, both legs at once.
kill_pattern "$PAT_RELAY_VIDEO" "video relay" "$LOG" 2 &
kill_pattern "$PAT_RELAY_AUDIO" "audio relay" "$LOG" 2 &
wait
rm -f "$VSPOT_HOME/relay.pid" "$VSPOT_HOME/audio_relay.pid"

# Hand over. The supervisor (432bleu-houseloop.service) needs the lock to start
# the loop, so let go of it entirely.
flock -u 9
exec 9>&-

# The supervisor polls every few seconds and starts the loop once Owncast shows
# the relay's slot is free. Watch for that, or for OBS coming back first.
deadline=$(( $(date +%s) + HANDOFF_WAIT ))
while [ "$(date +%s)" -lt "$deadline" ]; do
    if relay_running; then
        slog "$LOG" "OBS came back before the loop started, nothing to do"
        exit 0
    fi
    if pids_matching "$PAT_LOOP_VIDEO" >/dev/null; then
        slog "$LOG" "house loop handed to the supervisor"
        exit 0
    fi
    sleep 1
done

# Fallback: the supervisor did not start the loop. Maybe it is down. Start it
# here, as before 2026-11-16. If the supervisor is alive after all, it re-homes
# this loop into its own cgroup later. That costs a short gap, but the venue is
# never left dark.
slog "$LOG" "WARNING: no house loop ${HANDOFF_WAIT}s after the drop (is 432bleu-houseloop running?), starting it here"
exec 9> "$VSPOT_HOME/stream.lock"
flock -w 150 9 || slog "$LOG" "WARNING: lock still held after 150s, proceeding without it"
export STREAM_LOCK_HELD=1

if relay_running || pids_matching "$PAT_LOOP_VIDEO" >/dev/null; then
    slog "$LOG" "something took the slot while we waited for the lock, nothing to do"
    exit 0
fi

# start_loop.sh verifies against Owncast and retries internally; a second call
# after a success is a no-op, so two attempts here is enough.
for attempt in 1 2; do
    if "$VSPOT_HOME/start_loop.sh" --force; then
        slog "$LOG" "house loop restored by fallback (attempt $attempt)"
        exit 0
    fi
    slog "$LOG" "loop restart attempt $attempt failed, retrying"
    sleep 5
done

slog "$LOG" "ERROR: house loop did not come back — Owncast is dark, check $VSPOT_HOME/loop.log"
exit 1
