#!/bin/bash
# Fired by nginx-rtmp when OBS disconnects.
# Cleans up the relay and restarts the loop.

echo "[$(date)] on_publish_done fired" >> /home/vspot/loop.log

# Kill relay (it likely already died when OBS input closed, but clean up)
if [ -f /home/vspot/relay.pid ]; then
    kill "$(cat /home/vspot/relay.pid)" 2>/dev/null
    rm -f /home/vspot/relay.pid
fi

sleep 2

/home/vspot/start_loop.sh
