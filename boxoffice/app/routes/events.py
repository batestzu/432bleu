from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Event, TicketTier

router = APIRouter()


@router.get("/events")
def list_events(db: Session = Depends(get_db)):
    events = db.query(Event).filter(Event.is_active == True).order_by(Event.date).all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "date": e.date.isoformat(),
            "doors_time": e.doors_time.isoformat() if e.doors_time else None,
            "description": e.description,
        }
        for e in events
    ]


@router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id, Event.is_active == True).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
    return {
        "id": event.id,
        "name": event.name,
        "date": event.date.isoformat(),
        "doors_time": event.doors_time.isoformat() if event.doors_time else None,
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
