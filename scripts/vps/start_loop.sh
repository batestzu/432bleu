#!/bin/bash
# Starts the house loop: video -> Owncast, audio -> Icecast, so the venue is
# never dark and never silent between shows.
#
# Safe to run at any time, and idempotent: if a healthy loop is already
# publishing it says so and exits. Legs are found by command pattern, so a
# stale pidfile can no longer orphan a running loop (see stream_lib.sh).
#
#   start_loop.sh            start if not already healthy
#   start_loop.sh --force    always tear down and restart

source /home/vspot/owncast.conf
source /home/vspot/stream_lib.sh

LOG=$VSPOT_HOME/loop.log
FFLOG=$VSPOT_HOME/loop_ffmpeg.log
FORCE=0
[ "$1" = "--force" ] && FORCE=1

# Serialize against on_publish/on_publish_done. They set STREAM_LOCK_HELD
# because they already hold it; taking it again here would deadlock.
if [ "${STREAM_LOCK_HELD:-0}" != "1" ]; then
    exec 9> "$VSPOT_HOME/stream.lock"
    flock -w 30 9 || { slog "$LOG" "start_loop: lock busy for 30s, aborting"; exit 1; }
fi

# Already healthy? Leave it alone rather than punching a gap in the bed.
if [ "$FORCE" = "0" ] && pids_matching "$PAT_LOOP_VIDEO" >/dev/null; then
    read -r online _ <<< "$(owncast_status)"
    if [ "$online" = "true" ]; then
        record_pid "$PAT_LOOP_VIDEO" "$VSPOT_HOME/loop.pid"
        record_pid "$PAT_LOOP_AUDIO" "$VSPOT_HOME/loop_audio.pid"
        slog "$LOG" "loop already publishing, nothing to do"
        echo "Loop already running (PID: $(cat "$VSPOT_HOME/loop.pid" 2>/dev/null))"
        exit 0
    fi
    slog "$LOG" "loop process alive but Owncast is not online, restarting it"
fi

kill_pattern "$PAT_LOOP_VIDEO" "house loop video" "$LOG"
kill_pattern "$PAT_LOOP_AUDIO" "house loop audio" "$LOG"
rm -f "$VSPOT_HOME/loop.pid" "$VSPOT_HOME/loop_audio.pid"

# --- video leg -> Owncast ----------------------------------------------------
# Success is Owncast reporting a fresh publisher, not ffmpeg being alive.
# 9>&- so the child does not inherit (and hold) the lock — see stream_lib.sh.
started=0
for attempt in 1 2 3 4; do
    MARK=$(utc_mark)
    setsid ffmpeg -nostdin -nostats -loglevel warning \
        -re -stream_loop -1 -i "$VSPOT_HOME/loop.mp4" \
        -c copy -f flv "$OWNCAST_RTMP/$STREAM_KEY" \
        >> "$FFLOG" 2>&1 9>&- &
    sleep 1
    record_pid "$PAT_LOOP_VIDEO" "$VSPOT_HOME/loop.pid"

    wait_relay_live "$PAT_LOOP_VIDEO" "$MARK" 20; rc=$?
    if [ "$rc" = "0" ]; then
        slog "$LOG" "loop video publishing (attempt $attempt, pid $(cat "$VSPOT_HOME/loop.pid" 2>/dev/null))"
        echo "Loop started (PID: $(cat "$VSPOT_HOME/loop.pid" 2>/dev/null))"
        started=1
        break
    fi

    if [ "$rc" = "2" ]; then
        slog "$LOG" "loop video attempt $attempt exited immediately (Owncast slot still busy?), retrying"
    else
        slog "$LOG" "loop video attempt $attempt alive but Owncast never saw it, retrying"
        kill_pattern "$PAT_LOOP_VIDEO" "house loop video" "$LOG"
    fi
    sleep 3
done

if [ "$started" = "0" ]; then
    slog "$LOG" "ERROR: loop video never reached Owncast after 3 attempts"
    echo "Loop FAILED to reach Owncast — see $LOG" >&2
fi

# --- audio leg -> Icecast ----------------------------------------------------
# No-op until ICECAST_SOURCE_PASSWORD is set in owncast.conf.
# Icecast allows one source per mount, so on_publish.sh kills this leg before
# the show's audio relay takes /live.mp3.
if [ -n "${ICECAST_SOURCE_PASSWORD:-}" ]; then
    for attempt in 1 2 3; do
        setsid ffmpeg -nostdin -nostats -loglevel warning \
            -re -stream_loop -1 -i "$VSPOT_HOME/loop.mp4" -vn -c:a libmp3lame -b:a 128k \
            -content_type audio/mpeg -f mp3 \
            "icecast://source:$ICECAST_SOURCE_PASSWORD@127.0.0.1:$ICECAST_PORT/live.mp3" \
            >> "$VSPOT_HOME/loop_audio.log" 2>&1 9>&- &
        sleep 1
        record_pid "$PAT_LOOP_AUDIO" "$VSPOT_HOME/loop_audio.pid"

        wait_mount_live "$PAT_LOOP_AUDIO" 12; rc=$?
        if [ "$rc" = "0" ]; then
            slog "$LOG" "loop audio mounted on /live.mp3 (attempt $attempt, pid $(cat "$VSPOT_HOME/loop_audio.pid" 2>/dev/null))"
            echo "Loop audio started (PID: $(cat "$VSPOT_HOME/loop_audio.pid" 2>/dev/null))"
            break
        fi

        [ "$rc" = "1" ] && kill_pattern "$PAT_LOOP_AUDIO" "house loop audio" "$LOG"
        slog "$LOG" "loop audio attempt $attempt did not mount, retrying"
        sleep 2
        [ "$attempt" = "3" ] && slog "$LOG" "ERROR: loop audio never mounted — the venue bed is SILENT"
    done
else
    slog "$LOG" "loop audio skipped (no ICECAST_SOURCE_PASSWORD)"
fi

[ "$started" = "1" ]
