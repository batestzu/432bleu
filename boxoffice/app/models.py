from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    description = Column(String, default="")
    is_active = Column(Boolean, default=True)
    tiers = relationship("TicketTier", back_populates="event")


class TicketTier(Base):
    __tablename__ = "ticket_tiers"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)   # GA, PWYC, VIP, MG
    label = Column(String, nullable=False)  # Display name
    price_cents = Column(Integer, default=0)
    capacity = Column(Integer, nullable=True)  # None = unlimited
    sold = Column(Integer, default=0)
    description = Column(String, default="")
    event = relationship("Event", back_populates="tiers")
    tickets = relationship("Ticket", back_populates="tier")


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    tier_id = Column(Integer, ForeignKey("ticket_tiers.id"), nullable=False)
    code = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=False)
    name = Column(String, default="")
    stripe_session_id = Column(String, nullable=True, unique=True)
    amount_paid_cents = Column(Integer, default=0)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    tier = relationship("TicketTier", back_populates="tickets")
