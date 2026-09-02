#!/bin/bash
# Starts (or restarts) the Owncast loop video.
# Safe to run at any time — kills any existing loop first.
source /home/vspot/owncast.conf

if [ -f /home/vspot/loop.pid ]; then
    kill "$(cat /home/vspot/loop.pid)" 2>/dev/null
    rm -f /home/vspot/loop.pid
fi

setsid ffmpeg -re -stream_loop -1 -i /home/vspot/loop.mp4 \
    -c copy -f flv "$OWNCAST_RTMP/$STREAM_KEY" \
    >> /home/vspot/loop.log 2>&1 &
echo $! > /home/vspot/loop.pid
echo "Loop started (PID: $!)"

# Audio leg: the same loop file into Icecast, so the lobby/bar playAudio zones
# are never silent between shows. No-op until ICECAST_SOURCE_PASSWORD is set
# in owncast.conf. Killed by on_publish.sh when a show takes the mountpoint.
if [ -f /home/vspot/loop_audio.pid ]; then
    kill "$(cat /home/vspot/loop_audio.pid)" 2>/dev/null
    rm -f /home/vspot/loop_audio.pid
fi
if [ -n "$ICECAST_SOURCE_PASSWORD" ]; then
    setsid ffmpeg -re -stream_loop -1 -i /home/vspot/loop.mp4 -vn -c:a libmp3lame -b:a 128k \
        -content_type audio/mpeg -f mp3 \
        "icecast://source:$ICECAST_SOURCE_PASSWORD@127.0.0.1:${ICECAST_PORT:-8005}/live.mp3" \
        >> /home/vspot/loop_audio.log 2>&1 &
    echo $! > /home/vspot/loop_audio.pid
    echo "Loop audio started (PID: $(cat /home/vspot/loop_audio.pid))"
fi
