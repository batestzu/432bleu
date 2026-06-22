#!/usr/bin/env python3
"""
432 BLEU Box Office — management CLI
Usage:
  python manage.py create-event "Show Name" 2026-07-04 "Optional description"
  python manage.py list-events
  python manage.py sales <event-id>
  python manage.py deactivate <event-id>
  python manage.py create-membership-tier "season" "Season Pass" 1000 month "Optional description"
  python manage.py register-membership-tier "season" price_xxx ["Label override"] ["description"]
  python manage.py list-membership-tiers
  python manage.py members
  python manage.py deactivate-membership-tier <tier-id>
  python manage.py init-db
"""
import os
import sys
from datetime import datetime

os.environ.setdefault("DATABASE_URL", "postgresql://boxoffice:boxoffice@localhost:5433/boxoffice")

from app.database import engine, SessionLocal, Base
from app.models import Event, TicketTier, Ticket, MembershipTier, Membership
from sqlalchemy import func


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


def create_event(name, date_str, description=""):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Unrecognized date format: {date_str}")
        event = Event(name=name, date=date, description=description)
        db.add(event)
        db.flush()
        tiers = [
            TicketTier(event_id=event.id, name="GA",   label="General Admission", price_cents=0,     description="Standard access to the show"),
            TicketTier(event_id=event.id, name="PWYC", label="Pay What You Can",  price_cents=0,     description="Support the band — pay any amount"),
            TicketTier(event_id=event.id, name="VIP",  label="VIP",               price_cents=2000,  description="Access to the VIP area", capacity=50),
            TicketTier(event_id=event.id, name="MG",   label="Meet & Greet",      price_cents=15000, description="Meet the band backstage", capacity=10),
        ]
        db.add_all(tiers)
        db.commit()
        print(f"Created event #{event.id}: {name} on {date_str}")
    finally:
        db.close()


def list_events():
    db = SessionLocal()
    try:
        events = db.query(Event).order_by(Event.date).all()
        if not events:
            print("No events.")
            return
        for e in events:
            status = "active" if e.is_active else "inactive"
            print(f"  #{e.id}  [{status}]  {e.name}  —  {e.date.strftime('%Y-%m-%d')}")
    finally:
        db.close()


def sales_report(event_id):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print("Event not found.")
            return
        print(f"\n  {event.name}  —  {event.date.strftime('%Y-%m-%d')}")
        print("  " + "─" * 48)
        tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
        total = 0
        for tier in tiers:
            revenue = db.query(func.sum(Ticket.amount_paid_cents))\
                .filter(Ticket.tier_id == tier.id).scalar() or 0
            cap = f"/ {tier.capacity}" if tier.capacity else ""
            print(f"  {tier.label:<20} {tier.sold}{cap} sold   ${revenue/100:>8.2f}")
            total += revenue
        print("  " + "─" * 48)
        print(f"  {'Total revenue':<20}              ${total/100:>8.2f}\n")
    finally:
        db.close()


def deactivate(event_id):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print("Event not found.")
            return
        event.is_active = False
        db.commit()
        print(f"Event #{event_id} deactivated.")
    finally:
        db.close()


def create_membership_tier(name, label, price_cents, interval, description=""):
    if interval not in ("month", "year"):
        raise ValueError('interval must be "month" or "year"')

    import stripe
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    product = stripe.Product.create(
        name=label,
        description=description or f"{label} membership",
        default_price_data={
            "unit_amount": price_cents,
            "currency": "usd",
            "recurring": {"interval": interval},
        },
    )

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        tier = MembershipTier(
            name=name,
            label=label,
            price_cents=price_cents,
            interval=interval,
            stripe_price_id=product.default_price,
            stripe_product_id=product.id,
            description=description,
        )
        db.add(tier)
        db.commit()
        print(f"Created membership tier #{tier.id}: {label} (${price_cents/100:.2f}/{interval})")
        print(f"  Stripe product: {product.id}  price: {product.default_price}")
    finally:
        db.close()


def register_membership_tier(name, stripe_price_id, label=None, description=""):
    """Register a membership tier from a price already created in the Stripe dashboard."""
    import stripe
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    price = stripe.Price.retrieve(stripe_price_id, expand=["product"])
    if not price.recurring:
        raise ValueError(f"{stripe_price_id} is not a recurring price")

    product = price.product
    final_label = label or product.name
    final_description = description or (product.description or "")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        tier = MembershipTier(
            name=name,
            label=final_label,
            price_cents=price.unit_amount,
            interval=price.recurring.interval,
            stripe_price_id=price.id,
            stripe_product_id=product.id,
            description=final_description,
        )
        db.add(tier)
        db.commit()
        print(f"Registered membership tier #{tier.id}: {final_label} "
              f"(${price.unit_amount/100:.2f}/{price.recurring.interval})")
    finally:
        db.close()


def list_membership_tiers():
    db = SessionLocal()
    try:
        tiers = db.query(MembershipTier).all()
        if not tiers:
            print("No membership tiers.")
            return
        for t in tiers:
            status = "active" if t.is_active else "inactive"
            print(f"  #{t.id}  [{status}]  {t.label}  —  ${t.price_cents/100:.2f}/{t.interval}  ({t.stripe_price_id})")
    finally:
        db.close()


def deactivate_membership_tier(tier_id):
    db = SessionLocal()
    try:
        tier = db.query(MembershipTier).filter(MembershipTier.id == tier_id).first()
        if not tier:
            print("Membership tier not found.")
            return
        tier.is_active = False
        db.commit()
        print(f"Membership tier #{tier_id} deactivated.")
    finally:
        db.close()


def list_members():
    db = SessionLocal()
    try:
        memberships = db.query(Membership).order_by(Membership.created_at).all()
        if not memberships:
            print("No members.")
            return
        for m in memberships:
            print(f"  #{m.id}  [{m.status}]  {m.name or m.email}  —  {m.tier.label}  —  code {m.code}")
    finally:
        db.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "init-db":
        init_db()
    elif cmd == "create-event":
        if len(sys.argv) < 4:
            print('Usage: python manage.py create-event "Name" YYYY-MM-DD ["description"]')
        else:
            create_event(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    elif cmd == "list-events":
        list_events()
    elif cmd == "sales":
        if len(sys.argv) < 3:
            print("Usage: python manage.py sales <event-id>")
        else:
            sales_report(int(sys.argv[2]))
    elif cmd == "deactivate":
        if len(sys.argv) < 3:
            print("Usage: python manage.py deactivate <event-id>")
        else:
            deactivate(int(sys.argv[2]))
    elif cmd == "create-membership-tier":
        if len(sys.argv) < 5:
            print('Usage: python manage.py create-membership-tier "name" "Label" <price_cents> <month|year> ["description"]')
        else:
            create_membership_tier(
                sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5],
                sys.argv[6] if len(sys.argv) > 6 else "",
            )
    elif cmd == "register-membership-tier":
        if len(sys.argv) < 4:
            print('Usage: python manage.py register-membership-tier "name" price_xxx ["Label override"] ["description"]')
        else:
            register_membership_tier(
                sys.argv[2], sys.argv[3],
                sys.argv[4] if len(sys.argv) > 4 else None,
                sys.argv[5] if len(sys.argv) > 5 else "",
            )
    elif cmd == "list-membership-tiers":
        list_membership_tiers()
    elif cmd == "deactivate-membership-tier":
        if len(sys.argv) < 3:
            print("Usage: python manage.py deactivate-membership-tier <tier-id>")
        else:
            deactivate_membership_tier(int(sys.argv[2]))
    elif cmd == "members":
        list_members()
    else:
        print(__doc__)
