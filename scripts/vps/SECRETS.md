# Secrets and key rotation

Written 2026-08-04. Which credentials this stack holds, where they live, and what breaks when you
change them.

**General procedure.** Back up `.env`, change the value, recreate the services that read it:

```
cd ~/workadventure && cp .env .env.bak-$(date +%F-%H%M%S) && sed -i "s|^VAR_NAME=.*|VAR_NAME=$(openssl rand -hex 32)|" .env
```

```
docker compose -f docker-compose.yaml -f docker-compose.livekit.yaml up -d --force-recreate <services>
```

Always both `-f` files — bringing the stack up without the livekit override has caused a multi-day
outage before.

> [!NOTE]
> `scripts/vps/setup-map-storage-secrets.sh` does **not** rotate. It is deliberately idempotent and
> keeps any non-empty value, so re-running is a no-op. Rotation is the `sed` above.

---

## Tier 1 — rotate freely

`MAP_STORAGE_AUTH_PASSWORD`, `MAP_STORAGE_AUTH_TOKEN`, `MAP_STORAGE_API_TOKEN`,
`PROMETHEUS_AUTHORIZATION_TOKEN`

Nothing persists across a change. Recreate `play back map-storage`. Only consequence: the next map
upload uses the new password.

---

## Tier 2 — rotate in lockstep; logs everyone out

### `SECRET_KEY`

Consumed in four places: `play` (docker-compose.yaml:78), `back` (:228), `map-storage` (:293), and
handed to Synapse as `JWT_SECRET` (:527). `play/src/pusher/services/JWTTokenManager.ts:26` uses it
to sign the WorkAdventure auth JWT.

- Rotating **invalidates every session** — everyone in the venue is disconnected and must re-enter.
- Recreating the four services one at a time leaves them disagreeing about signatures in the gap.
  Change the value once, then recreate all four in a single command.
- Never during a show.

Ships as the literal `yourSecretKey2020` in `.env.template:200` — confirm prod is not still that.

### `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`

These live in **two** places and must match:

1. `.env`, passed through `docker-compose.livekit.yaml:22-23`
2. the `keys:` block in `livekit-config.yaml:23`

Change one without the other and LiveKit rejects every token — proximity video and the megaphone
die, with no obvious error in the UI. This is the easiest one to get wrong, because a YAML config
file is not where people look for a credential.

Template ships dev defaults (`LIVEKIT_API_KEY=devkey`, `LIVEKIT_API_SECRET=1234...`), so these are
worth auditing.

---

## Tier 3 — baked into data; rotation is not a swap

### Matrix secrets — `synapse/homeserver.template.yaml:30-32`

`registration_shared_secret`, `macaroon_secret_key`, `form_secret`.

| Secret | Effect of rotating |
|---|---|
| `registration_shared_secret` | Safe. **Urgent** — it currently lets anyone create accounts. |
| `macaroon_secret_key` | Invalidates every Matrix access token. Free now (no accounts), painful later. |
| `form_secret` | Safe anytime. |

> [!WARNING]
> **These live in a git-tracked file, not `.env`.** Editing them on the VPS leaves the working tree
> dirty, so the next `git pull` conflicts — and if the change is ever committed and pushed, the new
> secrets become public exactly like the old ones did. See "Moving Matrix secrets to .env" below.

### Not secrets, but same class — unrotatable after real use

- `SYNAPSE_SERVER_NAME` — baked into every Matrix user ID (`@user:server_name`).
- The Synapse signing key (`signing_key_path`) — your federation identity.

Both are free to set correctly before the first registration and effectively permanent after.

---

## Tier 4 — rotate at the provider first

`STRIPE_SECRET_KEY`, `SENDGRID_API_KEY`, `NOWPAYMENTS_API_KEY`, `NOWPAYMENTS_IPN_SECRET`,
`EMBEDLY_KEY`, `IFRAMELY_KEY`

Order matters:

1. Issue the new key in the provider's dashboard
2. Put it in `.env`, recreate `boxoffice`
3. **Then** revoke the old key

Revoking first causes live payment or email failures in the window between.

---

## Moving Matrix secrets to .env

The proper fix for the Tier 3 warning. `synapse/start.sh:21` already renders the template through
`envsubst`, and `:9-19` hard-fails if any `${VAR}` in the template is undefined — so this is a
supported path, not a hack.

Replace the three literals in `homeserver.template.yaml`:

```yaml
registration_shared_secret: "${MATRIX_REGISTRATION_SHARED_SECRET}"
macaroon_secret_key: "${MATRIX_MACAROON_SECRET_KEY}"
form_secret: "${MATRIX_FORM_SECRET}"
```

Add all three to `.env` (and to `.env.template` as empty keys), then recreate `synapse`. After this
the repo holds no Matrix secrets and rotation is a `.env` change like everything else.

**Because start.sh exits 1 on an undefined variable, the `.env` entries must exist before the next
`synapse` recreate — otherwise the container fails to start.**

---

## Known-leaked credentials

Anything that has ever been committed to this repo is public, because
`github.com/batestzu/432bleu` is public. Rotating the value fixes the future; it does not un-publish
the old one. Git history rewriting is the only way to remove it, and is rarely worth it — rotation
plus not repeating the mistake is the practical answer.

As of 2026-08-04 this covers the three Matrix secrets above, which shipped as upstream dev defaults.
