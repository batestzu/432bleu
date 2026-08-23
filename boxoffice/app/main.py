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


@app.get("/account")
def account_page():
    return FileResponse("/app/frontend/account.html")
