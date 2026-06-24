"""
Agent Management API — onboarding, settings, subscription management.
Also serves as the backend for the web dashboard.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.database import get_db, Agent, Listing, Lead, Deal, RentalUnit, ScheduledTask
from app.services.deals import deal_tracker
from app.services.listings import listing_service
from app.services.rentals import rental_manager
from app.services.followup import follow_up_manager
from app.services.market import market_watch
from app.services.evolution import evolution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


# ── Agent Management ──────────────────────────────────

@router.post("/agents")
async def create_agent(request: dict, db: AsyncSession = Depends(get_db)):
    """Register a new agent. Called from the onboarding flow."""
    phone = request.get("whatsapp_number", "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="whatsapp_number required")

    # Check if already exists
    result = await db.execute(select(Agent).where(Agent.whatsapp_number == phone))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Agent already registered")

    agent = Agent(
        whatsapp_number=phone,
        display_name=request.get("display_name", "New Agent"),
        business_name=request.get("business_name"),
        areas=json.dumps(request.get("areas", [])),
        property_types=json.dumps(request.get("property_types", ["house"])),
        price_range_min=request.get("price_range_min"),
        price_range_max=request.get("price_range_max"),
        subscription_tier=request.get("subscription_tier", "starter"),
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # Send welcome message via WhatsApp
    try:
        await evolution.send_text(
            phone,
            f"🎉 *Welcome to iGosa, {agent.display_name}!*\n\n"
            f"Your WhatsApp AI assistant is now active. Here's what you can do:\n\n"
            f"🏠 Add listings: 'add listing: 3 bed Pimville R450K'\n"
            f"📊 Check pipeline: 'pipeline'\n"
            f"📈 Get valuations: 'value: 3 bed Diepkloof'\n"
            f"🏦 Bond checks: 'can I afford R400K?'\n"
            f"📄 Documents: 'docs [deal_id]'\n"
            f"📱 Social posts: 'post [listing_id]'\n\n"
            f"Just type your command or forward client messages to this number!\n\n"
            f"_Need help? Just ask 'help'_"
        )
    except Exception as e:
        logger.warning(f"Could not send welcome message: {e}")

    return {"id": agent.id, "display_name": agent.display_name, "whatsapp_number": agent.whatsapp_number}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Get agent details."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "id": agent.id,
        "display_name": agent.display_name,
        "business_name": agent.business_name,
        "whatsapp_number": agent.whatsapp_number,
        "areas": json.loads(agent.areas or "[]"),
        "subscription_tier": agent.subscription_tier,
        "is_active": agent.is_active,
    }


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, request: dict, db: AsyncSession = Depends(get_db)):
    """Update agent settings."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    for field in ["display_name", "business_name", "subscription_tier"]:
        if field in request:
            setattr(agent, field, request[field])

    if "areas" in request:
        agent.areas = json.dumps(request["areas"])
    if "property_types" in request:
        agent.property_types = json.dumps(request["property_types"])
    if "price_range_min" in request:
        agent.price_range_min = request["price_range_min"]
    if "price_range_max" in request:
        agent.price_range_max = request["price_range_max"]

    await db.commit()
    return {"status": "updated"}


# ── Dashboard Stats ───────────────────────────────────

@router.get("/dashboard/{agent_id}")
async def get_dashboard(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Get agent dashboard with all stats."""
    # Agent info
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Listing stats
    listing_stats = await listing_service.get_stats(db, agent_id)

    # Pipeline
    pipeline = await deal_tracker.get_pipeline(db, agent_id)

    # Leads
    lead_result = await db.execute(
        select(func.count()).select_from(Lead).where(Lead.agent_id == agent_id)
    )
    lead_count = lead_result.scalar() or 0

    new_lead_result = await db.execute(
        select(func.count()).select_from(Lead).where(
            Lead.agent_id == agent_id, Lead.lead_status == "new"
        )
    )
    new_leads = new_lead_result.scalar() or 0

    # Pending follow-ups
    pending = await follow_up_manager.get_pending_count(db, agent_id)

    # Rental summary
    rental_summary = await rental_manager.get_portfolio_summary(db, agent_id)

    # Market hot areas
    hot = await market_watch.get_hot_areas()

    # Pending tasks
    task_result = await db.execute(
        select(func.count()).select_from(ScheduledTask).where(
            ScheduledTask.agent_id == agent_id, ScheduledTask.status == "pending"
        )
    )
    pending_tasks = task_result.scalar() or 0

    return {
        "agent": {
            "name": agent.display_name,
            "business": agent.business_name,
            "tier": agent.subscription_tier,
        },
        "listings": listing_stats,
        "pipeline": {
            "active_deals": pipeline["active_deals"],
            "pipeline_value": pipeline["pipeline_value"],
            "est_commission": pipeline["est_commission"],
            "closed_this_month": pipeline["closed_this_month"],
            "hot_deals": len(pipeline["hot_deals"]),
        },
        "leads": {
            "total": lead_count,
            "new": new_leads,
        },
        "tasks": {
            "pending_follow_ups": pending,
            "pending_total": pending_tasks,
        },
        "rentals": {
            "units": rental_summary.get("total_units", 0),
            "collected": rental_summary.get("collected", 0),
            "outstanding": rental_summary.get("outstanding", 0),
        },
        "market": hot,
    }


# ── Task Processing (for cron) ────────────────────────

@router.post("/tasks/process")
async def process_tasks(db: AsyncSession = Depends(get_db)):
    """Process all due tasks. Called by cron/external scheduler."""
    sent = await follow_up_manager.process_due_tasks(db)
    return {"processed": sent, "status": "ok"}


@router.get("/tasks/pending/{agent_id}")
async def get_pending_tasks(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Get pending tasks for an agent."""
    result = await db.execute(
        select(ScheduledTask).where(
            ScheduledTask.agent_id == agent_id,
            ScheduledTask.status == "pending",
        ).order_by(ScheduledTask.scheduled_for).limit(20)
    )
    tasks = result.scalars().all()
    return [
        {
            "id": t.id,
            "type": t.task_type,
            "scheduled_for": t.scheduled_for.isoformat() if t.scheduled_for else None,
            "message": t.custom_message[:100] if t.custom_message else None,
            "status": t.status,
        }
        for t in tasks
    ]


# ── Quick Commands (WhatsApp accessible) ──────────────

@router.get("/quick/stats/{agent_id}")
async def quick_stats(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Quick stats suitable for WhatsApp responses."""
    listing_stats = await listing_service.get_stats(db, agent_id)
    pipeline = await deal_tracker.get_pipeline(db, agent_id)
    pending = await follow_up_manager.get_pending_count(db, agent_id)

    return {
        "listings_active": listing_stats["active"],
        "deals_active": pipeline["active_deals"],
        "pipeline_value": f"R{pipeline['pipeline_value']:,.0f}",
        "pending_follow_ups": pending,
    }
