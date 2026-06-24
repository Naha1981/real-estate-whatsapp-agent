"""
Database models and session management.
Uses SQLAlchemy with async SQLite (production-ready for Render free tier).
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, func
from datetime import datetime
import uuid
from typing import Optional, List

from app.config import settings


# ── Engine & Session ──────────────────────────────────

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Models ────────────────────────────────────────────

class Agent(Base):
    """Registered estate agent or agency."""
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    whatsapp_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    business_name: Mapped[Optional[str]] = mapped_column(String(200))
    areas: Mapped[Optional[str]] = mapped_column(Text)  # JSON array: '["Soweto","Pimville"]'
    property_types: Mapped[Optional[str]] = mapped_column(Text)  # JSON array
    price_range_min: Mapped[Optional[float]] = mapped_column(Float)
    price_range_max: Mapped[Optional[float]] = mapped_column(Float)
    subscription_tier: Mapped[str] = mapped_column(String(20), default="starter")
    subscription_status: Mapped[str] = mapped_column(String(20), default="active")
    ffc_number: Mapped[Optional[str]] = mapped_column(String(50))
    ppra_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Listing(Base):
    """Property listing."""
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/under_offer/sold/rented/archived
    property_type: Mapped[str] = mapped_column(String(30), default="house")
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer)
    floor_area_sqm: Mapped[Optional[int]] = mapped_column(Integer)
    erf_size_sqm: Mapped[Optional[int]] = mapped_column(Integer)
    address: Mapped[Optional[str]] = mapped_column(Text)
    suburb: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    city: Mapped[str] = mapped_column(String(50), default="Johannesburg")
    price: Mapped[float] = mapped_column(Float, nullable=False)
    price_type: Mapped[str] = mapped_column(String(10), default="sale")  # sale/rent
    listing_type: Mapped[Optional[str]] = mapped_column(String(20))  # sole_mandate/open
    photos: Mapped[Optional[str]] = mapped_column(Text)  # JSON array of URLs
    features: Mapped[Optional[str]] = mapped_column(Text)  # JSON array
    rdp_restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    rdp_restriction_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Lead(Base):
    """Prospective buyer, seller, tenant, or landlord."""
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    whatsapp_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    lead_type: Mapped[Optional[str]] = mapped_column(String(20))  # buyer/seller/tenant/landlord
    budget_min: Mapped[Optional[float]] = mapped_column(Float)
    budget_max: Mapped[Optional[float]] = mapped_column(Float)
    preferred_areas: Mapped[Optional[str]] = mapped_column(Text)  # JSON array
    preferred_type: Mapped[Optional[str]] = mapped_column(String(30))  # house/apartment/rdp
    bedrooms_min: Mapped[Optional[int]] = mapped_column(Integer)
    bedrooms_max: Mapped[Optional[int]] = mapped_column(Integer)
    pre_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    pre_approved_amount: Mapped[Optional[float]] = mapped_column(Float)
    bond_status: Mapped[Optional[str]] = mapped_column(String(30))
    qualification_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    lead_source: Mapped[Optional[str]] = mapped_column(String(30))
    lead_status: Mapped[str] = mapped_column(String(20), default="new")
    last_contacted: Mapped[Optional[datetime]] = mapped_column(DateTime)
    next_follow_up: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text)  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Conversation(Base):
    """Message log for AI context tracking."""
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10))  # inbound/outbound
    message_type: Mapped[str] = mapped_column(String(20), default="text")  # text/voice/image/video
    message_text: Mapped[Optional[str]] = mapped_column(Text)
    media_url: Mapped[Optional[str]] = mapped_column(Text)
    intent_classified: Mapped[Optional[str]] = mapped_column(String(30))
    ai_responded: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_response: Mapped[Optional[str]] = mapped_column(Text)
    handoff_to_human: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Deal(Base):
    """Active transaction/pipeline deal."""
    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    listing_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("listings.id"))
    lead_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("leads.id"))
    deal_type: Mapped[str] = mapped_column(String(20), default="sale")  # sale/purchase/rental
    deal_value: Mapped[Optional[float]] = mapped_column(Float)
    commission_estimate: Mapped[Optional[float]] = mapped_column(Float)
    deal_stage: Mapped[str] = mapped_column(String(30), default="lead")
    offer_amount: Mapped[Optional[float]] = mapped_column(Float)
    offer_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    bond_originator: Mapped[Optional[str]] = mapped_column(String(100))
    bond_status: Mapped[Optional[str]] = mapped_column(String(30))
    transferring_attorney: Mapped[Optional[str]] = mapped_column(String(200))
    estimated_close_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    documents_collected: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    stage_history: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class RentalUnit(Base):
    """Managed rental property."""
    __tablename__ = "rental_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    listing_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("listings.id"))
    tenant_name: Mapped[str] = mapped_column(String(100))
    tenant_whatsapp: Mapped[str] = mapped_column(String(20))
    monthly_rent: Mapped[float] = mapped_column(Float, nullable=False)
    deposit: Mapped[Optional[float]] = mapped_column(Float)
    lease_start: Mapped[Optional[datetime]] = mapped_column(DateTime)
    lease_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    payment_day: Mapped[int] = mapped_column(Integer, default=1)
    rent_collected_current_month: Mapped[bool] = mapped_column(Boolean, default=False)
    maintenance_requests: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ScheduledTask(Base):
    """Scheduled follow-ups, reminders, alerts."""
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(30))  # follow_up/rent_reminder/report/market_alert/social_post
    lead_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("leads.id"))
    deal_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("deals.id"))
    rental_unit_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("rental_units.id"))
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    message_template: Mapped[Optional[str]] = mapped_column(String(100))
    custom_message: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
