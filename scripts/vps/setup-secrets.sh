#!/usr/bin/env bash
# Fill the generated credentials in the VPS .env: map-storage and Matrix/Synapse.
#
# Run on the VPS from ~/workadventure after a git pull:
#   bash scripts/vps/setup-secrets.sh
#
# Idempotent: a variable that already has a non-empty value is left alone, so
# re-running never rotates a credential out from under a running container.
# Values are never printed -- only whether each one was set or kept.
#
# The Matrix entries MUST exist before `synapse` is next recreated: start.sh renders
# homeserver.template.yaml through envsubst and exits 1 on any undefined ${VAR}.
#
# Hex values only. envsubst expands unbraced $sequences too, so a secret containing
# something like `$u8` would be silently mangled at render time -- which is exactly
# what the upstream dev defaults did.

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
echo "-- map-storage"
set_var MAP_STORAGE_AUTH_USER     "432bleu"
set_var MAP_STORAGE_AUTH_PASSWORD "$(openssl rand -hex 32)"
set_var MAP_STORAGE_AUTH_TOKEN    "$(openssl rand -hex 32)"
set_var MAP_STORAGE_API_TOKEN     "$(openssl rand -hex 32)"

echo "-- matrix/synapse"
set_var MATRIX_REGISTRATION_SHARED_SECRET "$(openssl rand -hex 32)"
set_var MATRIX_MACAROON_SECRET_KEY        "$(openssl rand -hex 32)"
set_var MATRIX_FORM_SECRET                "$(openssl rand -hex 32)"

echo "-- oidc provider (boxoffice)"
# RSA signing key is base64-wrapped: multiline PEM does not survive .env/compose.
set_var OIDC_CLIENT_SECRET    "$(openssl rand -hex 32)"
set_var OIDC_PRIVATE_KEY_B64  "$(openssl genrsa 2048 2>/dev/null | base64 -w0)"

# Fail loudly rather than letting synapse die on its next start.
missing=""
for key in MATRIX_REGISTRATION_SHARED_SECRET MATRIX_MACAROON_SECRET_KEY MATRIX_FORM_SECRET OIDC_CLIENT_SECRET OIDC_PRIVATE_KEY_B64; do
    val=$(grep -E "^${key}=" "$ENV_FILE" | head -1 | cut -d= -f2- || true)
    [ -z "$val" ] && missing="$missing $key"
done
if [ -n "$missing" ]; then
    echo >&2
    echo "ERROR: still empty:$missing" >&2
    echo "synapse/start.sh exits 1 on an undefined \${VAR}, so it will not start." >&2
    exit 1
fi

echo
echo "Done. To read the upload password back when you need it (prints ONLY that value):"
echo "  grep '^MAP_STORAGE_AUTH_PASSWORD=' $ENV_FILE | cut -d= -f2-"
echo
echo "Next: recreate the stack with BOTH compose files, e.g."
echo "  docker compose -f docker-compose.yaml -f docker-compose.livekit.yaml up -d --force-recreate play back map-storage"
echo
echo "NOTE: synapse renders its config from the template at start, so the rotated Matrix"
echo "secrets only take effect once it is recreated. Do NOT recreate synapse until its"
echo "config is production-shaped -- see scripts/vps/MAP-STORAGE-AND-MATRIX.md section 6a."
