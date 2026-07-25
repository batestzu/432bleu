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
from ..models import LoginToken
from ..email_client import send_login_email
from ..session import set_session_cookie, clear_session_cookie, get_current_email

router = APIRouter()
BOXOFFICE_DOMAIN = os.getenv("BOXOFFICE_DOMAIN", "https://432bleu.com")

TOKEN_TTL_MINUTES = 15
MAX_TOKENS_PER_HOUR = 5


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RequestLinkBody(BaseModel):
    email: EmailStr


@router.post("/auth/request-link")
@limiter.limit("5/minute")
def request_link(request: Request, req: RequestLinkBody, db: Session = Depends(get_db)):
    email = req.email.lower().strip()

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
def verify(token: str, db: Session = Depends(get_db)):
    login_token = db.query(LoginToken).filter(LoginToken.token_hash == _hash_token(token)).first()
    if not login_token:
        raise HTTPException(status_code=400, detail="Invalid or expired login link")

    expires_at = login_token.expires_at.replace(tzinfo=timezone.utc)
    if login_token.used_at or datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired login link")

    login_token.used_at = datetime.now(timezone.utc)
    db.commit()

    response = RedirectResponse(f"{BOXOFFICE_DOMAIN}/account", status_code=302)
    set_session_cookie(response, login_token.email)
    return response


@router.post("/auth/logout")
def logout():
    response = Response(status_code=200)
    clear_session_cookie(response)
    return response


@router.get("/auth/me")
def me(email: str = Depends(get_current_email)):
    return {"email": email}
