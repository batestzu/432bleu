#!/usr/bin/env bash
# Build the map-storage upload bundle for concert.tmj.
#
# map-storage's /upload is a FULL DIRECTORY REPLACE (DiskFileSystem.ts:26) -- whatever
# is missing from this zip is deleted server-side. So the bundle must always carry the
# map AND every asset it references.
#
# It must NOT contain a .wam file: an existing concert.wam survives a re-upload only
# when the zip has the .tmj and no .wam (DiskFileSystem.ts:36-38). That is what
# preserves megaphone areas placed in the in-browser map editor.
#
# It must also NOT contain the other maps under maps/ -- ~130 upstream test maps plus
# starter/, lab/ and Tuto/ are Tiled maps in .json form, and map-storage rejects any
# .json that looks like a map (UploadController.ts:139-152), failing the whole upload.

#
# Usage:
#   bash scripts/vps/build-map-bundle.sh [output.zip]            # build only
#   bash scripts/vps/build-map-bundle.sh [output.zip] --upload   # build then upload
#
# --upload reads MAP_STORAGE_AUTH_USER/PASSWORD from .env and feeds them to curl via a
# config file on stdin, so the password never appears in argv (visible in `ps`) or in
# shell history.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAPS_DIR="$REPO_ROOT/maps"
OUT="${1:-$REPO_ROOT/concert-bundle.zip}"
DO_UPLOAD=0
[ "${2:-}" = "--upload" ] && DO_UPLOAD=1

for cmd in zip unzip python3 curl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: '$cmd' not installed. Run: sudo apt-get update && sudo apt-get install -y zip unzip" >&2
        exit 1
    fi
done

cd "$MAPS_DIR"

if [ ! -f concert.json ]; then
    echo "ERROR: maps/concert.json not found" >&2
    exit 1
fi

# The .tmj rename happens HERE, inside the bundle only -- the repo keeps concert.json.
#
# This is deliberate. The `maps` container serves maps.432bleu.com/concert.json, which is
# what the currently live START_ROOM_URL points at, and WorkAdventure sends returning
# visitors back to their last room regardless of START_ROOM_URL. Renaming the file in git
# would 404 the live room on the next routine `git pull` on the VPS, before the /~/ cutover
# is ready. Rename the repo file only at cutover, together with START_ROOM_URL and the
# setup-prod.py literal that regenerates it.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp concert.json "$STAGE/concert.tmj"
ln -s "$MAPS_DIR/assets" "$STAGE/assets"
cd "$STAGE"

# Verify every tileset image referenced by the map exists before packing, so a broken
# bundle is caught here rather than as blank tiles in a live room.
python3 - <<'PY'
import json, os, sys
m = json.load(open("concert.tmj"))
missing = []
for ts in m.get("tilesets", []):
    img = ts.get("image")
    if not img:
        print(f"  external tileset (not embedded): {ts.get('source')}", file=sys.stderr)
        missing.append(ts.get("source"))
        continue
    if not os.path.exists(img):
        missing.append(img)
if missing:
    print("ERROR: unresolved tileset references:", file=sys.stderr)
    for p in missing:
        print(f"  {p}", file=sys.stderr)
    sys.exit(1)
print(f"all {len(m.get('tilesets', []))} tilesets resolve")
PY

rm -f "$OUT"
# zip follows symlinks by default (no -y), so assets/ is stored as real files.

# Paths are stored relative to maps/ so the map's "assets/..." references resolve.
zip -q -r "$OUT" concert.tmj assets \
    -x '*/.*' '.*' '*/node_modules/*'

echo "built: $OUT"
unzip -l "$OUT" | tail -1

# Guard rails: prove the two failure modes are absent.
# Use -Z1 (names only) -- parsing `unzip -l` columns silently misses matches.
if unzip -Z1 "$OUT" | grep -q '\.wam$'; then
    echo "ERROR: bundle contains a .wam -- this would overwrite placed map-editor areas" >&2
    exit 1
fi

# Any .json that parses as a Tiled map fails the whole upload. Non-map .json
# (e.g. assets/venue_props_anims.json, a tile-animation sidecar) is fine.
BAD_JSON=$(unzip -Z1 "$OUT" | grep -E '\.json$' || true)
if [ -n "$BAD_JSON" ]; then
    while IFS= read -r f; do
        if python3 -c "
import json,sys,zipfile
z=zipfile.ZipFile('$OUT')
try: d=json.loads(z.read('$f'))
except Exception: sys.exit(1)
sys.exit(0 if isinstance(d,dict) and 'layers' in d and 'tilesets' in d else 1)
"; then
            echo "ERROR: $f is a Tiled map in .json form -- rename it .tmj or exclude it" >&2
            exit 1
        fi
    done <<< "$BAD_JSON"
    echo "non-map .json files present (harmless):"
    echo "$BAD_JSON" | sed 's/^/  /'
fi

if [ "$DO_UPLOAD" = "0" ]; then
    cat <<EOF

Built only. To upload, re-run with --upload, or by hand (let curl PROMPT for the
password -- inlining it puts it in shell history and in \`ps\`):

  curl -u \$MAP_STORAGE_AUTH_USER -F "file=@$OUT" -F "directory=" https://mapstorage.432bleu.com/upload
EOF
    exit 0
fi

# ---- upload ----------------------------------------------------------------
ENV_FILE="$REPO_ROOT/.env"
[ -f "$ENV_FILE" ] || { echo "ERROR: $ENV_FILE not found; cannot read credentials" >&2; exit 1; }

MS_USER=$(grep -E '^MAP_STORAGE_AUTH_USER=' "$ENV_FILE" | head -1 | cut -d= -f2-)
MS_PASS=$(grep -E '^MAP_STORAGE_AUTH_PASSWORD=' "$ENV_FILE" | head -1 | cut -d= -f2-)

if [ -z "$MS_USER" ] || [ -z "$MS_PASS" ]; then
    echo "ERROR: MAP_STORAGE_AUTH_USER/PASSWORD empty in .env." >&2
    echo "       Run: bash scripts/vps/setup-secrets.sh" >&2
    exit 1
fi

echo
echo "Uploading to https://mapstorage.432bleu.com/upload ..."

# -K - reads config from stdin, keeping credentials out of argv.
HTTP_CODE=$(printf 'user = "%s:%s"\n' "$MS_USER" "$MS_PASS" | curl -sS -K - \
    -o /tmp/map-upload-response.txt -w '%{http_code}' \
    -F "file=@$OUT" -F "directory=" \
    https://mapstorage.432bleu.com/upload)

echo "HTTP $HTTP_CODE"
echo "--- response ---"
head -c 2000 /tmp/map-upload-response.txt; echo

if [ "$HTTP_CODE" != "200" ]; then
    echo >&2
    echo "Upload FAILED. Nothing was changed server-side on a validation error." >&2
    exit 1
fi

echo
echo "Uploaded. Verify the generated WAM and the map list:"
echo "  curl -s https://mapstorage.432bleu.com/maps"
