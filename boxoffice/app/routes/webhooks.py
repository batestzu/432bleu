import hmac
import hashlib
import json
import os
import stripe
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Event, TicketTier, Ticket, MembershipTier, Membership, CryptoOrder
from ..code_gen import generate_code
from ..email_client import send_ticket_email, send_membership_email

router = APIRouter()
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET", "")


def _unique_code(db: Session, model) -> str:
    code = generate_code()
    for _ in range(10):
        if not db.query(model).filter(model.code == code).first():
            return code
        code = generate_code()
    return code


def _handle_ticket_checkout(db: Session, session):
    if db.query(Ticket).filter(Ticket.stripe_session_id == session["id"]).first():
        return

    meta = session.get("metadata", {})
    event_id = int(meta["event_id"])
    tier_id = int(meta["tier_id"])
    name = meta.get("name", "")
    email = meta.get("email", session.get("customer_email", ""))
    amount_paid = session.get("amount_total", 0)

    tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
    db_event = db.query(Event).filter(Event.id == event_id).first()

    ticket = Ticket(
        event_id=event_id,
        tier_id=tier_id,
        code=_unique_code(db, Ticket),
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
            code=ticket.code,
        )
    except Exception:
        pass


def _handle_membership_checkout(db: Session, session):
    if db.query(Membership).filter(Membership.stripe_session_id == session["id"]).first():
        return

    meta = session.get("metadata", {})
    tier_id = int(meta["tier_id"])
    name = meta.get("name", "")
    email = meta.get("email", session.get("customer_email", ""))

    tier = db.query(MembershipTier).filter(MembershipTier.id == tier_id).first()

    membership = Membership(
        tier_id=tier_id,
        code=_unique_code(db, Membership),
        email=email,
        name=name,
        stripe_customer_id=session.get("customer"),
        stripe_subscription_id=session.get("subscription"),
        stripe_session_id=session["id"],
        status="active",
    )
    db.add(membership)
    db.commit()

    try:
        send_membership_email(
            to_email=email,
            name=name,
            tier_label=tier.label,
            code=membership.code,
        )
    except Exception:
        pass


def _handle_subscription_updated(db: Session, subscription):
    membership = db.query(Membership).filter(
        Membership.stripe_subscription_id == subscription["id"]
    ).first()
    if not membership:
        return
    membership.status = subscription.get("status", membership.status)
    period_end = subscription.get("current_period_end")
    if period_end:
        membership.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
    db.commit()


def _handle_subscription_deleted(db: Session, subscription):
    membership = db.query(Membership).filter(
        Membership.stripe_subscription_id == subscription["id"]
    ).first()
    if not membership:
        return
    membership.status = "canceled"
    db.commit()


def _verify_nowpayments_sig(payload: bytes, sig: str) -> bool:
    if not NOWPAYMENTS_IPN_SECRET or not sig:
        return False
    body = json.loads(payload)
    sorted_body = json.dumps(body, sort_keys=True, separators=(",", ":"))
    expected = hmac.new(
        NOWPAYMENTS_IPN_SECRET.encode(), sorted_body.encode(), hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, sig)


def _handle_crypto_ticket_finished(db: Session, order: CryptoOrder):
    if order.status == "finished":
        return

    tier = db.query(TicketTier).filter(TicketTier.id == order.tier_id).first()
    db_event = db.query(Event).filter(Event.id == order.event_id).first()

    ticket = Ticket(
        event_id=order.event_id,
        tier_id=order.tier_id,
        code=_unique_code(db, Ticket),
        email=order.email,
        name=order.name,
        amount_paid_cents=order.amount_cents,
    )
    db.add(ticket)
    tier.sold += 1
    order.status = "finished"
    order.result_code = ticket.code
    db.commit()

    try:
        send_ticket_email(
            to_email=order.email,
            name=order.name,
            event_name=db_event.name,
            event_date=db_event.date.strftime("%B %d, %Y"),
            tier_label=tier.label,
            code=ticket.code,
        )
    except Exception:
        pass


@router.post("/webhooks/nowpayments")
async def nowpayments_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("x-nowpayments-sig", "")

    if not _verify_nowpayments_sig(payload, sig):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = json.loads(payload)
    order_id = event.get("order_id")
    payment_status = event.get("payment_status")

    order = db.query(CryptoOrder).filter(CryptoOrder.order_id == order_id).first()
    if not order:
        return {"status": "ignored"}

    if payment_status in ("finished", "confirmed"):
        order.nowpayments_payment_id = str(event.get("payment_id", ""))
        if order.kind == "ticket":
            _handle_crypto_ticket_finished(db, order)
    elif payment_status in ("failed", "expired", "refunded"):
        order.status = "failed"
        order.nowpayments_payment_id = str(event.get("payment_id", ""))
        db.commit()

    return {"status": "ok"}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        if obj.get("mode") == "subscription":
            _handle_membership_checkout(db, obj)
        else:
            _handle_ticket_checkout(db, obj)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(db, obj)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(db, obj)
    else:
        return {"status": "ignored"}

    return {"status": "ok"}
