"""
Rental Manager — full rental portfolio management via WhatsApp.
Handles rent reminders, payment tracking, and maintenance requests.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.database import RentalUnit, Listing
from app.services.evolution import evolution

logger = logging.getLogger(__name__)


class RentalManager:
    """Manages rental portfolios — payments, maintenance, leases."""

    async def add_rental_unit(
        self,
        db: AsyncSession,
        agent_id: str,
        tenant_name: str,
        tenant_whatsapp: str,
        monthly_rent: float,
        listing_id: Optional[str] = None,
        deposit: Optional[float] = None,
        lease_start: Optional[datetime] = None,
        lease_end: Optional[datetime] = None,
    ) -> RentalUnit:
        """Register a new rental unit."""
        unit = RentalUnit(
            agent_id=agent_id,
            listing_id=listing_id,
            tenant_name=tenant_name,
            tenant_whatsapp=tenant_whatsapp,
            monthly_rent=monthly_rent,
            deposit=deposit,
            lease_start=lease_start or datetime.utcnow(),
            lease_end=lease_end,
            payment_day=1,
            rent_collected_current_month=False,
            maintenance_requests=json.dumps([]),
        )
        db.add(unit)
        await db.commit()
        await db.refresh(unit)

        # Send welcome message to tenant
        await evolution.send_text(
            tenant_whatsapp,
            f"🏠 *Welcome!* Your rental has been registered.\n"
            f"Monthly Rent: R{monthly_rent:,.0f}\n"
            f"Payment Day: 1st of each month\n"
            f"Deposit Paid: R{deposit:,.0f}\n\n"
            f"For maintenance or queries, just message this number!"
        )

        return unit

    async def send_rent_reminder(self, db: AsyncSession, unit: RentalUnit):
        """Send rent reminder to a tenant."""
        days_until_due = (datetime.utcnow().replace(day=unit.payment_day) - datetime.utcnow()).days
        if days_until_due < 0:
            days_until_due += 30  # Next month

        if days_until_due <= 3:
            urgency = "⚠️ Due in {days_until_due} days!"
        elif days_until_due <= 7:
            urgency = "📅 Due on the 1st"
        else:
            urgency = "📋 Upcoming"

        msg = (
            f"🏠 *Rent Reminder*\n\n"
            f"Amount: R{unit.monthly_rent:,.0f}\n"
            f"Due: {unit.payment_day}st of each month\n"
            f"Status: {urgency}\n\n"
            f"Please use your reference when paying:\n"
            f"`{unit.id[:8]}`\n\n"
            f"Thank you! 🙏"
        )

        await evolution.send_text(unit.tenant_whatsapp, msg)
        logger.info(f"📤 Rent reminder sent to {unit.tenant_name}")

    async def send_overdue_reminder(self, db: AsyncSession, unit: RentalUnit, days_overdue: int):
        """Send overdue rent reminder."""
        msgs = {
            3: "Just a friendly reminder that rent is now 3 days overdue. Please arrange payment as soon as possible. 🙏",
            7: "Rent is now 7 days overdue. Please contact your agent urgently to discuss payment arrangements. ⚠️",
            14: "RENT ARREARS — Your rent is 14 days overdue. Legal action may follow if payment is not received within 48 hours. Please contact us immediately.",
        }

        msg_text = msgs.get(days_overdue, f"Rent is {days_overdue} days overdue. Please settle immediately.")
        msg = f"🏠 *Rent Overdue* — R{unit.monthly_rent:,.0f}\n\n{msg_text}"

        await evolution.send_text(unit.tenant_whatsapp, msg)
        logger.info(f"⚠️ Overdue notice ({days_overdue}d) sent to {unit.tenant_name}")

    async def mark_rent_paid(self, db: AsyncSession, unit_id: str):
        """Mark current month's rent as collected."""
        result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
        unit = result.scalar_one_or_none()
        if unit:
            unit.rent_collected_current_month = True
            await db.commit()

            # Thank tenant
            await evolution.send_text(
                unit.tenant_whatsapp,
                f"✅ Rent of R{unit.monthly_rent:,.0f} received! Thank you. 🙏"
            )

    async def log_maintenance(self, db: AsyncSession, unit_id: str, issue: str, urgency: str = "medium"):
        """Log a maintenance request."""
        result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
        unit = result.scalar_one_or_none()
        if not unit:
            return

        requests = json.loads(unit.maintenance_requests or "[]")
        requests.append({
            "date": datetime.utcnow().isoformat(),
            "issue": issue,
            "urgency": urgency,
            "status": "pending",
        })
        unit.maintenance_requests = json.dumps(requests)
        await db.commit()

        # Acknowledge to tenant
        await evolution.send_text(
            unit.tenant_whatsapp,
            f"🔧 *Maintenance Logged*\n\n"
            f"Issue: {issue}\n"
            f"Urgency: {urgency.upper()}\n\n"
            f"Your agent has been notified and will arrange repairs. We'll keep you updated."
        )

    async def get_portfolio_summary(self, db: AsyncSession, agent_id: str) -> Dict[str, Any]:
        """Get rental portfolio summary."""
        result = await db.execute(
            select(RentalUnit).where(RentalUnit.agent_id == agent_id)
        )
        units = result.scalars().all()

        total_rent = sum(u.monthly_rent for u in units)
        collected = sum(u.monthly_rent for u in units if u.rent_collected_current_month)
        outstanding = total_rent - collected

        # Leases expiring in 30 days
        soon = datetime.utcnow() + timedelta(days=30)
        expiring = [u for u in units if u.lease_end and u.lease_end <= soon]

        # Open maintenance
        open_issues = 0
        for u in units:
            reqs = json.loads(u.maintenance_requests or "[]")
            open_issues += sum(1 for r in reqs if r.get("status") == "pending")

        return {
            "total_units": len(units),
            "total_monthly_rent": total_rent,
            "collected": collected,
            "outstanding": outstanding,
            "collection_rate": int(collected / total_rent * 100) if total_rent > 0 else 0,
            "expiring_leases": len(expiring),
            "open_maintenance": open_issues,
            "units": [
                {
                    "id": u.id[:8],
                    "tenant": u.tenant_name,
                    "rent": u.monthly_rent,
                    "paid": u.rent_collected_current_month,
                }
                for u in units
            ],
        }

    async def format_portfolio_message(self, db: AsyncSession, agent_id: str) -> str:
        """Format rental portfolio as WhatsApp message."""
        summary = await self.get_portfolio_summary(db, agent_id)

        if summary["total_units"] == 0:
            return "You don't have any rental units yet. Add one with: 'new tenant: [name] [whatsapp] [rent]'"

        msg = f"🏢 *Rental Portfolio*\n\n"
        msg += f"📊 Units: {summary['total_units']}\n"
        msg += f"💰 Monthly Income: R{summary['total_monthly_rent']:,.0f}\n"
        msg += f"✅ Collected: R{summary['collected']:,.0f} ({summary['collection_rate']}%)\n"
        msg += f"⚠️ Outstanding: R{summary['outstanding']:,.0f}\n\n"

        msg += f"📅 Expiring Leases: {summary['expiring_leases']}\n"
        msg += f"🔧 Open Maintenance: {summary['open_maintenance']}\n\n"

        msg += "*Units:*\n"
        for u in summary["units"]:
            icon = "✅" if u["paid"] else "❌"
            msg += f"{icon} {u['tenant']} — R{u['rent']:,.0f} ({u['id']})\n"

        return msg

    async def process_monthly_tasks(self, db: AsyncSession):
        """End-of-month processing: reset collection flags, send reminders."""
        result = await db.execute(select(RentalUnit))
        units = result.scalars().all()

        for unit in units:
            unit.rent_collected_current_month = False

            # Send reminder 3 days before due date
            await self.send_rent_reminder(db, unit)

        await db.commit()
        logger.info(f"📅 Monthly rental tasks processed for {len(units)} units")


# Singleton
rental_manager = RentalManager()
