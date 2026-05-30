#!/bin/bash
# Fired by nginx-rtmp when OBS connects and starts publishing.
# Kills the loop, then relays OBS feed from nginx-rtmp → Owncast.
source /home/vspot/owncast.conf
INCOMING=$1

# Kill existing loop
if [ -f /home/vspot/loop.pid ]; then
    kill "$(cat /home/vspot/loop.pid)" 2>/dev/null
    rm -f /home/vspot/loop.pid
fi

# Kill any stale relay
if [ -f /home/vspot/relay.pid ]; then
    kill "$(cat /home/vspot/relay.pid)" 2>/dev/null
    rm -f /home/vspot/relay.pid
fi

# Wait for Owncast to release the previous connection
sleep 2

# Relay OBS feed from nginx-rtmp to Owncast
# -map 0:v -map 0:a ensures video is stream 0 (required by FLV/RTMP)
ffmpeg -i "rtmp://localhost:1935/live/$INCOMING" \
    -map 0:v -map 0:a -c copy -f flv "$OWNCAST_RTMP/$STREAM_KEY" \
    >> /home/vspot/relay.log 2>&1 &
echo $! > /home/vspot/relay.pid
