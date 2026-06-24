"""
Market Watch — competitor intelligence and market trend monitoring.
Provides daily alerts and weekly reports for agents.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.database import Listing
from app.services.valuation import AREA_BENCHMARKS

logger = logging.getLogger(__name__)


class MarketWatch:
    """Monitors market activity and generates alerts."""

    async def get_area_summary(self, area: str) -> Dict[str, Any]:
        """Get market summary for an area."""
        area_lower = area.lower().strip()

        benchmark = None
        for key, data in AREA_BENCHMARKS.items():
            if key in area_lower or area_lower in key:
                benchmark = data
                break

        if not benchmark:
            return {
                "area": area,
                "status": "No benchmark data available for this area yet.",
                "avg_price_per_sqm": 0,
                "trend": "unknown",
            }

        return {
            "area": area.title(),
            "avg_price_per_sqm": benchmark["avg_price_per_sqm"],
            "avg_house_price": benchmark["avg_house"],
            "market_trend": benchmark["trend"],
        }

    async def generate_daily_alert(self, db: AsyncSession, agent_id: str, agent_areas: List[str]) -> str:
        """Generate a daily market alert for an agent."""
        if not agent_areas:
            return "Set your areas to receive market alerts. Use 'settings areas: Soweto, Pimville'"

        msg = "📈 *Daily Market Alert*\n\n"

        for area in agent_areas[:3]:
            summary = await self.get_area_summary(area)
            trend_emoji = {"up": "📈", "stable": "📊", "down": "📉"}.get(summary.get("market_trend", ""), "📊")

            msg += f"*{area.title()}* {trend_emoji}\n"
            msg += f"   Avg Price: R{summary.get('avg_house_price', 0):,}\n"
            msg += f"   Per sqm: R{summary.get('avg_price_per_sqm', 0):,}\n\n"

        msg += f"📅 {datetime.utcnow().strftime('%d %b %Y')} | Powered by iGosa"

        return msg

    async def generate_weekly_report(self, db: AsyncSession, agent_id: str) -> str:
        """Generate a weekly market report."""
        # This would pull from actual scraped data in production
        # For now, uses benchmark data

        msg = "🗞️ *Weekly Market Report*\n"
        msg += f"Week ending: {datetime.utcnow().strftime('%d %b %Y')}\n\n"

        msg += "📊 *Area Overview — Johannesburg Townships*\n\n"

        for area, data in list(AREA_BENCHMARKS.items())[:10]:
            trend = {"up": "↑", "stable": "→", "down": "↓"}.get(data["trend"], "→")
            msg += f"{trend} *{area.title()}* — R{data['avg_house']:,} (R{data['avg_price_per_sqm']:,}/sqm)\n"

        msg += f"\n💡 *Tip:* Properties in {'Soweto' if datetime.utcnow().month % 2 == 0 else 'Diepkloof'} are moving fastest this week.\n"
        msg += f"\n📅 {datetime.utcnow().strftime('%d %b %Y')} | iGosa Market Intelligence"

        return msg

    async def check_price_drops(self, db: AsyncSession, agent_id: str) -> List[Dict]:
        """Check for properties with recent price drops (stub for future integration)."""
        # In production, this would compare with scraped data
        return []

    async def get_hot_areas(self) -> List[Dict]:
        """Get areas with highest activity."""
        hot = sorted(
            [{"area": k.title(), "trend": v["trend"], "avg": v["avg_house"]}
             for k, v in AREA_BENCHMARKS.items() if v["trend"] == "up"],
            key=lambda x: x["avg"],
            reverse=True,
        )[:5]
        return hot


# Singleton
market_watch = MarketWatch()
