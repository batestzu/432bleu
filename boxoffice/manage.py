#!/usr/bin/env python3
"""
432 BLEU Box Office — management CLI
Usage:
  python manage.py create-event "Show Name" 2026-07-04 "Optional description"
  python manage.py list-events
  python manage.py sales <event-id>
  python manage.py deactivate <event-id>
  python manage.py init-db
"""
import os
import sys
from datetime import datetime

os.environ.setdefault("DATABASE_URL", "postgresql://boxoffice:boxoffice@localhost:5433/boxoffice")

from app.database import engine, SessionLocal, Base
from app.models import Event, TicketTier, Ticket
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
    else:
        print(__doc__)
