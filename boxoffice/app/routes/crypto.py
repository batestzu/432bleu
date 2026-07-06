import os
import secrets
import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from ..database import get_db
from ..limiter import limiter
from ..models import Event, TicketTier, CryptoOrder
from ..cookies import set_pass_cookie

router = APIRouter()
DOMAIN = os.getenv("BOXOFFICE_DOMAIN", "https://432bleu.com")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY", "")
NOWPAYMENTS_API_URL = "https://api.nowpayments.io/v1/invoice"


class CryptoCheckoutRequest(BaseModel):
    event_id: int
    tier_id: int
    email: EmailStr
    name: str
    amount_cents: int  # fixed for VIP/MG, user-supplied for PWYC


def _unique_order_id(db: Session) -> str:
    for _ in range(10):
        order_id = secrets.token_hex(12)
        if not db.query(CryptoOrder).filter(CryptoOrder.order_id == order_id).first():
            return order_id
    raise RuntimeError("Could not generate unique order id")


@router.post("/checkout/crypto")
@limiter.limit("10/minute")
def create_crypto_checkout(request: Request, req: CryptoCheckoutRequest, db: Session = Depends(get_db)):
    if not NOWPAYMENTS_API_KEY:
        raise HTTPException(status_code=503, detail="Crypto checkout is not configured")

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
    if amount < 1000:
        raise HTTPException(status_code=400, detail="Crypto payments require a minimum of $10.00 due to BTC network limits. Please use card payment or enter a higher amount.")

    event = db.query(Event).filter(Event.id == req.event_id).first()
    order_id = _unique_order_id(db)

    order = CryptoOrder(
        order_id=order_id,
        kind="ticket",
        event_id=req.event_id,
        tier_id=req.tier_id,
        email=req.email,
        name=req.name,
        amount_cents=amount,
    )
    db.add(order)
    db.commit()

    def _fail(detail: str):
        # invoice never got created — drop the pending order so it doesn't linger
        db.delete(order)
        db.commit()
        raise HTTPException(status_code=502, detail=detail)

    try:
        resp = requests.post(
            NOWPAYMENTS_API_URL,
            headers={"x-api-key": NOWPAYMENTS_API_KEY, "Content-Type": "application/json"},
            json={
                "price_amount": amount / 100,
                "price_currency": "usd",
                "order_id": order_id,
                "order_description": f"{tier.label} — {event.name}",
                "ipn_callback_url": f"{DOMAIN}/api/webhooks/nowpayments",
                "success_url": f"{DOMAIN}/success?order_id={order_id}",
                "cancel_url": f"{DOMAIN}/events/{req.event_id}",
            },
            timeout=15,
        )
    except requests.RequestException:
        _fail("Crypto payment provider error")

    if not resp.ok:
        err_msg = "Crypto payment provider error"
        try:
            err_msg = resp.json().get("message", err_msg)
        except Exception:
            pass
        _fail(err_msg)

    invoice_url = resp.json().get("invoice_url")
    if not invoice_url:
        _fail("Crypto payment provider error")

    return {"checkout_url": invoice_url}


@router.get("/checkout/crypto/by-order")
@limiter.limit("20/minute")
def crypto_order_status(request: Request, order_id: str, response: Response, db: Session = Depends(get_db)):
    order = db.query(CryptoOrder).filter(CryptoOrder.order_id == order_id).first()
    if not order or order.status != "finished" or not order.result_code:
        return {"ready": False}
    set_pass_cookie(response, order.result_code)
    return {"ready": True}
