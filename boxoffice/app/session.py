import os
from fastapi import Request, Response, HTTPException
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SESSION_COOKIE_NAME = "bleu_session"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", ".432bleu.com")
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "")

# An empty key would make session cookies forgeable by anyone who has read this
# file — refuse to start rather than silently sign with "".
if not SESSION_SECRET_KEY:
    raise RuntimeError("SESSION_SECRET_KEY is empty — set it in .env before starting boxoffice")

_serializer = URLSafeTimedSerializer(SESSION_SECRET_KEY, salt="bleu-session")


def set_session_cookie(response: Response, email: str):
    token = _serializer.dumps({"email": email})
    response.set_cookie(
        SESSION_COOKIE_NAME, token,
        domain=COOKIE_DOMAIN, max_age=SESSION_MAX_AGE,
        httponly=True, secure=True, samesite="lax", path="/",
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME, domain=COOKIE_DOMAIN, path="/")


def get_current_email(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return data["email"]
