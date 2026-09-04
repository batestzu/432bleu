#!/bin/bash
# Shared helpers for the 432 Bleu stream scripts. Sourced, never run directly.
#
# WHY THIS EXISTS
# ---------------
# Every script used to identify its ffmpeg processes by a pid read from a
# pidfile. On 2026-09-03 that cost the venue an entire show. The mechanism:
# a loop restart failed (Owncast still held the publisher slot), but the script
# had already written the dead ffmpeg's pid into loop.pid. The loop that was
# actually running became invisible to every later kill. It held Owncast's one
# publisher slot for two days, so every relay attempt was refused with
# "stream already running; can not overtake an existing stream" and the
# audience watched the house loop through the whole event.
#
# Two rules come out of that, and this file exists to enforce them:
#
#   1. Identify processes by their COMMAND PATTERN, not by a pid we wrote down.
#      A pattern cannot go stale. Pidfiles are still written because they are
#      useful to a human reading the logs, but no control flow depends on them.
#
#   2. Prove success against the SERVICE, not against the process. ffmpeg stays
#      alive for several seconds while Owncast is refusing it, so the old
#      `kill -0` check three seconds after launch reported a confident success
#      while the relay was being rejected. Ask Owncast whether it has a
#      publisher; ask Icecast whether it has a source.

PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH

# EVERY backgrounded ffmpeg must be launched with `9>&-`. The scripts hold their
# mutual-exclusion lock on file descriptor 9, and a child inherits open
# descriptors: an ffmpeg started without that redirection keeps holding the lock
# for its whole life, long after the script that took it has exited. The first
# build of this rewrite did exactly that, and on_publish_done sat waiting on a
# lock owned by the relay it was trying to kill while Owncast stayed dark.
VSPOT_HOME=${VSPOT_HOME:-/home/vspot}
OWNCAST_API=${OWNCAST_API:-http://localhost:8085}
ICECAST_PORT=${ICECAST_PORT:-8005}

# --- process patterns --------------------------------------------------------
# Matched by pgrep/pkill -f against the whole command line, as extended regex.
# Both loop legs read loop.mp4 with -stream_loop; both relay legs read from
# nginx-rtmp on 1935. Within each pair, video carries -c copy / -map 0:v and
# audio carries -vn, so no pattern can match the wrong leg.
#
# The wildcard after "ffmpeg" is load-bearing twice over: it absorbs the
# -nostdin/-loglevel flags, and it keeps these patterns matching legs started
# by the OLDER version of these scripts, which is what a deploy has to clean up.
# Owncast's own transcoder (-i pipe:0 -map v:0) matches none of them.
PAT_LOOP_VIDEO='ffmpeg .*-stream_loop .*loop\.mp4 -c copy'
PAT_LOOP_AUDIO='ffmpeg .*-stream_loop .*loop\.mp4 -vn'
PAT_RELAY_VIDEO='ffmpeg .*-i rtmp://localhost:1935/live/.*-map 0:v'
PAT_RELAY_AUDIO='ffmpeg .*-i rtmp://localhost:1935/live/.*-vn'

# --- logging -----------------------------------------------------------------
# slog <logfile> <message...>   Event log, UTC, one line. ffmpeg's own chatter
# goes to a separate *_ffmpeg.log so these files stay greppable.
slog() {
    local f=$1; shift
    echo "[$(date -u '+%Y-%m-%d %H:%M:%SZ')] $*" >> "$f"
}

# --- process control ---------------------------------------------------------
# pids_matching <pattern>
# Candidates from pgrep, then narrowed to processes whose name really is
# ffmpeg. That second filter is not optional: `pkill -f` matches ANY process
# whose command line merely mentions the pattern, which includes an operator's
# own diagnostic command and the shell running it. Killing the venue's
# engineer mid-show is a worse outcome than the bug this replaces.
# Returns 1 when nothing matches, so callers can use it as a condition. A bare
# `for` loop over no items would return 0, which reads as "found".
PROC_NAME=${PROC_NAME:-ffmpeg}
pids_matching() {
    local pid found=1
    for pid in $(pgrep -f "$1" 2>/dev/null); do
        if [ "$(cat /proc/"$pid"/comm 2>/dev/null)" = "$PROC_NAME" ]; then
            printf '%s\n' "$pid"
            found=0
        fi
    done
    return $found
}

# kill_pattern <pattern> <label> <logfile>
# SIGTERM, wait up to 12s, SIGKILL, wait up to 4s. Returns 0 only when nothing
# matching the pattern is left. Owncast frees its publisher slot when the
# connection is really gone, not when kill() returns, so callers must wait.
kill_pattern() {
    local pat=$1 label=$2 logf=$3 i pids
    pids=$(pids_matching "$pat")
    [ -z "$pids" ] && return 0
    slog "$logf" "killing $label (pids: $(echo $pids | tr '\n' ' '))"
    kill $pids 2>/dev/null
    for i in $(seq 1 24); do
        pids=$(pids_matching "$pat")
        [ -z "$pids" ] && { slog "$logf" "$label released"; return 0; }
        sleep 0.5
    done
    slog "$logf" "$label ignored SIGTERM for 12s, sending SIGKILL"
    kill -9 $pids 2>/dev/null
    for i in $(seq 1 8); do
        pids=$(pids_matching "$pat")
        [ -z "$pids" ] && { slog "$logf" "$label released (after SIGKILL)"; return 0; }
        sleep 0.5
    done
    slog "$logf" "ERROR: $label still running after SIGKILL (pids: $(echo $pids | tr '\n' ' '))"
    return 1
}

# record_pid <pattern> <pidfile>
# Writes the pid that is actually running, resolved from the pattern, rather
# than $! (which can name a setsid wrapper or an ffmpeg that already exited).
record_pid() {
    local pid
    pid=$(pids_matching "$1" | head -1)
    if [ -n "$pid" ]; then echo "$pid" > "$2"; else rm -f "$2"; fi
}

# --- service state -----------------------------------------------------------
# owncast_status  ->  "<true|false|unknown> <lastConnectTime|->"
owncast_status() {
    curl -s --max-time 4 "$OWNCAST_API/api/status" 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("unknown -"); sys.exit(0)
print("true" if d.get("online") else "false", d.get("lastConnectTime") or "-")
' 2>/dev/null || echo "unknown -"
}

# wait_owncast_publisher <since_utc_iso> <timeout_s>
# Succeeds once Owncast reports a publisher that connected at or after the
# mark. This is the only trustworthy proof that a relay took the slot.
# Bounded by wall clock, not by iteration count: a hung Owncast makes each
# curl take its full timeout, and this runs inside an nginx publish hook.
wait_owncast_publisher() {
    local since=$1 timeout=${2:-20} deadline online lct
    deadline=$(( $(date +%s) + timeout ))
    while :; do
        read -r online lct <<< "$(owncast_status)"
        if [ "$online" = "true" ] && [ "$lct" != "-" ] && [[ "$lct" > "$since" ]]; then
            return 0
        fi
        [ "$(date +%s)" -ge "$deadline" ] && return 1
        sleep 1
    done
}

# icecast_has_source — 0 when something is mounted on /live.mp3.
# Never probe an Icecast mount with curl -I: it answers 400 to every HEAD,
# healthy or not. Read the status JSON instead.
icecast_has_source() {
    curl -s --max-time 4 "http://127.0.0.1:$ICECAST_PORT/status-json.xsl" 2>/dev/null | python3 -c '
import json, sys
try:
    s = json.load(sys.stdin)["icestats"].get("source")
except Exception:
    sys.exit(1)
if not s:
    sys.exit(1)
s = s if isinstance(s, list) else [s]
sys.exit(0 if any("/live.mp3" in (x.get("listenurl") or "") for x in s) else 1)
' 2>/dev/null
}

wait_icecast_source() {
    local timeout=${1:-15} deadline
    deadline=$(( $(date +%s) + timeout ))
    while :; do
        icecast_has_source && return 0
        [ "$(date +%s)" -ge "$deadline" ] && return 1
        sleep 1
    done
}

# --- waiting on a leg we just launched ---------------------------------------
# Both return: 0 the service accepted it, 2 the process exited (retry now),
# 1 timed out with the process still alive (kill it, then retry).
#
# The exit-2 case is the common one and is not really a failure: nginx-rtmp
# cannot serve a player until the publisher has sent enough of a stream, so a
# relay launched immediately after the publish hook fires dies at once with
# "Error opening input". Detecting that costs a second, where waiting out the
# service timeout costs the venue twenty.

# wait_relay_live <pattern> <since_utc_iso> <timeout_s>
wait_relay_live() {
    local pat=$1 since=$2 timeout=${3:-25} deadline online lct
    deadline=$(( $(date +%s) + timeout ))
    while :; do
        read -r online lct <<< "$(owncast_status)"
        if [ "$online" = "true" ] && [ "$lct" != "-" ] && [[ "$lct" > "$since" ]]; then return 0; fi
        pids_matching "$pat" >/dev/null || return 2
        [ "$(date +%s)" -ge "$deadline" ] && return 1
        sleep 1
    done
}

# wait_mount_live <pattern> <timeout_s>
wait_mount_live() {
    local pat=$1 timeout=${2:-15} deadline
    deadline=$(( $(date +%s) + timeout ))
    while :; do
        icecast_has_source && return 0
        pids_matching "$pat" >/dev/null || return 2
        [ "$(date +%s)" -ge "$deadline" ] && return 1
        sleep 1
    done
}

# utc_mark [seconds_ago] — timestamp for comparing against lastConnectTime.
# Defaults to two seconds ago so a connection landing in the same second as
# the mark still counts.
utc_mark() { date -u -d "${1:-2} seconds ago" '+%Y-%m-%dT%H:%M:%SZ'; }
