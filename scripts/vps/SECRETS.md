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
> `scripts/vps/setup-secrets.sh` does **not** rotate. It is deliberately idempotent and
> keeps any non-empty value, so re-running is a no-op. Rotation is the `sed` above.

---

## Tier 1 — rotate freely

`MAP_STORAGE_AUTH_PASSWORD`, `MAP_STORAGE_AUTH_TOKEN`, `MAP_STORAGE_API_TOKEN`,
`PROMETHEUS_AUTHORIZATION_TOKEN`

Nothing persists across a change. Recreate `play back map-storage`. Only consequence: the next map
upload uses the new password.

### `OIDC_CLIENT_SECRET` / `OIDC_PRIVATE_KEY_B64` (boxoffice OIDC provider)

Also Tier 1, with one wrinkle each. The client secret is shared between boxoffice and the
WA pusher (`OPENID_CLIENT_SECRET` in `.env`) — **rotate BOTH in the same edit** and recreate
`boxoffice` + `play`, or every staff login fails with a 401 from `/token`. The RSA key signs
id/access tokens that live at most 1 hour: rotating it invalidates outstanding tokens (staff
mid-session in WA keep playing — WA only checks at login — but a re-login inside that hour
would need one retry). `OIDC_STAFF_TAGS` is not a secret; edit it freely, applies on next login.

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

### Matrix secrets — now in `.env` (migrated 2026-08-04)

`MATRIX_REGISTRATION_SHARED_SECRET`, `MATRIX_MACAROON_SECRET_KEY`, `MATRIX_FORM_SECRET`.

| Secret | Effect of rotating |
|---|---|
| `MATRIX_REGISTRATION_SHARED_SECRET` | Safe. **Urgent** — it lets anyone create accounts. |
| `MATRIX_MACAROON_SECRET_KEY` | Invalidates every Matrix access token. Free now (no accounts), painful later. |
| `MATRIX_FORM_SECRET` | Safe anytime. |

These used to be hardcoded literals in `synapse/homeserver.template.yaml`, a **committed, public**
file. They are now `${VAR}` references resolved from `.env` by `envsubst` at container start.

> [!IMPORTANT]
> **Rotating these only takes effect when `synapse` is recreated.** `start.sh:21` renders
> `homeserver.yaml` from the template at every start, and `synapse/homeserver.yaml` is gitignored
> (`.gitignore:29`) — so editing the *rendered* file appears to work, leaves `git status` clean, and
> is silently overwritten on the next restart. Always change `.env`, never `homeserver.yaml`.

> [!WARNING]
> **Hex values only.** `envsubst` expands unbraced `$sequences` inside values too. The old upstream
> defaults contained fragments like `$u8` and `$~Je`, so the secret Synapse actually ran with was
> not the secret written in the file. `openssl rand -hex 32` avoids this entirely.

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

## Populating secrets

```
cd ~/workadventure && git pull && bash scripts/vps/setup-secrets.sh
```

Idempotent — fills only what is empty, keeps what is already set, writes a timestamped `.env`
backup, and prints whether each key was set or kept, never the value.

> [!CAUTION]
> **The Matrix entries must exist before `synapse` is next recreated.** `synapse/start.sh:9-19`
> greps the template for `${VAR}` references and **exits 1** if any is undefined, so a missing entry
> means the container will not start. `setup-secrets.sh` re-checks all three at the end and fails
> loudly rather than letting that happen.

Note this is *only* about the config rendering correctly. Synapse should still not be exposed until
the items in `MAP-STORAGE-AND-MATRIX.md` §6a are addressed — open registration, the OIDC-mock
startup dependency, and the wide-open room publication rules.

---

## Known-leaked credentials

Anything that has ever been committed to this repo is public, because
`github.com/batestzu/432bleu` is public. Rotating the value fixes the future; it does not un-publish
the old one. Git history rewriting is the only way to remove it, and is rarely worth it — rotation
plus not repeating the mistake is the practical answer.

As of 2026-08-04 this covers the three Matrix secrets above, which shipped as upstream dev defaults.
