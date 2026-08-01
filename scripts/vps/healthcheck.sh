#!/usr/bin/env bash
# Venue health check. Runs on the VPS from cron; prints a report and exits non-zero
# if anything is wrong.
#
# Dead-man's-switch mode: set HEALTHCHECK_PING_URL (e.g. a healthchecks.io ping URL)
# and this script pings it ONLY when every check passes. The external service alerts
# on the ABSENCE of a ping, so it catches both failure modes with one free dependency:
#   - services down but box alive  -> checks fail  -> no ping -> alert
#   - whole box down / rebooted    -> cron never runs -> no ping -> alert
#
# Install:
#   sudo cp scripts/vps/healthcheck.sh /home/vspot/healthcheck.sh && sudo chmod +x /home/vspot/healthcheck.sh
#   echo 'HEALTHCHECK_PING_URL=https://hc-ping.com/<uuid>' | sudo tee /home/vspot/healthcheck.conf
#   crontab -e   ->   */5 * * * * /home/vspot/healthcheck.sh >> /home/vspot/healthcheck.log 2>&1

set -u
[ -r /home/vspot/healthcheck.conf ] && . /home/vspot/healthcheck.conf
FAILED=""

check_http() {
    local label=$1 url=$2 want=$3
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$url" 2>/dev/null)
    case " $want " in
        *" $code "*) echo "  OK   $label ($code)" ;;
        *) echo "  FAIL $label (got $code, want one of: $want)"; FAILED="$FAILED $label" ;;
    esac
}

echo "[$(date '+%Y-%m-%d %H:%M:%S')] healthcheck"

# 302 = gate redirect with no pass cookie; that is the healthy unauthenticated answer.
check_http "play"      "https://play.432bleu.com/"             "200 302"
check_http "boxoffice" "https://boxoffice.432bleu.com/api/events" "200"
check_http "owncast"   "https://owncast.432bleu.com/api/status"   "200"

# Owncast being UP is not the same as Owncast having a SOURCE. The house loop is a bare
# process that no reboot restores, so the stream can sit sourceless indefinitely --
# exactly what happened for ~40 min on 2026-08-01 and went unnoticed.
ONLINE=$(curl -s --max-time 15 https://owncast.432bleu.com/api/status 2>/dev/null \
         | grep -oE '"online":[a-z]+' | cut -d: -f2)
if [ "$ONLINE" = "true" ]; then
    echo "  OK   owncast-source (stream online)"
else
    echo "  FAIL owncast-source (online=${ONLINE:-unknown} -- house loop dead or no performer?)"
    FAILED="$FAILED owncast-source"
fi

# Any container that exited is a problem: prod services should all carry a restart policy.
# Note: "could not check" must FAIL, never silently pass -- a monitor that reports healthy
# when it was unable to look is worse than no monitor at all.
COMPOSE_DIR=/home/vspot/workadventure
if ! command -v docker >/dev/null 2>&1; then
    echo "  FAIL containers (docker not found)"
    FAILED="$FAILED docker-missing"
elif [ ! -d "$COMPOSE_DIR" ]; then
    echo "  FAIL containers (compose dir $COMPOSE_DIR not found)"
    FAILED="$FAILED compose-dir"
elif ! PS=$(cd "$COMPOSE_DIR" && docker compose -f docker-compose.yaml -f docker-compose.livekit.yaml \
              ps --status exited --status dead --format '{{.Service}}' 2>/dev/null); then
    echo "  FAIL containers (docker compose ps failed)"
    FAILED="$FAILED compose-ps"
else
    DOWN=$(echo "$PS" | grep -vE '^(messages|redisinsight|oidc-server-mock)$' | tr '\n' ' ')
    if [ -n "${DOWN// /}" ]; then
        echo "  FAIL containers exited: $DOWN"
        FAILED="$FAILED containers"
    else
        echo "  OK   containers (no unexpected exits)"
    fi
fi

if [ -n "$FAILED" ]; then
    echo "  RESULT: UNHEALTHY --$FAILED"
    exit 1
fi

echo "  RESULT: healthy"
[ -n "${HEALTHCHECK_PING_URL:-}" ] && curl -fsS --max-time 10 "$HEALTHCHECK_PING_URL" >/dev/null 2>&1
exit 0
