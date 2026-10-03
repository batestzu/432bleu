import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..limiter import limiter
from ..models import Ticket, Membership, GateEntry
from ..cookies import COOKIE_NAME, set_pass_cookie
from ..venue_time import VENUE_TZ  # event dates are naive, in venue-local time

router = APIRouter()
logger = logging.getLogger("boxoffice")
BOXOFFICE_DOMAIN = os.getenv("BOXOFFICE_DOMAIN", "https://432bleu.com")

TICKET_VALID_HOURS_AFTER_EVENT = 4
MEMBERSHIP_ACTIVE_STATUSES = {"active", "trialing", "past_due"}


def _access_grant(db: Session, code: str):
    """The Ticket or Membership that `code` currently admits, or None."""
    ticket = db.query(Ticket).filter(Ticket.code == code).first()
    if ticket:
        event_start = ticket.tier.event.date.replace(tzinfo=VENUE_TZ)
        expires_at = event_start + timedelta(hours=TICKET_VALID_HOURS_AFTER_EVENT)
        return ticket if datetime.now(timezone.utc) < expires_at else None

    membership = db.query(Membership).filter(Membership.code == code).first()
    if membership and membership.status in MEMBERSHIP_ACTIVE_STATUSES:
        return membership

    return None


def _code_grants_access(db: Session, code: str) -> bool:
    return _access_grant(db, code) is not None


def _record_entry(db: Session, request: Request, code: str, grant) -> None:
    """Log who the gate let in. Best-effort: a failed write must never turn a valid
    ticket away at the door, so errors are logged and swallowed. Caddy's forward_auth
    passes the visitor's own headers through, plus the page they asked for in
    X-Forwarded-Uri."""
    try:
        is_ticket = isinstance(grant, Ticket)
        db.add(GateEntry(
            code=code,
            kind="ticket" if is_ticket else "membership",
            event_id=grant.event_id if is_ticket else None,
            path=urlsplit(request.headers.get("x-forwarded-uri", "")).path[:500],
            user_agent=request.headers.get("user-agent", "")[:300],
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Gate let %s in but could not record the entry", code)


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
    grant = _access_grant(db, code) if code else None
    if grant is None:
        return RedirectResponse(f"{BOXOFFICE_DOMAIN}/enter", status_code=302)
    _record_entry(db, request, code, grant)
    return Response(status_code=200)


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
