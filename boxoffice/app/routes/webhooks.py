import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Event, TicketTier, Ticket
from ..code_gen import generate_code
from ..email_client import send_ticket_email

router = APIRouter()
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] != "checkout.session.completed":
        return {"status": "ignored"}

    session = event["data"]["object"]

    # Idempotency — Stripe can retry webhooks
    if db.query(Ticket).filter(Ticket.stripe_session_id == session["id"]).first():
        return {"status": "already processed"}

    meta = session.get("metadata", {})
    event_id = int(meta["event_id"])
    tier_id = int(meta["tier_id"])
    name = meta.get("name", "")
    email = meta.get("email", session.get("customer_email", ""))
    amount_paid = session.get("amount_total", 0)

    tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
    db_event = db.query(Event).filter(Event.id == event_id).first()

    code = generate_code()
    for _ in range(10):
        if not db.query(Ticket).filter(Ticket.code == code).first():
            break
        code = generate_code()

    ticket = Ticket(
        event_id=event_id,
        tier_id=tier_id,
        code=code,
        email=email,
        name=name,
        stripe_session_id=session["id"],
        amount_paid_cents=amount_paid,
    )
    db.add(ticket)
    tier.sold += 1
    db.commit()

    try:
        send_ticket_email(
            to_email=email,
            name=name,
            event_name=db_event.name,
            event_date=db_event.date.strftime("%B %d, %Y"),
            tier_label=tier.label,
            code=code,
        )
    except Exception:
        pass

    return {"status": "ok"}
