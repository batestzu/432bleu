#!/usr/bin/env python3
"""
432 BLEU Box Office — management CLI
Usage:
  python manage.py create-event "Show Name" 2026-07-04 "Optional description" ["2026-07-04 20:00"]
  python manage.py set-date <event-id> "2026-07-04"
  python manage.py set-doors-time <event-id> "2026-07-04 20:00"
  python manage.py list-events
  python manage.py sales <event-id>
  python manage.py deactivate <event-id>
  python manage.py mark-sold-out <event-id>
  python manage.py set-capacity <event-id> <tier-name> <capacity|none>
  python manage.py export-survey [out.csv]
  python manage.py list-tickets <email>
  python manage.py resend-ticket <code>
  python manage.py issue-ticket <event-id> <tier-name> <email> "Name"
  python manage.py create-membership-tier "season" "Season Pass" 1000 month "Optional description"
  python manage.py register-membership-tier "season" price_xxx ["Label override"] ["description"]
  python manage.py list-membership-tiers
  python manage.py members
  python manage.py grant-membership "season" you@example.com "Your Name" [days=365]
  python manage.py deactivate-membership-tier <tier-id>
  python manage.py init-db
"""
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://boxoffice:boxoffice@localhost:5433/boxoffice")

from app.database import engine, SessionLocal, Base
from app.models import Event, TicketTier, Ticket, MembershipTier, Membership, SurveyResponse
from app.code_gen import generate_code
from app.email_client import send_ticket_email, send_membership_email
from sqlalchemy import func


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


def _parse_date(date_str):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str}")


def create_event(name, date_str, description="", doors_str=None):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        date = _parse_date(date_str)
        doors = _parse_date(doors_str) if doors_str else None
        event = Event(name=name, date=date, doors_time=doors, description=description)
        db.add(event)
        db.flush()
        tiers = [
            TicketTier(event_id=event.id, name="GA",   label="General Admission", price_cents=0,     description="Standard access to the show", capacity=40),
            TicketTier(event_id=event.id, name="PWYC", label="Pay What You Can",  price_cents=0,     description="Support the band — pay any amount", capacity=60),
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


def set_event_date(event_id, date_str):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print("Event not found.")
            return
        event.date = _parse_date(date_str)
        db.commit()
        print(f"Event #{event_id} date set to {date_str}")
    finally:
        db.close()


def set_doors_time(event_id, doors_str):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print("Event not found.")
            return
        event.doors_time = _parse_date(doors_str)
        db.commit()
        print(f"Event #{event_id} doors set to {doors_str}")
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


def mark_sold_out(event_id):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print("Event not found.")
            return
        tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
        if not tiers:
            print("Event has no ticket tiers.")
            return
        for tier in tiers:
            tier.capacity = tier.sold
        db.commit()
        print(f"Event #{event_id} ({event.name}) marked sold out — capacity capped at current sold count for all {len(tiers)} tier(s).")
    finally:
        db.close()


def set_capacity(event_id, tier_name, capacity):
    """capacity is the TOTAL allotment for the tier, not the remaining count —
    sold already counts against it, so remaining = capacity - sold. "none" = unlimited."""
    db = SessionLocal()
    try:
        tier = db.query(TicketTier).filter(
            TicketTier.event_id == event_id,
            TicketTier.name == tier_name.upper(),
        ).first()
        if not tier:
            print(f"Tier '{tier_name}' not found for event #{event_id}")
            return
        cap = None if str(capacity).lower() in ("none", "unlimited", "") else int(capacity)
        if cap is not None and cap < tier.sold:
            print(f"Warning: capacity {cap} is below {tier.sold} already sold — tier reads as sold out.")
        tier.capacity = cap
        db.commit()
        shown = "unlimited" if cap is None else cap
        remaining = "unlimited" if cap is None else max(cap - tier.sold, 0)
        print(f"Event #{event_id} {tier.label}: capacity set to {shown} "
              f"({tier.sold} sold, {remaining} remaining)")
    finally:
        db.close()


def export_survey(path=None):
    """Flatten the JSON answer blobs into a CSV. Columns are the union of every key
    seen, in first-seen order, so a questionnaire that gained or lost a question
    between rounds still exports as one table."""
    import csv
    db = SessionLocal()
    try:
        rows = db.query(SurveyResponse).order_by(SurveyResponse.created_at).all()
        if not rows:
            print("No survey responses.")
            return
        keys = []
        for r in rows:
            for k in r.answers or {}:
                if k not in keys:
                    keys.append(k)
        out = open(path, "w", newline="") if path else sys.stdout
        try:
            writer = csv.writer(out)
            writer.writerow(["id", "created_at"] + keys)
            for r in rows:
                answers = r.answers or {}
                writer.writerow([r.id, r.created_at.isoformat()] + [answers.get(k, "") for k in keys])
        finally:
            if path:
                out.close()
        if path:
            print(f"Wrote {len(rows)} response(s) to {path}")
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


def list_tickets(email):
    db = SessionLocal()
    try:
        tickets = db.query(Ticket).filter(Ticket.email == email).order_by(Ticket.created_at.desc()).all()
        if not tickets:
            print(f"No tickets found for {email}")
            return
        for t in tickets:
            print(f"  #{t.id}  code={t.code}  tier={t.tier.label}  event={t.tier.event.name}  created={t.created_at.strftime('%Y-%m-%d %H:%M')}")
    finally:
        db.close()


def resend_ticket(code):
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.code == code).first()
        if not ticket:
            print(f"No ticket with code {code}")
            return
        event = ticket.tier.event
        send_ticket_email(
            to_email=ticket.email,
            name=ticket.name,
            event_name=event.name,
            event_date=event.date.strftime("%B %d, %Y"),
            tier_label=ticket.tier.label,
            code=ticket.code,
        )
        print(f"Resent ticket {code} to {ticket.email}")
    finally:
        db.close()


def issue_ticket(event_id, tier_name, email, name):
    db = SessionLocal()
    try:
        tier = db.query(TicketTier).filter(
            TicketTier.event_id == event_id,
            TicketTier.name == tier_name.upper(),
        ).first()
        if not tier:
            print(f"Tier '{tier_name}' not found for event #{event_id}")
            return
        event = db.query(Event).filter(Event.id == event_id).first()
        for _ in range(10):
            code = generate_code()
            if not db.query(Ticket).filter(Ticket.code == code).first():
                break
        else:
            print("Could not generate unique code")
            return
        ticket = Ticket(event_id=event_id, tier_id=tier.id, code=code, email=email, name=name, amount_paid_cents=0)
        db.add(ticket)
        tier.sold += 1
        db.commit()
        send_ticket_email(
            to_email=email,
            name=name,
            event_name=event.name,
            event_date=event.date.strftime("%B %d, %Y"),
            tier_label=tier.label,
            code=code,
        )
        print(f"Issued ticket {code} ({tier.label}) to {email}")
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


def grant_membership(tier_name, email, name, days=365):
    """Comp/test membership — creates an active Membership with no Stripe subscription
    behind it, so it never bills and never auto-renews. Good for staff/test accounts;
    not a substitute for a real subscription."""
    db = SessionLocal()
    try:
        tier = db.query(MembershipTier).filter(MembershipTier.name == tier_name).first()
        if not tier:
            print(f"Membership tier '{tier_name}' not found")
            return
        for _ in range(10):
            code = generate_code()
            if not db.query(Membership).filter(Membership.code == code).first():
                break
        else:
            print("Could not generate unique code")
            return
        membership = Membership(
            tier_id=tier.id,
            code=code,
            email=email,
            name=name,
            status="active",
            current_period_end=datetime.now(timezone.utc) + timedelta(days=days),
        )
        db.add(membership)
        db.commit()
        send_membership_email(to_email=email, name=name, tier_label=tier.label, code=code)
        print(f"Granted membership {code} ({tier.label}) to {email}, active {days} days (comp/test — no Stripe subscription behind it)")
    finally:
        db.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "init-db":
        init_db()
    elif cmd == "create-event":
        if len(sys.argv) < 4:
            print('Usage: python manage.py create-event "Name" YYYY-MM-DD ["description"] ["YYYY-MM-DD HH:MM doors"]')
        else:
            create_event(sys.argv[2], sys.argv[3],
                         sys.argv[4] if len(sys.argv) > 4 else "",
                         sys.argv[5] if len(sys.argv) > 5 else None)
    elif cmd == "set-date":
        if len(sys.argv) < 4:
            print('Usage: python manage.py set-date <event-id> "YYYY-MM-DD"')
        else:
            set_event_date(int(sys.argv[2]), sys.argv[3])
    elif cmd == "set-doors-time":
        if len(sys.argv) < 4:
            print('Usage: python manage.py set-doors-time <event-id> "YYYY-MM-DD HH:MM"')
        else:
            set_doors_time(int(sys.argv[2]), sys.argv[3])
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
    elif cmd == "mark-sold-out":
        if len(sys.argv) < 3:
            print("Usage: python manage.py mark-sold-out <event-id>")
        else:
            mark_sold_out(int(sys.argv[2]))
    elif cmd == "set-capacity":
        if len(sys.argv) < 5:
            print("Usage: python manage.py set-capacity <event-id> <tier-name> <capacity|none>")
        else:
            set_capacity(int(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif cmd == "export-survey":
        export_survey(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "list-tickets":
        if len(sys.argv) < 3:
            print("Usage: python manage.py list-tickets <email>")
        else:
            list_tickets(sys.argv[2])
    elif cmd == "resend-ticket":
        if len(sys.argv) < 3:
            print("Usage: python manage.py resend-ticket <code>")
        else:
            resend_ticket(sys.argv[2])
    elif cmd == "issue-ticket":
        if len(sys.argv) < 6:
            print('Usage: python manage.py issue-ticket <event-id> <tier-name> <email> "Name"')
        else:
            issue_ticket(int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5])
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
    elif cmd == "grant-membership":
        if len(sys.argv) < 5:
            print('Usage: python manage.py grant-membership <tier-name> <email> "Name" [days=365]')
        else:
            grant_membership(sys.argv[2], sys.argv[3], sys.argv[4],
                              int(sys.argv[5]) if len(sys.argv) > 5 else 365)
    else:
        print(__doc__)
