#!/bin/bash
# 432 Bleu house-loop supervisor.
#
# WHY THIS EXISTS
# ---------------
# start_loop.sh is invoked from nginx-rtmp's on_publish_done hook, so every
# ffmpeg leg it spawns inherits nginx.service's cgroup. nginx runs Delegate=no
# KillMode=mixed, so `systemctl restart nginx` SIGKILLs the whole house loop.
# On 2026-09-17 an unattended-upgrades run did exactly that and the venue was
# dark and silent for 60 hours. setsid does NOT help: it detaches the
# controlling terminal, not the cgroup.
#
# This runs as a systemd service, so anything it spawns lives in THIS unit's
# cgroup, where nginx cannot reach it. Its one invariant:
#
#     the house loop runs, in our cgroup, whenever no performer is live.
#
# HOW IT COOPERATES WITH THE SHOW
# -------------------------------
# on_publish.sh deliberately kills the loop so the performer's relay can take
# the single Owncast publisher slot and the single Icecast mount. A supervisor
# that simply restarted the loop whenever it vanished would fight the show for
# both. So before acting we require ALL of:
#
#   * the stream lock is free   -- no on_publish/on_publish_done mid-transition
#   * no relay leg is running   -- no performer on air
#   * Owncast is not online     -- nothing else holds the publisher slot
#
# Anything else and we do nothing this tick. Doing nothing is always safe here;
# the next tick is 15s away.

set -u

source /home/vspot/owncast.conf
source /home/vspot/stream_lib.sh

LOG=$VSPOT_HOME/loop.log
INTERVAL=${HOUSELOOP_INTERVAL:-15}
LOCK=$VSPOT_HOME/stream.lock

# Our own cgroup path. Loop legs must live here; any leg outside it was started
# by on_publish_done under nginx and is one `systemctl restart nginx` from death.
my_cgroup() { awk -F: '{print $3}' /proc/self/cgroup 2>/dev/null | head -1; }
MY_CG=$(my_cgroup)

relay_running() {
    pids_matching "$PAT_RELAY_VIDEO" >/dev/null && return 0
    pids_matching "$PAT_RELAY_AUDIO" >/dev/null && return 0
    return 1
}

# 0 when at least one loop leg is running outside our cgroup.
legs_foreign() {
    local pid cg
    for pid in $( { pids_matching "$PAT_LOOP_VIDEO"; pids_matching "$PAT_LOOP_AUDIO"; } 2>/dev/null ); do
        cg=$(awk -F: '{print $3}' /proc/"$pid"/cgroup 2>/dev/null | head -1)
        [ -n "$cg" ] && [ "$cg" != "$MY_CG" ] && return 0
    done
    return 1
}

# start_loop.sh takes the stream lock itself. We already hold it on fd 9 when we
# call it, so pass the same guard on_publish_done uses or it deadlocks on us.
# start_loop.sh closes fd 9 on every ffmpeg it backgrounds (9>&-), so the legs
# never hold the lock -- do not "fix" that.
run_start_loop() {
    STREAM_LOCK_HELD=1 "$VSPOT_HOME/start_loop.sh" --force >/dev/null 2>&1
    return $?
}

shutdown() {
    slog "$LOG" "supervisor stopping (systemd will reap the legs in our cgroup)"
    exit 0
}
trap shutdown TERM INT

slog "$LOG" "supervisor started, cgroup=$MY_CG, interval=${INTERVAL}s"

# fd 9 is the stream lock for the whole process; we take and release it per tick.
exec 9>"$LOCK"

while :; do
    # A transition is in flight (on_publish / on_publish_done / a manual
    # start_loop). Never race it -- skip and look again next tick.
    if flock -n 9; then

        if relay_running; then
            :   # performer on air; the loop must stay down

        elif ! pids_matching "$PAT_LOOP_VIDEO" >/dev/null; then
            # No loop. Only claim the slot if nothing else already holds it --
            # on_publish retries for 120s and Owncast can be mid-handshake.
            read -r online _ <<< "$(owncast_status)"
            if [ "$online" = "true" ]; then
                :   # something is publishing that is not our loop; leave it alone
            else
                slog "$LOG" "supervisor: no house loop and nothing publishing, starting it"
                run_start_loop \
                    && slog "$LOG" "supervisor: house loop started" \
                    || slog "$LOG" "supervisor: ERROR start_loop.sh failed, retrying in ${INTERVAL}s"
            fi

        elif legs_foreign; then
            # on_publish_done restarted the loop under nginx after a show.
            # Re-home it so the next nginx restart cannot kill the venue.
            slog "$LOG" "supervisor: loop legs outside unit cgroup (started under nginx), re-homing"
            run_start_loop \
                && slog "$LOG" "supervisor: house loop re-homed into $MY_CG" \
                || slog "$LOG" "supervisor: ERROR re-home failed, will retry"
        fi

        flock -u 9
    fi

    sleep "$INTERVAL"
done
