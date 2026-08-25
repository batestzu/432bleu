from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Event, TicketTier
from ..venue_time import venue_iso

router = APIRouter()


@router.get("/events")
def list_events(db: Session = Depends(get_db)):
    events = db.query(Event).filter(Event.is_active == True).order_by(Event.date).all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "date": venue_iso(e.date),
            "doors_time": venue_iso(e.doors_time),
            "description": e.description,
        }
        for e in events
    ]


@router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id, Event.is_active == True).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    # Explicit order or Postgres hands back heap order, which means editing a tier
    # (set-capacity rewrites the row) silently moves it to the bottom of the page.
    # Cheapest first, so the free/PWYC ways in lead.
    tiers = (
        db.query(TicketTier)
        .filter(TicketTier.event_id == event_id)
        .order_by(TicketTier.price_cents, TicketTier.id)
        .all()
    )
    return {
        "id": event.id,
        "name": event.name,
        "date": venue_iso(event.date),
        "doors_time": venue_iso(event.doors_time),
        "description": event.description,
        "tiers": [
            {
                "id": t.id,
                "name": t.name,
                "label": t.label,
                "price_cents": t.price_cents,
                "capacity": t.capacity,
                "sold": t.sold,
                "description": t.description,
                "available": t.capacity is None or t.sold < t.capacity,
            }
            for t in tiers
        ],
    }
