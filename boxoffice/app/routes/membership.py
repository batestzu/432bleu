import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from ..database import get_db
from ..limiter import limiter
from ..models import MembershipTier, Membership
from ..cookies import COOKIE_NAME, set_pass_cookie

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
DOMAIN = os.getenv("BOXOFFICE_DOMAIN", "https://432bleu.com")


class MembershipCheckoutRequest(BaseModel):
    tier_id: int
    email: EmailStr
    name: str


@router.get("/membership/tiers")
def list_membership_tiers(db: Session = Depends(get_db)):
    tiers = db.query(MembershipTier).filter(MembershipTier.is_active == True).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "label": t.label,
            "price_cents": t.price_cents,
            "interval": t.interval,
            "description": t.description,
        }
        for t in tiers
    ]


@router.post("/membership/checkout")
@limiter.limit("10/minute")
def create_membership_checkout(request: Request, req: MembershipCheckoutRequest, db: Session = Depends(get_db)):
    tier = db.query(MembershipTier).filter(
        MembershipTier.id == req.tier_id,
        MembershipTier.is_active == True,
    ).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Membership tier not found")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": tier.stripe_price_id, "quantity": 1}],
        mode="subscription",
        customer_email=req.email,
        metadata={
            "tier_id": str(req.tier_id),
            "name": req.name,
            "email": req.email,
        },
        subscription_data={
            "metadata": {
                "tier_id": str(req.tier_id),
                "name": req.name,
                "email": req.email,
            },
        },
        success_url=f"{DOMAIN}/membership/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{DOMAIN}/membership",
    )

    return {"checkout_url": session.url}


@router.get("/membership/by-session")
@limiter.limit("20/minute")
def membership_by_session(request: Request, session_id: str, response: Response, db: Session = Depends(get_db)):
    membership = db.query(Membership).filter(Membership.stripe_session_id == session_id).first()
    if not membership:
        return {"ready": False}
    set_pass_cookie(response, membership.code)
    return {"ready": True}


@router.post("/membership/portal")
@limiter.limit("10/minute")
def membership_portal(request: Request, db: Session = Depends(get_db)):
    code = request.cookies.get(COOKIE_NAME, "").upper().strip()
    membership = db.query(Membership).filter(Membership.code == code).first()
    if not membership or not membership.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No active membership found")

    session = stripe.billing_portal.Session.create(
        customer=membership.stripe_customer_id,
        return_url=f"{DOMAIN}/membership",
    )
    return {"portal_url": session.url}
