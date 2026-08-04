#!/usr/bin/env bash
# Fill the four map-storage credentials in the VPS .env.
#
# Run on the VPS from ~/workadventure after a git pull:
#   bash scripts/vps/setup-map-storage-secrets.sh
#
# Idempotent: a variable that already has a non-empty value is left alone, so
# re-running never rotates a credential out from under a running container.
# Values are never printed -- only whether each one was set or kept.

set -euo pipefail

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Run this from ~/workadventure." >&2
    exit 1
fi

cp "$ENV_FILE" "$ENV_FILE.bak-$(date +%F-%H%M%S)"

set_var() {
    local key="$1" val="$2"
    local current
    current=$(grep -E "^${key}=" "$ENV_FILE" | head -1 | cut -d= -f2- || true)

    if [ -n "$current" ]; then
        echo "  kept  $key (already set)"
        return
    fi

    if grep -qE "^${key}=" "$ENV_FILE"; then
        # Present but empty. Use a non-/ delimiter: hex values are safe, but the
        # username could contain anything.
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
    fi
    echo "  set   $key"
}

echo "Updating $ENV_FILE (backup written alongside):"
set_var MAP_STORAGE_AUTH_USER     "432bleu"
set_var MAP_STORAGE_AUTH_PASSWORD "$(openssl rand -hex 32)"
set_var MAP_STORAGE_AUTH_TOKEN    "$(openssl rand -hex 32)"
set_var MAP_STORAGE_API_TOKEN     "$(openssl rand -hex 32)"

echo
echo "Done. To read the upload password back when you need it (prints ONLY that value):"
echo "  grep '^MAP_STORAGE_AUTH_PASSWORD=' $ENV_FILE | cut -d= -f2-"
echo
echo "Next: recreate the stack with BOTH compose files, e.g."
echo "  docker compose -f docker-compose.yaml -f docker-compose.livekit.yaml up -d --force-recreate play back map-storage"
