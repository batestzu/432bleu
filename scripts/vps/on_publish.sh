#!/bin/bash
# Fired by nginx-rtmp when OBS connects and starts publishing.
# Stops the house loop, then relays the OBS feed from nginx-rtmp to Owncast
# (video) and Icecast (audio, so the venue's playAudio zones carry the show).
#
# Success is measured against Owncast and Icecast, never against ffmpeg being
# alive: on 2026-09-03 a refused relay stayed alive long enough to pass the old
# three-second liveness check, and this script logged "relay running" for the
# whole event while the audience watched the house loop. See stream_lib.sh.

source /home/vspot/owncast.conf
source /home/vspot/stream_lib.sh

INCOMING=$1
LOG=$VSPOT_HOME/relay.log
FFLOG=$VSPOT_HOME/relay_ffmpeg.log

slog "$LOG" "publish started (name=$INCOMING)"

# Refuse unknown stream keys. nginx-rtmp's exec_publish cannot reject the TCP
# publisher itself, but exiting here means an unknown key is never relayed to
# Owncast or Icecast — the house loop just keeps playing over it.
if [ -n "${STREAM_KEY:-}" ] && [ "$INCOMING" != "$STREAM_KEY" ]; then
    slog "$LOG" "REFUSED unknown stream key '$INCOMING'"
    exit 1
fi

# Serialize against start_loop.sh and on_publish_done.sh. Children inherit the
# guard so the fallback below does not deadlock on our own lock.
#
# Waits generously: on_publish_done can hold the lock for a couple of minutes
# while it restores the loop, and if a performer reconnects during that window
# the show is what matters. Giving up leaves the house loop playing, which is
# safe but means an OBS stop/start to try again.
exec 9> "$VSPOT_HOME/stream.lock"
flock -w 120 9 || { slog "$LOG" "lock busy for 120s, aborting — the house loop keeps playing"; exit 1; }
export STREAM_LOCK_HELD=1

# Owncast accepts one publisher and the loop is holding it. Wait for the
# connection to really be gone, not just for kill() to return.
kill_pattern "$PAT_LOOP_VIDEO" "house loop video" "$LOG"
kill_pattern "$PAT_LOOP_AUDIO" "house loop audio" "$LOG"
kill_pattern "$PAT_RELAY_VIDEO" "stale video relay" "$LOG"
kill_pattern "$PAT_RELAY_AUDIO" "stale audio relay" "$LOG"
rm -f "$VSPOT_HOME/loop.pid" "$VSPOT_HOME/loop_audio.pid"

sleep 2   # let Owncast notice the closed connection

# --- audio leg -> Icecast ----------------------------------------------------
start_audio_relay() {
    [ -n "${ICECAST_SOURCE_PASSWORD:-}" ] || { slog "$LOG" "icecast leg skipped (no ICECAST_SOURCE_PASSWORD)"; return 0; }
    local attempt rc
    for attempt in 1 2 3 4; do
        ffmpeg -nostdin -nostats -loglevel warning \
            -i "rtmp://localhost:1935/live/$INCOMING" -vn -c:a libmp3lame -b:a 128k \
            -content_type audio/mpeg -f mp3 \
            "icecast://source:$ICECAST_SOURCE_PASSWORD@127.0.0.1:$ICECAST_PORT/live.mp3" \
            >> "$VSPOT_HOME/audio_relay.log" 2>&1 9>&- &
        sleep 1
        record_pid "$PAT_RELAY_AUDIO" "$VSPOT_HOME/audio_relay.pid"

        wait_mount_live "$PAT_RELAY_AUDIO" 12; rc=$?
        if [ "$rc" = "0" ]; then
            slog "$LOG" "audio relay mounted on /live.mp3 (attempt $attempt, pid $(cat "$VSPOT_HOME/audio_relay.pid" 2>/dev/null))"
            return 0
        fi
        [ "$rc" = "1" ] && kill_pattern "$PAT_RELAY_AUDIO" "audio relay" "$LOG"
        slog "$LOG" "audio relay attempt $attempt did not mount, retrying"
        sleep 2
    done

    # Better a music bed than silence: put the loop's audio leg back on the
    # mount. Video is unaffected either way.
    slog "$LOG" "AUDIO RELAY FAILED — restoring loop audio so the venue is not silent"
    setsid ffmpeg -nostdin -nostats -loglevel warning \
        -re -stream_loop -1 -i "$VSPOT_HOME/loop.mp4" -vn -c:a libmp3lame -b:a 128k \
        -content_type audio/mpeg -f mp3 \
        "icecast://source:$ICECAST_SOURCE_PASSWORD@127.0.0.1:$ICECAST_PORT/live.mp3" \
        >> "$VSPOT_HOME/loop_audio.log" 2>&1 9>&- &
    sleep 1
    record_pid "$PAT_LOOP_AUDIO" "$VSPOT_HOME/loop_audio.pid"
    return 1
}

# --- video leg -> Owncast ----------------------------------------------------
# -map 0:v -map 0:a puts video in stream 0, which FLV/RTMP requires.
#
# Keep trying for two minutes rather than a fixed number of attempts. nginx-rtmp
# cannot serve a player until the publisher has pushed enough of a stream, and
# how long that takes depends on the encoder at the other end, so an attempt
# that dies instantly is expected early and costs about a second to detect.
DEADLINE=$(( $(date +%s) + 120 ))
attempt=0
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
    attempt=$((attempt + 1))
    MARK=$(utc_mark)
    ffmpeg -nostdin -nostats -loglevel warning \
        -i "rtmp://localhost:1935/live/$INCOMING" \
        -map 0:v -map 0:a -c copy -f flv "$OWNCAST_RTMP/$STREAM_KEY" \
        >> "$FFLOG" 2>&1 9>&- &
    sleep 1
    record_pid "$PAT_RELAY_VIDEO" "$VSPOT_HOME/relay.pid"

    wait_relay_live "$PAT_RELAY_VIDEO" "$MARK" 25; rc=$?
    if [ "$rc" = "0" ]; then
        slog "$LOG" "relay LIVE on Owncast (attempt $attempt, pid $(cat "$VSPOT_HOME/relay.pid" 2>/dev/null))"
        start_audio_relay
        exit 0
    fi

    if [ "$rc" = "2" ]; then
        slog "$LOG" "relay attempt $attempt exited (nginx-rtmp input not ready yet), retrying"
        sleep 2
    else
        slog "$LOG" "relay attempt $attempt alive but Owncast never saw it, retrying"
        kill_pattern "$PAT_RELAY_VIDEO" "video relay" "$LOG"
        sleep 3
    fi
done

# Never leave Owncast with no input. The performer is still publishing to
# nginx-rtmp at this point, so recovering needs an OBS stop/start, which
# re-fires this script.
slog "$LOG" "RELAY FAILED after $attempt attempts in 120s — falling back to the house loop"
"$VSPOT_HOME/start_loop.sh" --force
