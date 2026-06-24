"""
Deal Tracker — pipeline management via WhatsApp.
Tracks deals through stages: lead → viewing → offer → negotiation → accepted → bond_pending → closed → lost
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.database import Deal, Listing, Lead, Agent

logger = logging.getLogger(__name__)


DEAL_STAGES = [
    "lead",
    "viewing",
    "offer",
    "negotiation",
    "accepted",
    "bond_pending",
    "closed",
    "lost",
]

STAGE_EMOJI = {
    "lead": "🔍",
    "viewing": "👁️",
    "offer": "💰",
    "negotiation": "🤝",
    "accepted": "✅",
    "bond_pending": "🏦",
    "closed": "🎉",
    "lost": "❌",
}


class DealTracker:
    """Manages the deal pipeline."""

    async def create_deal(
        self,
        db: AsyncSession,
        agent_id: str,
        lead_id: Optional[str] = None,
        listing_id: Optional[str] = None,
        deal_type: str = "sale",
        deal_value: Optional[float] = None,
    ) -> Deal:
        """Create a new deal."""
        deal = Deal(
            agent_id=agent_id,
            lead_id=lead_id,
            listing_id=listing_id,
            deal_type=deal_type,
            deal_value=deal_value,
            deal_stage="lead",
            stage_history=json.dumps([{"stage": "lead", "date": datetime.utcnow().isoformat()}]),
        )
        db.add(deal)
        await db.commit()
        await db.refresh(deal)
        logger.info(f"🆕 Deal created: {deal.id}")
        return deal

    async def update_stage(
        self, db: AsyncSession, deal_id: str, new_stage: str, notes: Optional[str] = None
    ) -> Optional[Deal]:
        """Advance a deal to a new stage."""
        result = await db.execute(select(Deal).where(Deal.id == deal_id))
        deal = result.scalar_one_or_none()
        if not deal:
            return None

        deal.deal_stage = new_stage
        deal.updated_at = datetime.utcnow()

        # Append to stage history
        history = json.loads(deal.stage_history or "[]")
        history.append({
            "stage": new_stage,
            "date": datetime.utcnow().isoformat(),
            "notes": notes,
        })
        deal.stage_history = json.dumps(history)

        # Auto-calculate commission on close
        if new_stage == "closed" and deal.deal_value:
            deal.commission_estimate = deal.deal_value * 0.07  # 7% standard

        await db.commit()
        await db.refresh(deal)
        logger.info(f"📋 Deal {deal_id} → {new_stage}")
        return deal

    async def get_pipeline(self, db: AsyncSession, agent_id: str) -> Dict[str, Any]:
        """Get full pipeline summary for an agent."""
        result = await db.execute(
            select(Deal).where(
                Deal.agent_id == agent_id,
                Deal.deal_stage.notin_(["closed", "lost"]),
            ).order_by(Deal.updated_at.desc())
        )
        deals = result.scalars().all()

        # Closed this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        closed_result = await db.execute(
            select(func.count(), func.sum(Deal.deal_value)).where(
                Deal.agent_id == agent_id,
                Deal.deal_stage == "closed",
                Deal.updated_at >= month_start,
            )
        )
        closed_stats = closed_result.one()

        by_stage = {}
        total_value = 0
        total_commission = 0

        for deal in deals:
            stage = deal.deal_stage
            if stage not in by_stage:
                by_stage[stage] = []
            by_stage[stage].append({
                "id": deal.id[:8],
                "stage": deal.deal_stage,
                "value": deal.deal_value,
            })
            if deal.deal_stage != "lost":
                total_value += deal.deal_value or 0
                total_commission += (deal.deal_value or 0) * 0.07

        return {
            "active_deals": len(deals),
            "by_stage": {s: len(d) for s, d in by_stage.items()},
            "pipeline_value": total_value,
            "est_commission": total_commission,
            "closed_this_month": closed_stats[0] or 0,
            "closed_value": closed_stats[1] or 0,
            "hot_deals": by_stage.get("offer", []) + by_stage.get("negotiation", []) + by_stage.get("accepted", []),
        }

    async def format_pipeline_message(self, db: AsyncSession, agent_id: str) -> str:
        """Format pipeline as a WhatsApp-friendly message."""
        pipeline = await self.get_pipeline(db, agent_id)

        msg = "📊 *Your Pipeline*\n\n"
        emoji_stages = {s: f"{STAGE_EMOJI.get(s, '📌')} *{s.title()}*" for s in DEAL_STAGES}

        for stage, count in pipeline["by_stage"].items():
            emoji = STAGE_EMOJI.get(stage, "📌")
            msg += f"{emoji} *{stage.title()}*: {count} deal(s)\n"

        msg += f"\n💰 *Pipeline Value:* R{pipeline['pipeline_value']:,.0f}\n"
        msg += f"💵 *Est. Commission:* R{pipeline['est_commission']:,.0f}\n"

        if pipeline["hot_deals"]:
            msg += f"\n🔥 *Hot Deals:* {len(pipeline['hot_deals'])} requiring attention\n"

        if pipeline["closed_this_month"]:
            msg += f"\n✅ *Closed this month:* {pipeline['closed_this_month']} (R{pipeline['closed_value']:,.0f})"

        return msg


# Singleton
deal_tracker = DealTracker()
