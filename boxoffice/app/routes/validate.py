import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..limiter import limiter
from ..models import Ticket, TicketTier

router = APIRouter()

STAFF_TOKEN = os.getenv("STAFF_TOKEN", "")
_bearer = HTTPBearer()

TIER_AREA = {
    "GA":   "audience",
    "PWYC": "audience",
    "VIP":  "vip",
    "MG":   "meetgreet",
}


def require_staff(credentials: HTTPAuthorizationCredentials = Security(_bearer)):
    if not STAFF_TOKEN:
        raise HTTPException(status_code=500, detail="STAFF_TOKEN not configured")
    if credentials.credentials != STAFF_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid staff token")


class ValidateRequest(BaseModel):
    code: str


@router.post("/validate-code")
@limiter.limit("10/minute")
def validate_code(
    request: Request,
    req: ValidateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_staff),
):
    ticket = db.query(Ticket).filter(Ticket.code == req.code.upper().strip()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Invalid code")
    if ticket.used_at:
        raise HTTPException(status_code=410, detail="Code already used")

    tier = db.query(TicketTier).filter(TicketTier.id == ticket.tier_id).first()
    area = TIER_AREA.get(tier.name, "audience")

    ticket.used_at = datetime.now(timezone.utc)
    db.commit()

    return {"valid": True, "area": area, "tier": tier.name, "name": ticket.name}
