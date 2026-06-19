import os
from fastapi import Response

COOKIE_NAME = "bleu_pass"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", ".432bleu.com")
COOKIE_MAX_AGE = 60 * 60 * 24 * 180  # 180 days


def set_pass_cookie(response: Response, code: str):
    response.set_cookie(
        COOKIE_NAME, code,
        domain=COOKIE_DOMAIN, max_age=COOKIE_MAX_AGE,
        httponly=True, secure=True, samesite="lax", path="/",
    )
