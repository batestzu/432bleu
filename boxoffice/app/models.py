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


class MembershipTier(Base):
    __tablename__ = "membership_tiers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)    # "season", "vip" — internal key
    label = Column(String, nullable=False)   # Display name, e.g. "Season Pass"
    price_cents = Column(Integer, nullable=False)
    interval = Column(String, default="month")  # "month" or "year"
    stripe_price_id = Column(String, nullable=False)
    stripe_product_id = Column(String, nullable=True)
    description = Column(String, default="")
    is_active = Column(Boolean, default=True)
    memberships = relationship("Membership", back_populates="tier")


class Membership(Base):
    __tablename__ = "memberships"
    id = Column(Integer, primary_key=True)
    tier_id = Column(Integer, ForeignKey("membership_tiers.id"), nullable=False)
    code = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=False)
    name = Column(String, default="")
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, unique=True)
    stripe_session_id = Column(String, nullable=True, unique=True)
    status = Column(String, default="incomplete")  # active, past_due, canceled, incomplete
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    tier = relationship("MembershipTier", back_populates="memberships")


class CryptoOrder(Base):
    __tablename__ = "crypto_orders"
    id = Column(Integer, primary_key=True)
    order_id = Column(String, unique=True, nullable=False, index=True)
    kind = Column(String, nullable=False)  # "ticket" or "membership"
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    tier_id = Column(Integer, nullable=False)  # ticket_tiers.id or membership_tiers.id depending on kind
    email = Column(String, nullable=False)
    name = Column(String, default="")
    amount_cents = Column(Integer, default=0)
    nowpayments_payment_id = Column(String, nullable=True, index=True)
    status = Column(String, default="pending")  # pending, finished, failed
    result_code = Column(String, nullable=True)  # ticket/membership code, set once payment finishes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
