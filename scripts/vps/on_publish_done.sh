#!/bin/bash
# Fired by nginx-rtmp when OBS disconnects (including when
# drop_idle_publisher cuts a stalled uplink loose).
# Tears down the relay legs and puts the house loop back.

source /home/vspot/stream_lib.sh

LOG=$VSPOT_HOME/loop.log
slog "$LOG" "on_publish_done fired"

# Serialize against on_publish.sh and start_loop.sh, and pass the guard down so
# start_loop.sh does not deadlock on the lock we hold.
#
# on_publish gives itself a 120s budget to establish a relay, so wait longer
# than that. If the lock is still held after all of it something is wedged, and
# then we go ahead anyway: this script is the venue's recovery path, and a
# missed restart leaves Owncast dark and the bed silent until a human notices.
exec 9> "$VSPOT_HOME/stream.lock"
flock -w 150 9 || slog "$LOG" "WARNING: lock still held after 150s, proceeding without it"
export STREAM_LOCK_HELD=1

# Both legs usually die on their own when the OBS input closes. Kill by pattern
# anyway: a relay whose input stalled can sit for minutes holding Owncast's
# publisher slot and Icecast's mount, which blocks the loop from coming back.
kill_pattern "$PAT_RELAY_VIDEO" "video relay" "$LOG"
kill_pattern "$PAT_RELAY_AUDIO" "audio relay" "$LOG"
rm -f "$VSPOT_HOME/relay.pid" "$VSPOT_HOME/audio_relay.pid"

sleep 5   # let Owncast release the publisher slot

# start_loop.sh verifies against Owncast and retries internally; a second call
# after a success is a no-op, so two attempts here is enough.
for attempt in 1 2; do
    if "$VSPOT_HOME/start_loop.sh" --force; then
        slog "$LOG" "house loop restored (attempt $attempt)"
        exit 0
    fi
    slog "$LOG" "loop restart attempt $attempt failed, retrying"
    sleep 5
done

slog "$LOG" "ERROR: house loop did not come back — Owncast is dark, check $VSPOT_HOME/loop.log"
exit 1
