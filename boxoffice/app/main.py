from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .database import engine, Base
from .limiter import limiter
from .routes import events, tickets, webhooks, validate, gate, membership, crypto


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
