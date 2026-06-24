"""
Valuation Service — property valuation and comparable sales analysis.
"""
import json
import logging
from typing import Dict, Any, List, Optional


from app.config import settings

logger = logging.getLogger(__name__)


# ── Area Price Benchmarks (Johannesburg townships, 2026 estimates) ──

AREA_BENCHMARKS = {
    "soweto": {"avg_price_per_sqm": 3500, "avg_house": 420000, "trend": "up"},
    "pimville": {"avg_price_per_sqm": 4000, "avg_house": 450000, "trend": "up"},
    "diepkloof": {"avg_price_per_sqm": 3800, "avg_house": 430000, "trend": "stable"},
    "meadowlands": {"avg_price_per_sqm": 3200, "avg_house": 380000, "trend": "stable"},
    "orlando": {"avg_price_per_sqm": 3400, "avg_house": 400000, "trend": "up"},
    "protea glen": {"avg_price_per_sqm": 4200, "avg_house": 520000, "trend": "up"},
    "alexandra": {"avg_price_per_sqm": 2800, "avg_house": 350000, "trend": "up"},
    "tembisa": {"avg_price_per_sqm": 2200, "avg_house": 320000, "trend": "stable"},
    "katlehong": {"avg_price_per_sqm": 2000, "avg_house": 300000, "trend": "stable"},
    "vosloorus": {"avg_price_per_sqm": 2100, "avg_house": 310000, "trend": "stable"},
    "lenasia": {"avg_price_per_sqm": 4500, "avg_house": 550000, "trend": "up"},
    "eldorado park": {"avg_price_per_sqm": 1800, "avg_house": 250000, "trend": "stable"},
    "cosmo city": {"avg_price_per_sqm": 3500, "avg_house": 420000, "trend": "up"},
    "diepsloot": {"avg_price_per_sqm": 1500, "avg_house": 200000, "trend": "up"},
    "midrand": {"avg_price_per_sqm": 5000, "avg_house": 750000, "trend": "up"},
    "hillbrow": {"avg_price_per_sqm": 2000, "avg_house": 280000, "trend": "stable"},
    "johannesburg": {"avg_price_per_sqm": 3500, "avg_house": 450000, "trend": "up"},
}


class ValuationService:
    """Provides property valuations and comparable analysis."""

    def estimate_value(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate property value based on area benchmarks and features."""
        area = (entities.get("suburb") or entities.get("area") or "").lower().strip()
        bedrooms = entities.get("bedrooms", 3)
        bathrooms = entities.get("bathrooms", 1)
        floor_area = entities.get("floor_area_sqm")
        features = entities.get("features", [])
        property_type = entities.get("property_type", "house")

        # Find area benchmark
        benchmark = None
        for key, data in AREA_BENCHMARKS.items():
            if key in area or area in key:
                benchmark = data
                break

        if not benchmark:
            # Use Johannesburg average
            benchmark = AREA_BENCHMARKS["johannesburg"]

        # Base estimate
        if floor_area:
            base_value = floor_area * benchmark["avg_price_per_sqm"]
        else:
            base_value = benchmark["avg_house"]

        # Adjust for bedrooms
        base_value += (bedrooms - 3) * 50000

        # Adjust for bathrooms
        if bathrooms and bathrooms > 1:
            base_value += (bathrooms - 1) * 30000

        # Adjust for features
        feature_multiplier = 1.0
        premium_features = ["garage", "pool", "garden", "renovated", "security", "modern kitchen"]
        for f in features:
            if f.lower() in premium_features:
                feature_multiplier += 0.05

        base_value *= feature_multiplier

        # RDP discount
        if property_type == "rdp":
            base_value = min(base_value, 350000)  # RDP resale cap

        low = int(base_value * 0.85)
        high = int(base_value * 1.15)
        mid = int(base_value)

        return {
            "estimated_value": mid,
            "range_low": low,
            "range_high": high,
            "area": area.title(),
            "avg_price_per_sqm": benchmark["avg_price_per_sqm"],
            "market_trend": benchmark["trend"],
            "based_on": "area benchmark",
            "confidence": "medium",
        }

    def format_valuation_message(self, valuation: Dict[str, Any]) -> str:
        """Format valuation as WhatsApp message."""
        trend_emoji = {"up": "📈", "stable": "📊", "down": "📉"}.get(valuation["market_trend"], "📊")

        msg = (
            f"📊 *Property Valuation*\n\n"
            f"📍 *Area:* {valuation['area']}\n"
            f"💰 *Estimated Value:* R{valuation['estimated_value']:,}\n"
            f"📏 *Range:* R{valuation['range_low']:,} – R{valuation['range_high']:,}\n"
            f"📐 *Avg Price/sqm:* R{valuation['avg_price_per_sqm']:,}\n"
            f"{trend_emoji} *Market Trend:* {valuation['market_trend'].upper()}\n\n"
            f"⚠️ *Confidence:* {valuation['confidence'].upper()}\n"
            f"_This is an automated estimate based on area benchmarks. For a formal valuation, consult a professional appraiser._"
        )
        return msg


# Singleton
valuation_service = ValuationService()
