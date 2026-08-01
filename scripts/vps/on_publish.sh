#!/bin/bash
# Fired by nginx-rtmp when OBS connects and starts publishing.
# Kills the loop, then relays OBS feed from nginx-rtmp → Owncast.
source /home/vspot/owncast.conf
INCOMING=$1

log() {
    echo "[$(date)] on_publish: $*" >> /home/vspot/relay.log
}

log "publish started (name=$INCOMING)"

# Kill existing loop and WAIT for it to actually exit.
# Owncast only frees the RTMP slot once the loop's connection is really gone,
# so returning as soon as kill() is sent is what caused the 2026-07-27 race:
# the relay opened while Owncast still held the slot and died instantly with
# "Error opening output ...: Input/output error".
if [ -f /home/vspot/loop.pid ]; then
    LOOP_PID="$(cat /home/vspot/loop.pid)"
    kill "$LOOP_PID" 2>/dev/null
    for _ in $(seq 1 20); do
        kill -0 "$LOOP_PID" 2>/dev/null || break
        sleep 0.5
    done
    if kill -0 "$LOOP_PID" 2>/dev/null; then
        log "loop pid $LOOP_PID ignored SIGTERM after 10s, sending SIGKILL"
        kill -9 "$LOOP_PID" 2>/dev/null
        sleep 1
    fi
    rm -f /home/vspot/loop.pid
fi

# Kill any stale relay
if [ -f /home/vspot/relay.pid ]; then
    kill "$(cat /home/vspot/relay.pid)" 2>/dev/null
    rm -f /home/vspot/relay.pid
fi

# Let Owncast notice the closed connection before the first attempt.
sleep 2

# Retry up to 5 times in case Owncast still hasn't released the slot.
# ffmpeg exits within about a second when the slot is busy, so a liveness
# check after a short sleep distinguishes a real failure from a good relay.
# -map 0:v -map 0:a ensures video is stream 0 (required by FLV/RTMP)
for i in 1 2 3 4 5; do
    ffmpeg -i "rtmp://localhost:1935/live/$INCOMING" \
        -map 0:v -map 0:a -c copy -f flv "$OWNCAST_RTMP/$STREAM_KEY" \
        >> /home/vspot/relay.log 2>&1 &
    RELAY_PID=$!
    echo "$RELAY_PID" > /home/vspot/relay.pid
    sleep 3
    if kill -0 "$RELAY_PID" 2>/dev/null; then
        log "relay running (attempt $i, pid $RELAY_PID)"
        exit 0
    fi
    log "relay attempt $i failed, retrying..."
    rm -f /home/vspot/relay.pid
    sleep 3
done

# Never leave Owncast with no input — fall back to the house loop so viewers
# see something. The performer is still publishing to nginx-rtmp at this point,
# so recovering needs an OBS stop/start (which re-fires this script).
log "RELAY FAILED after 5 attempts — falling back to house loop"
echo "[$(date)] on_publish: relay failed, restarting loop as fallback" >> /home/vspot/loop.log
/home/vspot/start_loop.sh >> /home/vspot/loop.log 2>&1
