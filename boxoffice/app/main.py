import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .database import engine, Base
from .limiter import limiter
from .routes import events, tickets, webhooks, validate, gate, membership, crypto, auth, oidc, survey


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(events.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(validate.router, prefix="/api")
app.include_router(gate.router, prefix="/api")
app.include_router(membership.router, prefix="/api")
app.include_router(crypto.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(survey.router, prefix="/api")
# OIDC provider lives at the app root: /.well-known/* must be at a fixed path.
app.include_router(oidc.router)

@app.middleware("http")
async def revalidate_by_default(request: Request, call_next):
    """Make browsers check with us before reusing anything they've cached.

    There is no build step here: the .jsx and .html files ARE the deploy artifact,
    served from stable URLs with no content hash, so every deploy reuses the same
    URLs. Starlette sends etag and last-modified but no Cache-Control, and with no
    Cache-Control a browser is free to apply *heuristic* freshness — commonly a
    fraction of the age since last-modified — and serve a stale copy without asking.
    That is how a fix can be verifiably live to curl and still show the old page in
    a browser for hours.

    "no-cache" is not "don't cache": it keeps the copy and requires revalidation,
    which the etag answers with a cheap 304. Anything that wants real caching can
    still set its own Cache-Control — setdefault leaves it alone.
    """
    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-cache")
    return response


app.mount("/static", StaticFiles(directory="/app/frontend/static"), name="static")

# Large binaries -- the pitch-deck video today, show footage later -- are served from
# a host bind-mount rather than from the image (see the boxoffice `volumes:` block in
# docker-compose.yaml). Git history is append-only, so anything committed is permanent
# weight for every future clone; this keeps media out of both the repo and the image
# layers, and lets a new file go live with an scp instead of a rebuild.
#
# The directory is created first so a fresh clone or a run without the compose file
# still starts: StaticFiles raises at import time if its directory is missing, which
# would take the whole box office down over an absent video.
MEDIA_DIR = "/app/media"
os.makedirs(MEDIA_DIR, exist_ok=True)
# Inherits the default Cache-Control: no-cache from the middleware above, on purpose --
# footage gets replaced under the same filename while a cut is being iterated on, and
# revalidation makes the new file appear on the next load instead of after a TTL.
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


@app.get("/")
def index():
    return FileResponse("/app/frontend/index.html")


@app.get("/events")
def events_list():
    return RedirectResponse(url="/", status_code=302)


@app.get("/events/{event_id}")
def event_page(event_id: int):
    return FileResponse("/app/frontend/event.html")


@app.get("/success")
def success_page():
    return FileResponse("/app/frontend/success.html")


@app.get("/enter")
def enter_page():
    return FileResponse("/app/frontend/enter.html")


@app.get("/artists")
def artists_page():
    return FileResponse("/app/frontend/artists.html")


@app.get("/membership")
def membership_page():
    return FileResponse("/app/frontend/membership.html")


@app.get("/membership/success")
def membership_success_page():
    return FileResponse("/app/frontend/membership-success.html")


@app.get("/login")
def login_page():
    return FileResponse("/app/frontend/login.html")


@app.get("/survey")
def survey_page():
    return FileResponse("/app/frontend/survey.html")


@app.get("/survey/short")
def survey_short_page():
    """Same file, cold-traffic cut. survey.html reads the path and drops section B,
    most of the social battery, NPS and two open questions -- one stylesheet and one
    submit path instead of a fork that drifts. Recruitment links carry ?src= too:
    /survey/short?src=prolific."""
    return FileResponse("/app/frontend/survey.html")


@app.get("/privacy")
def privacy_page():
    return FileResponse("/app/frontend/privacy.html")


@app.get("/pitch/slides-4f2a")
def pitch_deck():
    """The investor deck, served unlisted rather than gated.

    Nothing links here and the path segment is unguessable, so the only way in is a
    link we sent. That keeps a cold send frictionless -- an investor opening this on
    a phone should see slide one, not a login -- while X-Robots-Tag keeps it out of
    search if the URL ever leaks into a crawlable place. Deliberately NOT added to
    robots.txt: a Disallow would advertise the path, and we are about to buy ads, so
    the rest of the site needs to stay indexable."""
    return FileResponse(
        "/app/frontend/pitch.html",
        headers={"X-Robots-Tag": "noindex, nofollow, noarchive"},
    )


@app.get("/pitch/slides-4f2a/appendix")
def pitch_appendix():
    """Survey data behind the deck, under the deck's own token rather than a second
    one. It goes to the same people in the same email, so a separate secret would be
    two things to keep track of protecting nothing extra -- anyone holding the deck
    link is already meant to see the numbers under it."""
    return FileResponse(
        "/app/frontend/appendix.html",
        headers={"X-Robots-Tag": "noindex, nofollow, noarchive"},
    )


@app.get("/account")
def account_page():
    return FileResponse("/app/frontend/account.html")
