#!/bin/bash
# Fired by nginx-rtmp when OBS disconnects.
# Cleans up the relay and restarts the loop.

echo "[$(date)] on_publish_done fired" >> /home/vspot/loop.log

# Kill relay (it likely already died when OBS input closed, but clean up)
if [ -f /home/vspot/relay.pid ]; then
    kill "$(cat /home/vspot/relay.pid)" 2>/dev/null
    rm -f /home/vspot/relay.pid
fi

# Kill the Icecast audio leg alongside it
if [ -f /home/vspot/audio_relay.pid ]; then
    kill "$(cat /home/vspot/audio_relay.pid)" 2>/dev/null
    rm -f /home/vspot/audio_relay.pid
fi

sleep 8

# Retry up to 5 times in case Owncast hasn't fully released yet
for i in 1 2 3 4 5; do
    /home/vspot/start_loop.sh
    sleep 2
    if [ -f /home/vspot/loop.pid ] && kill -0 "$(cat /home/vspot/loop.pid)" 2>/dev/null; then
        echo "[$(date)] Loop running (attempt $i)" >> /home/vspot/loop.log
        break
    fi
    echo "[$(date)] Loop start attempt $i failed, retrying..." >> /home/vspot/loop.log
    sleep 3
done
