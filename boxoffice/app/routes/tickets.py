import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from ..database import get_db
from ..limiter import limiter
from ..models import Event, TicketTier, Ticket
from ..code_gen import generate_code
from ..email_client import send_ticket_email
from ..cookies import set_pass_cookie

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
DOMAIN = os.getenv("BOXOFFICE_DOMAIN", "https://432bleu.com")


class FreeTicketRequest(BaseModel):
    event_id: int
    tier_id: int
    email: EmailStr
    name: str


class CheckoutRequest(BaseModel):
    event_id: int
    tier_id: int
    email: EmailStr
    name: str
    amount_cents: int  # fixed for VIP/MG, user-supplied for PWYC


def _unique_code(db: Session) -> str:
    for _ in range(10):
        code = generate_code()
        if not db.query(Ticket).filter(Ticket.code == code).first():
            return code
    raise RuntimeError("Could not generate unique code")


@router.post("/tickets/free")
@limiter.limit("5/minute")
def claim_free_ticket(request: Request, req: FreeTicketRequest, response: Response, db: Session = Depends(get_db)):
    tier = db.query(TicketTier).filter(
        TicketTier.id == req.tier_id,
        TicketTier.event_id == req.event_id,
    ).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")
    if tier.name == "PWYC":
        raise HTTPException(status_code=400, detail="Pay What You Can requires a minimum $1 payment")
    if tier.price_cents > 0:
        raise HTTPException(status_code=400, detail="This tier requires payment")
    if tier.capacity is not None and tier.sold >= tier.capacity:
        raise HTTPException(status_code=400, detail="Sold out")

    code = _unique_code(db)
    event = db.query(Event).filter(Event.id == req.event_id).first()

    ticket = Ticket(
        event_id=req.event_id,
        tier_id=req.tier_id,
        code=code,
        email=req.email,
        name=req.name,
        amount_paid_cents=0,
    )
    db.add(ticket)
    tier.sold += 1
    db.commit()

    try:
        send_ticket_email(
            to_email=req.email,
            name=req.name,
            event_name=event.name,
            event_date=event.date.strftime("%B %d, %Y"),
            tier_label=tier.label,
            code=code,
        )
    except Exception:
        pass  # ticket is created; email failure is non-fatal

    set_pass_cookie(response, code)
    return {"success": True}


@router.post("/checkout")
@limiter.limit("10/minute")
def create_checkout(request: Request, req: CheckoutRequest, db: Session = Depends(get_db)):
    tier = db.query(TicketTier).filter(
        TicketTier.id == req.tier_id,
        TicketTier.event_id == req.event_id,
    ).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")
    if tier.capacity is not None and tier.sold >= tier.capacity:
        raise HTTPException(status_code=400, detail="Sold out")

    amount = req.amount_cents if tier.name == "PWYC" else tier.price_cents
    if amount < 100:
        raise HTTPException(status_code=400, detail="Minimum payment is $1.00")

    event = db.query(Event).filter(Event.id == req.event_id).first()

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"{tier.label} — {event.name}",
                    "description": tier.description or "",
                },
                "unit_amount": amount,
            },
            "quantity": 1,
        }],
        mode="payment",
        customer_email=req.email,
        metadata={
            "event_id": str(req.event_id),
            "tier_id": str(req.tier_id),
            "name": req.name,
            "email": req.email,
        },
        success_url=f"{DOMAIN}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{DOMAIN}/events/{req.event_id}",
    )

    return {"checkout_url": session.url}


@router.get("/tickets/by-session")
@limiter.limit("20/minute")
def ticket_by_session(request: Request, session_id: str, response: Response, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.stripe_session_id == session_id).first()
    if not ticket:
        return {"ready": False}
    set_pass_cookie(response, ticket.code)
    return {"ready": True}
