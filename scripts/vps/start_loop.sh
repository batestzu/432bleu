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
