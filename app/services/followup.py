"""
FollowUp Service — automated follow-up sequences for leads.
Handles scheduling, drip sequences, and event-triggered follow-ups.

Sequence definitions:
- NEW_LEAD: 24h, 72h, 7d
- VIEWED_PROPERTY: 48h, 5d, 10d  
- BOND_IN_PROGRESS: weekly
- COLD_LEAD: bi-weekly "new listings" check
- OFFER_MADE: every 48h
- POST_SALE: 1mo, 3mo, 6mo
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.config import settings
from app.services.evolution import evolution

logger = logging.getLogger(__name__)


# ── Follow-Up Sequences ───────────────────────────────

@dataclass
class FollowUpStep:
    delay_hours: int
    message_template: str
    condition: Optional[str] = None  # e.g., "no_reply", "bond_pending"


FOLLOW_UP_SEQUENCES = {
    "new_lead": [
        FollowUpStep(24, "Hi {name}! 👋 Just checking in — still looking for a {beds}bed in {area}? I have some new options I can share with you."),
        FollowUpStep(72, "Hi {name}, hope you're well! 🏠 Still on the hunt for your perfect place in {area}? I'd love to help you find it."),
        FollowUpStep(168, "Hi {name}! 👋 Haven't heard from you in a bit. If you're still looking, I have some great {area} listings. If not, no worries — just let me know!"),
    ],
    "viewed_property": [
        FollowUpStep(48, "Hi {name}! 👋 How did you feel about the {suburb} property? Any questions I can answer?"),
        FollowUpStep(120, "Hi {name}, quick check-in — still thinking about the {suburb} place? The seller is motivated and open to offers."),
        FollowUpStep(240, "Hi {name}! 🏠 The {suburb} property is still available. Price is negotiable — want to make an offer?"),
    ],
    "bond_in_progress": [
        FollowUpStep(168, "Hi {name}, how's the bond application going with {originator}? Need any docs from our side?"),
        FollowUpStep(336, "Hi {name}, any update from the bank on your bond? Let me know if I can help push things along."),
    ],
    "cold_lead": [
        FollowUpStep(336, "Hi {name}! 🏠 New listings just came in for {area}. Would you like me to send them?"),
        FollowUpStep(672, "Hi {name}, hope all is well! Just checking if your property plans have changed — I'm here when you're ready."),
    ],
    "offer_made": [
        FollowUpStep(48, "Hi {name}, any thoughts on the offer? The seller is waiting for feedback. Happy to discuss if you have concerns!"),
        FollowUpStep(96, "Hi {name}, following up on the offer for {suburb}. The seller is flexible on terms — want to negotiate?"),
    ],
    "post_sale": [
        FollowUpStep(720, "Hi {name}! 🎉 Hope you're enjoying your new home! Everything settled in okay?"),
        FollowUpStep(2160, "Hi {name}, just checking in! If you ever need property advice — buying, selling, or renting — I'm here."),
    ],
}


# ── Follow-Up Manager ─────────────────────────────────

class FollowUpManager:
    """Manages automated follow-up sequences for leads."""

    async def schedule_sequence(
        self,
        db: AsyncSession,
        lead_id: str,
        agent_id: str,
        sequence_name: str,
        context: Dict[str, Any] = None,
    ):
        """Schedule a full follow-up sequence for a lead."""
        from app.services.database import ScheduledTask, Lead

        sequence = FOLLOW_UP_SEQUENCES.get(sequence_name, [])
        if not sequence:
            return

        context = context or {}

        # Load lead for name
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        lead_name = lead.display_name if lead and lead.display_name else "there"

        tasks_created = 0
        for step in sequence:
            scheduled_time = datetime.utcnow() + timedelta(hours=step.delay_hours)
            message = step.message_template.format(
                name=lead_name,
                **context,
                area=context.get("area", "your area"),
                beds=context.get("beds", ""),
                suburb=context.get("suburb", ""),
                originator=context.get("originator", "the bond originator"),
            )

            task = ScheduledTask(
                agent_id=agent_id,
                task_type="follow_up",
                lead_id=lead_id,
                scheduled_for=scheduled_time,
                status="pending",
                message_template=sequence_name,
                custom_message=message,
            )
            db.add(task)
            tasks_created += 1

        await db.commit()
        logger.info(f"📅 Scheduled {tasks_created} follow-ups for lead {lead_id} ({sequence_name})")

    async def cancel_sequence(self, db: AsyncSession, lead_id: str):
        """Cancel all pending follow-ups for a lead (e.g., when they become a client)."""
        from app.services.database import ScheduledTask

        result = await db.execute(
            select(ScheduledTask).where(
                and_(
                    ScheduledTask.lead_id == lead_id,
                    ScheduledTask.status == "pending",
                    ScheduledTask.task_type == "follow_up",
                )
            )
        )
        tasks = result.scalars().all()
        for task in tasks:
            task.status = "cancelled"
        await db.commit()
        logger.info(f"❌ Cancelled {len(tasks)} follow-ups for lead {lead_id}")

    async def process_due_tasks(self, db: AsyncSession):
        """Process all due follow-up tasks. Called by scheduler/cron."""
        from app.services.database import ScheduledTask

        result = await db.execute(
            select(ScheduledTask).where(
                and_(
                    ScheduledTask.status == "pending",
                    ScheduledTask.scheduled_for <= datetime.utcnow(),
                )
            ).limit(20)  # Process in batches
        )
        tasks = result.scalars().all()

        sent = 0
        for task in tasks:
            try:
                # Load lead for WhatsApp number
                from app.services.database import Lead
                lead_result = await db.execute(select(Lead).where(Lead.id == task.lead_id))
                lead = lead_result.scalar_one_or_none()

                if not lead:
                    task.status = "failed"
                    task.error_message = "Lead not found"
                    continue

                # Send follow-up message
                message = task.custom_message or "Hi! Just checking in — how's your property search going? 🏠"
                await evolution.send_text(lead.whatsapp_number, message)

                # Update task
                task.status = "sent"
                # Update lead last_contacted
                lead.last_contacted = datetime.utcnow()
                lead.next_follow_up = None

                sent += 1
                logger.info(f"📤 Follow-up sent to {lead.whatsapp_number}")

            except Exception as e:
                task.status = "failed"
                task.error_message = str(e)[:500]
                task.attempts += 1
                logger.error(f"❌ Follow-up failed for task {task.id}: {e}")

        await db.commit()
        return sent

    async def get_pending_count(self, db: AsyncSession, agent_id: str) -> int:
        """Get count of pending follow-ups for an agent."""
        from app.services.database import ScheduledTask
        from sqlalchemy import func

        result = await db.execute(
            select(func.count()).select_from(ScheduledTask).where(
                and_(
                    ScheduledTask.agent_id == agent_id,
                    ScheduledTask.status == "pending",
                    ScheduledTask.task_type == "follow_up",
                )
            )
        )
        return result.scalar() or 0


# ── Follow-Up Triggers ────────────────────────────────

async def trigger_follow_up_on_new_lead(db: AsyncSession, lead_id: str, agent_id: str, entities: Dict[str, Any]):
    """Trigger follow-up sequence when a new lead is created."""
    manager = FollowUpManager()
    context = {
        "area": entities.get("area", "your preferred area"),
        "beds": str(entities.get("bedrooms", "")),
    }
    await manager.schedule_sequence(db, lead_id, agent_id, "new_lead", context)


async def trigger_follow_up_on_viewing(db: AsyncSession, lead_id: str, agent_id: str, listing_suburb: str):
    """Trigger follow-up after a property viewing."""
    manager = FollowUpManager()
    context = {"suburb": listing_suburb}
    await manager.schedule_sequence(db, lead_id, agent_id, "viewed_property", context)


async def trigger_follow_up_on_offer(db: AsyncSession, lead_id: str, agent_id: str, suburb: str):
    """Trigger follow-up when an offer is made."""
    manager = FollowUpManager()
    context = {"suburb": suburb}
    await manager.schedule_sequence(db, lead_id, agent_id, "offer_made", context)


# Singleton
follow_up_manager = FollowUpManager()
