import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..limiter import limiter
from ..models import LoginToken, Ticket, Membership, CryptoOrder
from ..email_client import send_login_email
from ..session import set_session_cookie, clear_session_cookie, get_current_email
from ..cookies import set_pass_cookie
from .gate import find_access_code

router = APIRouter()
BOXOFFICE_DOMAIN = os.getenv("BOXOFFICE_DOMAIN", "https://432bleu.com")
PLAY_URL = os.getenv("PLAY_URL", "https://play.432bleu.com")

TOKEN_TTL_MINUTES = 15
MAX_TOKENS_PER_HOUR = 5

# Login tokens are only needed for the 15-min TTL plus the 1-hour rate-limit
# window; anything older is pure (email, timestamp) retention with no purpose.
TOKEN_RETENTION_HOURS = 24
ANONYMIZED_EMAIL = "deleted@anonymized.invalid"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RequestLinkBody(BaseModel):
    email: EmailStr


@router.post("/auth/request-link")
@limiter.limit("5/minute")
def request_link(request: Request, req: RequestLinkBody, db: Session = Depends(get_db)):
    email = req.email.lower().strip()

    # Opportunistic retention cleanup — keeps the table from accumulating a
    # permanent log of every login attempt (GDPR storage limitation).
    cutoff = datetime.now(timezone.utc) - timedelta(hours=TOKEN_RETENTION_HOURS)
    db.query(LoginToken).filter(LoginToken.created_at < cutoff).delete()

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_count = db.query(LoginToken).filter(
        LoginToken.email == email,
        LoginToken.created_at > one_hour_ago,
    ).count()

    if recent_count < MAX_TOKENS_PER_HOUR:
        token = secrets.token_urlsafe(32)
        login_token = LoginToken(
            email=email,
            token_hash=_hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MINUTES),
        )
        db.add(login_token)
        db.commit()

        link = f"{BOXOFFICE_DOMAIN}/api/auth/verify?token={token}"
        try:
            send_login_email(to_email=email, link=link)
        except Exception:
            pass

    # always return success — never reveal whether the email exists or was rate-limited
    return {"success": True}


@router.get("/auth/verify")
def verify(request: Request, token: str, db: Session = Depends(get_db)):
    login_token = db.query(LoginToken).filter(LoginToken.token_hash == _hash_token(token)).first()
    if not login_token:
        raise HTTPException(status_code=400, detail="Invalid or expired login link")

    expires_at = login_token.expires_at.replace(tzinfo=timezone.utc)
    if login_token.used_at or datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired login link")

    login_token.used_at = datetime.now(timezone.utc)
    db.commit()

    # If an OIDC /authorize redirect sent the user here, resume it (routes/oidc.py
    # sets bleu_next). Same-site relative paths only — "//host" would be an open
    # redirect. Best-effort: if the magic link was opened in a different browser,
    # the cookie is absent and we land on /account as before.
    next_path = request.cookies.get("bleu_next", "")
    if not (next_path.startswith("/") and not next_path.startswith("//") and "\\" not in next_path):
        next_path = "/account"

    response = RedirectResponse(f"{BOXOFFICE_DOMAIN}{next_path}", status_code=302)
    response.delete_cookie("bleu_next", path="/")
    set_session_cookie(response, login_token.email)
    return response


@router.post("/auth/logout")
def logout():
    response = Response(status_code=200)
    clear_session_cookie(response)
    return response


@router.get("/auth/me")
def me(email: str = Depends(get_current_email), db: Session = Depends(get_db)):
    code, kind = find_access_code(db, email)
    return {"email": email, "has_access": code is not None, "access_kind": kind, "play_url": PLAY_URL}


@router.post("/auth/room-pass")
def room_pass(response: Response, email: str = Depends(get_current_email), db: Session = Depends(get_db)):
    """Mint the bleu_pass gate cookie from a logged-in session.

    The Caddy ticket gate only ever checks bleu_pass (gate.py::gate_check); a magic-link
    login sets bleu_session, a different cookie. Without this, a logged-in member tapping
    "enter the room" lands back on /enter to retype a code they already own.
    """
    code, kind = find_access_code(db, email)
    if not code:
        raise HTTPException(status_code=403, detail="No active membership or valid ticket on this account.")
    set_pass_cookie(response, code)
    return {"ok": True, "access_kind": kind, "play_url": PLAY_URL}


@router.get("/auth/export")
@limiter.limit("5/minute")
def export_data(request: Request, email: str = Depends(get_current_email), db: Session = Depends(get_db)):
    """GDPR Art. 15/20: everything we hold about the logged-in email, as JSON."""
    tickets = db.query(Ticket).filter(Ticket.email == email).all()
    memberships = db.query(Membership).filter(Membership.email == email).all()
    crypto_orders = db.query(CryptoOrder).filter(CryptoOrder.email == email).all()

    return {
        "email": email,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tickets": [
            {
                "event_id": t.event_id,
                "tier": t.tier.label if t.tier else None,
                "code": t.code,
                "name": t.name,
                "amount_paid_cents": t.amount_paid_cents,
                "used_at": t.used_at.isoformat() if t.used_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tickets
        ],
        "memberships": [
            {
                "tier": m.tier.label if m.tier else None,
                "code": m.code,
                "name": m.name,
                "status": m.status,
                "current_period_end": m.current_period_end.isoformat() if m.current_period_end else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memberships
        ],
        "crypto_orders": [
            {
                "order_id": o.order_id,
                "kind": o.kind,
                "name": o.name,
                "amount_cents": o.amount_cents,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in crypto_orders
        ],
    }


@router.post("/auth/delete-account")
@limiter.limit("3/minute")
def delete_account(request: Request, email: str = Depends(get_current_email), db: Session = Depends(get_db)):
    """GDPR Art. 17: strip identity from our records.

    Transactional rows (tickets, memberships, crypto orders) are kept for
    accounting but anonymized — email and name are overwritten, so nothing ties
    them to a person. Login tokens are deleted outright. Ticket codes remain
    valid: they are bearer codes and carry no identity once anonymized.

    Refuses while a paid membership is still active/past_due — deleting the
    email while Stripe keeps billing would orphan the subscription. Cancel via
    the billing portal first.
    """
    billing = db.query(Membership).filter(
        Membership.email == email,
        Membership.status.in_(["active", "past_due"]),
    ).count()
    if billing:
        raise HTTPException(
            status_code=409,
            detail="You have an active membership. Cancel it in the billing portal first, then delete your account.",
        )

    db.query(Ticket).filter(Ticket.email == email).update(
        {Ticket.email: ANONYMIZED_EMAIL, Ticket.name: ""}, synchronize_session=False
    )
    db.query(Membership).filter(Membership.email == email).update(
        {Membership.email: ANONYMIZED_EMAIL, Membership.name: ""}, synchronize_session=False
    )
    db.query(CryptoOrder).filter(CryptoOrder.email == email).update(
        {CryptoOrder.email: ANONYMIZED_EMAIL, CryptoOrder.name: ""}, synchronize_session=False
    )
    db.query(LoginToken).filter(LoginToken.email == email).delete(synchronize_session=False)
    db.commit()

    response = Response(status_code=200)
    clear_session_cookie(response)
    return response
