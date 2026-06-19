import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..limiter import limiter
from ..models import Ticket
from ..cookies import COOKIE_NAME, set_pass_cookie

router = APIRouter()
BOXOFFICE_DOMAIN = os.getenv("BOXOFFICE_DOMAIN", "https://432bleu.com")


@router.get("/gate/check")
def gate_check(request: Request, db: Session = Depends(get_db)):
    code = request.cookies.get(COOKIE_NAME, "").upper().strip()
    if code:
        ticket = db.query(Ticket).filter(Ticket.code == code).first()
        if ticket:
            # TODO: once events have a definite end, check
            # ticket.tier.event.date + N hours < now() here and fall through
            # to the redirect below if the ticket's event has expired.
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
    ticket = db.query(Ticket).filter(Ticket.code == code).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Invalid code")
    set_pass_cookie(response, code)
    return {"success": True}
