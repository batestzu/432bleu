import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..limiter import limiter
from ..models import Ticket, Membership
from ..cookies import COOKIE_NAME, set_pass_cookie

router = APIRouter()
BOXOFFICE_DOMAIN = os.getenv("BOXOFFICE_DOMAIN", "https://432bleu.com")

TICKET_VALID_HOURS_AFTER_EVENT = 4
MEMBERSHIP_ACTIVE_STATUSES = {"active", "trialing", "past_due"}

# Event dates are stored as naive datetimes entered in venue-local time
VENUE_TZ = ZoneInfo(os.getenv("VENUE_TZ", "America/New_York"))


def _code_grants_access(db: Session, code: str) -> bool:
    ticket = db.query(Ticket).filter(Ticket.code == code).first()
    if ticket:
        event_start = ticket.tier.event.date.replace(tzinfo=VENUE_TZ)
        expires_at = event_start + timedelta(hours=TICKET_VALID_HOURS_AFTER_EVENT)
        return datetime.now(timezone.utc) < expires_at

    membership = db.query(Membership).filter(Membership.code == code).first()
    if membership:
        return membership.status in MEMBERSHIP_ACTIVE_STATUSES

    return False


def find_access_code(db: Session, email: str):
    """The best still-valid access code held by this email, as (code, kind).

    Lets a logged-in session be turned into the bleu_pass cookie the gate checks,
    so a member who arrived by magic link doesn't have to retype a code they own.
    Membership wins over a ticket — it outlives any single event.
    """
    membership = (
        db.query(Membership)
        .filter(Membership.email == email, Membership.status.in_(MEMBERSHIP_ACTIVE_STATUSES))
        .order_by(Membership.created_at.desc())
        .first()
    )
    if membership:
        return membership.code, "membership"

    now = datetime.now(timezone.utc)
    tickets = db.query(Ticket).filter(Ticket.email == email).all()
    for ticket in tickets:
        if not ticket.tier or not ticket.tier.event:
            continue
        event_start = ticket.tier.event.date.replace(tzinfo=VENUE_TZ)
        if now < event_start + timedelta(hours=TICKET_VALID_HOURS_AFTER_EVENT):
            return ticket.code, "ticket"

    return None, None


@router.get("/gate/check")
def gate_check(request: Request, db: Session = Depends(get_db)):
    code = request.cookies.get(COOKIE_NAME, "").upper().strip()
    if code and _code_grants_access(db, code):
        return Response(status_code=200)
    return RedirectResponse(f"{BOXOFFICE_DOMAIN}/enter", status_code=302)


class EnterRequest(BaseModel):
    code: str


@router.post("/gate/enter")
@limiter.limit("10/minute")
def gate_enter(
    request: Request,
    req: EnterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    code = req.code.upper().strip()
    if not _code_grants_access(db, code):
        raise HTTPException(status_code=404, detail="Invalid or expired code")
    set_pass_cookie(response, code)
    return {"success": True}
