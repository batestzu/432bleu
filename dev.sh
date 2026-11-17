#!/bin/bash
# Dev bench on Zoltan. Wraps docker compose with the dev env, the dev override
# and its own project name, so it can never be confused with the VPS stack.
#
#   ./dev.sh up            start the bench (core services only)
#   ./dev.sh logs -f play  follow the front end / pusher
#   ./dev.sh ps | down | restart play | ...   any compose command
#
# Open http://play.workadventure.localhost:8080 on Zoltan.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"
DC=(docker compose --env-file .env.dev -p bleu-dev -f docker-compose.yaml -f docker-compose.dev.yaml)
# What the venue room needs. Left out on purpose: boxoffice, postgres, umami,
# coturn, icecast, redisinsight.
CORE=(reverse-proxy redis messages back play map-storage maps icon uploader synapse oidc-server-mock)

if [ "${1:-}" = "up" ]; then
    shift
    exec "${DC[@]}" up -d "$@" "${CORE[@]}"
fi
exec "${DC[@]}" "$@"
