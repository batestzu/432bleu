#!/usr/bin/env python3
"""
Production setup for WorkAdventure → 432bleu.com
Run from /home/vspot/workadventure/ on the VPS
"""
import re, shutil, os

DOMAIN = "432bleu.com"
EMAIL  = "theskylerbates@gmail.com"

# ── docker-compose.yaml ───────────────────────────────────────────────────────
dc_path = "docker-compose.yaml"
shutil.copy(dc_path, dc_path + ".bak")
dc = open(dc_path).read()

# 1. Replace domain everywhere
dc = dc.replace("workadventure.localhost", DOMAIN)

# 2. Upgrade http:// external service URLs to https://
dc = re.sub(r'http://([a-zA-Z][a-zA-Z0-9-]*)\.432bleu\.com',
            r'https://\1.432bleu.com', dc)

# 3. Traefik: replace command block with HTTPS + Let's Encrypt
old_cmd = (
    "    command:\n"
    "      - --api.insecure=true\n"
    "      - --providers.docker\n"
    "      - --entryPoints.web.address=:80\n"
    "      - --providers.docker.exposedbydefault=false\n"
    "      #- --log.level=DEBUG\n"
)
new_cmd = (
    "    command:\n"
    "      - --providers.docker\n"
    "      - --providers.docker.exposedbydefault=false\n"
    "      - --entryPoints.web.address=:80\n"
    "      - --entryPoints.websecure.address=:443\n"
    "      - --entrypoints.web.http.redirections.entrypoint.to=websecure\n"
    "      - --entrypoints.web.http.redirections.entrypoint.scheme=https\n"
    "      - --certificatesresolvers.myresolver.acme.tlschallenge=true\n"
    f"      - --certificatesresolvers.myresolver.acme.email={EMAIL}\n"
    "      - --certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json\n"
)
if old_cmd in dc:
    dc = dc.replace(old_cmd, new_cmd)
    print("✓ Traefik command updated")
else:
    print("⚠ Traefik command block not matched — check manually")

# 4. Traefik: add port 443
dc = dc.replace(
    '    ports:\n      - "80:80"\n    command:',
    '    ports:\n      - "80:80"\n      - "443:443"\n    command:'
)

# 5. Traefik: remove expose section (insecure API disabled)
dc = dc.replace('    expose:\n      - "8080"\n    ports:', '    ports:')

# 6. Traefik: add letsencrypt volume
dc = dc.replace(
    "      - /var/run/docker.sock:/var/run/docker.sock\n    networks:",
    "      - /var/run/docker.sock:/var/run/docker.sock\n      - ./letsencrypt:/letsencrypt\n    networks:"
)

# 7. Change entryPoints=web → websecure in all service labels
dc = re.sub(
    r'(traefik\.http\.routers\.[a-z0-9-]+\.entryPoints=)web\b',
    r'\1websecure', dc
)

# 8. Add tls.certresolver to every router that doesn't already have it
routers = set(re.findall(r'traefik\.http\.routers\.([a-z0-9-]+)\.rule=', dc))
print(f"  Routers found: {sorted(routers)}")
for name in sorted(routers):
    tls_label = f'traefik.http.routers.{name}.tls.certresolver=myresolver'
    if tls_label not in dc:
        pattern = rf'(      - "traefik\.http\.routers\.{re.escape(name)}\.rule=[^"]*")'
        replacement = (
            rf'\1\n'
            rf'      - "traefik.http.routers.{name}.tls.certresolver=myresolver"'
        )
        dc, n = re.subn(pattern, replacement, dc)
        if n:
            print(f"  ✓ TLS added to router: {name}")
        else:
            print(f"  ⚠ Could not add TLS to router: {name}")

# 9. Owncast: remove port 8085 (route via Traefik instead), add labels
dc = dc.replace(
    '      - "8085:8080"   # web UI + HLS stream viewer\n      - "1935:1935"   # RTMP ingest (OBS points here)',
    '      - "1935:1935"   # RTMP ingest (OBS points here)'
)
owncast_labels = (
    '    labels:\n'
    '      - "traefik.enable=true"\n'
    f'      - "traefik.http.routers.owncast.rule=Host(`owncast.{DOMAIN}`)"\n'
    '      - "traefik.http.routers.owncast.entryPoints=websecure"\n'
    '      - "traefik.http.routers.owncast.tls.certresolver=myresolver"\n'
    '      - "traefik.http.services.owncast.loadbalancer.server.port=8080"\n'
)
dc = dc.replace(
    '    restart: unless-stopped\n\n#  coturn:',
    f'    restart: unless-stopped\n{owncast_labels}\n#  coturn:'
)

open(dc_path, 'w').write(dc)
print("✓ docker-compose.yaml saved")

# ── .env ──────────────────────────────────────────────────────────────────────
env_path = ".env"
shutil.copy(env_path, env_path + ".bak")
env = open(env_path).read()
env = env.replace("workadventure.localhost", DOMAIN)
env = re.sub(r'http://([a-zA-Z][a-zA-Z0-9-]*)\.432bleu\.com',
             r'https://\1.432bleu.com', env)
env = re.sub(r'ACME_EMAIL=.*',      f'ACME_EMAIL={EMAIL}', env)
env = re.sub(r'START_ROOM_URL=.*',
             f'START_ROOM_URL=/_/global/maps.{DOMAIN}/concert.json', env)
open(env_path, 'w').write(env)
print("✓ .env saved")

# ── maps/concert.json ─────────────────────────────────────────────────────────
cj_path = "maps/concert.json"
if os.path.exists(cj_path):
    cj = open(cj_path).read()
    cj = cj.replace("http://localhost:8085", f"https://owncast.{DOMAIN}")
    cj = cj.replace("workadventure.localhost", DOMAIN)
    cj = re.sub(r'http://([a-zA-Z][a-zA-Z0-9-]*)\.432bleu\.com',
                r'https://\1.432bleu.com', cj)
    open(cj_path, 'w').write(cj)
    print("✓ maps/concert.json saved")

# ── maps HTML files ───────────────────────────────────────────────────────────
html_files = [
    "backstage-pass.html", "return-to-concert.html",
    "loading-screen.html", "error-404.html",
    "error-desync.html",   "error-doors-closed.html",
]
for fname in html_files:
    p = f"maps/{fname}"
    if os.path.exists(p):
        content = open(p).read()
        content = content.replace("workadventure.localhost", DOMAIN)
        content = re.sub(r'http://([a-zA-Z][a-zA-Z0-9-]*)\.432bleu\.com',
                         r'https://\1.432bleu.com', content)
        open(p, 'w').write(content)
        print(f"✓ {p} saved")

# ── letsencrypt dir ───────────────────────────────────────────────────────────
os.makedirs("letsencrypt", exist_ok=True)
print("✓ letsencrypt/ directory ready")

print("\nAll done! Run: docker compose up -d")
