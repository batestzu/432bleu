# OIDC build-out: boxoffice as the identity provider

Status: **Phases 1-2 built** (2026-08-08). Phase 1 deployed-ready (compose passthrough,
`1b52ca4`); Phase 2 code complete in `boxoffice/app/routes/oidc.py` with the full flow
tested in-process (discovery → authorize → PKCE token exchange → userinfo, plus the
open-redirect, code-reuse, and bad-client rejection paths). Phase 3 (tags) shipped with
Phase 2 as `OIDC_STAFF_TAGS`. Remaining: Phase 4 cutover (populate .env on the VPS via
setup-secrets.sh, set the OPENID_* values for play, run the verification ladder).

Goal: give staff a real identity so `tags` can carry permissions, which unblocks two
things that are currently impossible for *everyone including the performer*:

- the **map editor** (`LocalAdmin.ts:99-100` grants `canEdit` on tag `admin` or `editor`)
- the **room-wide megaphone** (`WAMSettingsUtils.ts:23-32` `canUseMegaphone` checks room
  `rights` against the user's tags)

Both read the same tag array. Today `LocalAdmin.ts:241` returns `tags: tags ?? []` — an
empty array for every anonymous user — so a `rights`-gated megaphone is unusable by
anybody, and a `rights`-less one is usable by any attendee who wanders in.

`DISABLE_ANONYMOUS` stays `false`. Ticketed attendees keep entering anonymously through
the box-office gate. Only staff ever log in. Expected user count: single digits.

## Decision

**boxoffice is the OpenID Provider.** It already owns members, email, and cookies, and it
survives a WorkAdventure departure. The tradeoff accepted: we are implementing an OIDC
provider rather than configuring one, which is more work and more security surface than a
hosted IdP or self-hosted Authentik.

That cost is much lower than it first appears, because **the hard half already exists and
is in production.**

## What boxoffice already has

`boxoffice/app/routes/auth.py` + `session.py` are a working passwordless IdP core:

| Piece | Where | Notes |
|---|---|---|
| Magic-link login | `auth.py:33` `/api/auth/request-link` | rate-limited 5/min + 5/hour per email, no user-enumeration leak |
| Single-use tokens | `LoginToken` model | SHA-256 hashed at rest, 15-min TTL, `used_at` burn |
| Session cookie | `session.py:14` `set_session_cookie` | `bleu_session`, itsdangerous-signed, httponly + secure + samesite=lax, 30 days |
| Current-user dep | `session.py:26` `get_current_email` | ready to reuse verbatim |

**The cookie domain is `.432bleu.com`** (`session.py:6`), so a session established at
`432bleu.com` is *already* sent to `play.432bleu.com`. Authenticating the human — the part
that is genuinely hard to get right — is done. What's missing is the protocol shell that
lets WorkAdventure consume it.

## What WorkAdventure actually requires

Traced from `play/src/pusher/services/OpenIDClient.ts`. Several of these are not what a
generic "add OIDC" guide would tell you:

1. **Discovery is mandatory.** `OpenIDClient.ts:33` calls `Issuer.discover(OPID_CLIENT_ISSUER)`
   and, on failure, retries with `/.well-known/openid-configuration` appended (`:47`). There
   is no way to configure endpoints by hand. We must serve the discovery document.

2. **JWKS is mandatory.** `openid-client` validates the `id_token` signature against the
   `jwks_uri` from discovery. The ID token must be **RS256**, not HS256.

3. **PKCE is mandatory.** `:96-112` always sends `code_challenge` + `code_challenge_method: S256`,
   and `:145` always passes `code_verifier` to the token exchange. The token endpoint must
   accept `code_verifier` (and should verify it — cheap, and the whole point).

4. **`nonce` is NOT sent.** `:102` has it commented out. Do not require it.

5. **Tags come from `/userinfo`, not the ID token.** This is the big one.
   `:156-170` calls `client.userinfo(tokenSet)` and reads `email`, `sub`,
   `res[OPID_USERNAME_CLAIM]`, `res[OPID_LOCALE_CLAIM]`, `res[OPID_TAGS_CLAIM]` off the
   **userinfo response**. So the userinfo endpoint is where permissions actually live, and
   the ID token only needs to be well-formed and correctly signed.

6. **Claim names.** `OPID_TAGS_CLAIM` defaults to `"tags"` and `OPID_USERNAME_CLAIM` defaults
   to `"username"` (`EnvironmentVariable.ts:83-86`) — note `username`, *not* the standard
   `preferred_username`. Emit both to be safe.

7. **Non-standard query params on `/authorize`.** `authorizationUrl` appends `playUri`,
   `manuallyTriggered`, `chatRoomId`, `providerId`, `providerScopes` (`:103-110`). Our
   `/authorize` must tolerate and ignore them. It must **not** echo them back — the callback
   reads `playUri` from a cookie (`AuthenticateController.ts:295`), not the query string.

8. **`/userinfo` is called with a `playUri` query param** (`:158-160`). Ignore it.

## Blockers to clear first

**B1 — the OIDC settings are hardcoded to the dev mock.** `docker-compose.yaml:68-72`:

```yaml
OPENID_CLIENT_ID: authorization-code-client-id
OPENID_CLIENT_SECRET: authorization-code-client-secret
OPENID_CLIENT_ISSUER: http://oidc.workadventure.localhost
OPENID_SCOPE: profile openid email tags-scope
```

Setting these in `.env` does nothing today. Same hardcoded-dev-domain class as
`PUBLIC_MAP_STORAGE_URL` and the Matrix values. Note `tags-scope` is the *mock's* invented
scope name — a real provider rejects unknown scopes, so this must be parameterized too, not
just the credentials.

**B2 — `MATRIX_PUBLIC_URI` will hijack every login.** `AuthenticateController.ts:326`: if
`MATRIX_PUBLIC_URI` is non-empty, the OIDC callback does **not** return the user to the game.
It renders a page that redirects into Synapse SSO at
`/_matrix/client/v3/login/sso/redirect`. `docker-compose.yaml:149` hardcodes
`https://matrix.432bleu.com`, which **now resolves in DNS** (5.78.195.138 — someone added the
A record since 2026-08-02) but serves no TLS: `curl` fails with exit 35, no Caddy route, no
cert. So with OIDC on and this value set, **every staff login dead-ends at a TLS error.**

Fix: make it `${MATRIX_PUBLIC_URI:-}` and leave it empty in `.env` until Matrix is genuinely
wired. Do not point OIDC at Matrix and Matrix at OIDC in the same change.

**B3 — `oidc-server-mock` is load-bearing for synapse.** `synapse/start.sh:27` hard-waits on
the mock's well-known and exits 1 after 120s. Retiring the mock container therefore breaks
synapse startup. Since synapse now has `restart: unless-stopped`, that means a crash loop.
Leave the mock running (it is harmless and unreferenced once the issuer points elsewhere)
until the Matrix work handles `start.sh`.

**B4 — `OPENID_TAGS_CLAIM` is not passed through compose.** It defaults to `"tags"`, so this
is survivable rather than fatal, but add it to the passthrough anyway rather than relying on
a default we did not choose.

## Build

### Phase 1 — compose passthrough (no new code)

Replace the `docker-compose.yaml:68-72` literals with `${...}` refs, add
`OPENID_TAGS_CLAIM`, and make `MATRIX_PUBLIC_URI` env-driven and empty. Ship and verify
nothing changed — the mock issuer keeps working through env vars, which proves the
passthrough is correct before any new code exists.

### Phase 2 — the provider in boxoffice

New `boxoffice/app/routes/oidc.py`. **Mounted at app root, not under `/api`** — discovery has
to sit at a fixed well-known path.

| Endpoint | Job |
|---|---|
| `GET /.well-known/openid-configuration` | Static JSON: issuer, authorization/token/userinfo/jwks URIs, `response_types_supported: ["code"]`, `code_challenge_methods_supported: ["S256"]`, `id_token_signing_alg_values_supported: ["RS256"]` |
| `GET /.well-known/jwks.json` | RSA public key as a JWK, with a stable `kid` |
| `GET /authorize` | Validate `client_id` / `redirect_uri` (exact allowlist match) / `response_type=code`. Read `bleu_session` via `get_current_email`. If absent → redirect to `/login?next=<original authorize URL>`. If present → mint code, redirect to `redirect_uri?code=…&state=…` |
| `POST /token` | Client secret auth, `grant_type=authorization_code`. Verify code is unused, unexpired, bound to this client and redirect_uri, and that `SHA256(code_verifier)` matches the stored challenge. Return `access_token`, `id_token` (RS256), `token_type: Bearer`, `expires_in` |
| `GET /userinfo` | Bearer access token → `{sub, email, username, preferred_username, locale, tags}` |

New `AuthCode` model, modelled on `LoginToken` (hashed at rest, single-use `used_at`, short
TTL — 60s is plenty). New dependency: `pyjwt[crypto]` — `authlib` is the alternative but is
Flask/Django-shaped and drags in far more than one client needs.

RSA keypair: generate once, store as `OIDC_PRIVATE_KEY` in `.env` (PEM, newlines escaped),
add to `scripts/vps/setup-secrets.sh` as a fourth tier in `SECRETS.md`.

### Phase 3 — tags

Simplest thing that works for single-digit staff: `OIDC_STAFF_TAGS` in `.env`, e.g.
`skyler@…=admin,editor;soundtech@…=editor`. Parsed at `/userinfo` time, defaults to `[]`.
No new table, no admin UI, no migration. Promote to a `StaffTag` table only when someone
other than you needs to grant a tag.

### Phase 4 — cut over and verify

Set `OPENID_CLIENT_ISSUER=https://432bleu.com`, real client id, `openssl rand -hex 32`
secret, `OPENID_SCOPE="openid email profile"`. Register redirect URI
**`https://play.432bleu.com/openid-callback`** (`AuthenticateController.ts:293`).
Recreate `play`.

Verification ladder, in order — each step isolates one layer:

1. `curl -s https://432bleu.com/.well-known/openid-configuration | python3 -m json.tool`
2. `curl -s https://432bleu.com/.well-known/jwks.json` — one key, `"kty":"RSA"`, `"use":"sig"`
3. Sign in from the WA menu → should land back in the room, not at a Matrix TLS error (B2)
4. Decode the resulting authToken → `tags` present
5. Visit `/~/concert.tmj` → map editor sidebar appears (`RoomConnection.ts:574` gates on `canEdit`)
6. Set room megaphone `rights` + `scope: "ROOM"` → button live for staff, absent for anonymous

Step 6 needs `scope: "ROOM"` explicitly — `getMegaphoneUrl:9` returns undefined without it and
the megaphone silently disables.

## Security notes

- `redirect_uri` must be **exact-match against an allowlist**, never prefix or substring.
  This is the classic OIDC provider hole — an open redirect here hands out auth codes.
- Auth codes: single-use, ~60s TTL, hashed at rest, bound to client + redirect_uri + PKCE
  challenge. Reuse of a burnt code should be treated as an attack, not an error.
- The `/token` endpoint needs its own rate limit; `slowapi` is already wired (`limiter.py`).
- Constant-time compare for `client_secret` (`secrets.compare_digest`).
- Session cookie is `samesite=lax`, which is correct here — the `/authorize` redirect is a
  top-level GET navigation, so the cookie is sent. Do not "fix" this to `strict`; it would
  break the flow.
- `SESSION_SECRET_KEY` defaults to `""` (`session.py:9`) — an empty signing key. Verify it is
  actually set in the VPS `.env` before this carries staff permissions rather than just
  account pages.

## Deliberately out of scope

Matrix SSO (B2/B3), turning on `DISABLE_ANONYMOUS`, and the ticket-gate path-matching hole
(`@gate_root path /` is exact-match, so `/_/*` and `/~/*` are ungated). The gate hole is
worth noting here because OIDC does **not** fix it — it is a separate Caddy change, and
identity for staff is not a substitute for gating the room.
