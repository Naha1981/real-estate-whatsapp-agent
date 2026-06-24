"""
Listing Service — WhatsApp-based listing CRUD.
Agents manage their property inventory entirely via WhatsApp.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.database import Listing
from app.services.search import search

logger = logging.getLogger(__name__)


class ListingService:
    """Manage property listings via WhatsApp commands."""

    async def create_from_entities(
        self, db: AsyncSession, agent_id: str, entities: Dict[str, Any]
    ) -> Listing:
        """Create a listing from extracted entities."""
        listing = Listing(
            agent_id=agent_id,
            title=entities.get("title", "New Listing"),
            description=entities.get("description"),
            bedrooms=entities.get("bedrooms"),
            bathrooms=entities.get("bathrooms"),
            price=entities.get("price", 0),
            price_type=entities.get("price_type", "sale"),
            property_type=entities.get("property_type", "house"),
            suburb=entities.get("suburb") or entities.get("area"),
            address=entities.get("address"),
            floor_area_sqm=entities.get("floor_area_sqm"),
            erf_size_sqm=entities.get("erf_size_sqm"),
            features=json.dumps(entities.get("features", [])),
            status="active",
        )

        # Auto-detect RDP
        if "rdp" in str(entities.get("property_type", "")).lower():
            listing.rdp_restricted = True

        db.add(listing)
        await db.commit()
        await db.refresh(listing)

        # Index for search
        await search.index_listing(listing)

        logger.info(f"🏠 Listing created: {listing.id[:8]} — {listing.title}")
        return listing

    async def add_photos(self, db: AsyncSession, listing_id: str, photo_urls: List[str]):
        """Add photo URLs to a listing."""
        result = await db.execute(select(Listing).where(Listing.id == listing_id))
        listing = result.scalar_one_or_none()
        if not listing:
            return

        existing = json.loads(listing.photos or "[]")
        existing.extend(photo_urls)
        listing.photos = json.dumps(existing)
        listing.updated_at = datetime.utcnow()
        await db.commit()

    async def update_status(
        self, db: AsyncSession, listing_id: str, status: str
    ) -> Optional[Listing]:
        """Update listing status (active/under_offer/sold/rented/archived)."""
        result = await db.execute(select(Listing).where(Listing.id == listing_id))
        listing = result.scalar_one_or_none()
        if not listing:
            return None
        listing.status = status
        listing.updated_at = datetime.utcnow()
        await db.commit()
        return listing

    async def get_by_id(self, db: AsyncSession, listing_id: str) -> Optional[Listing]:
        result = await db.execute(select(Listing).where(Listing.id == listing_id))
        return result.scalar_one_or_none()

    async def list_for_agent(
        self, db: AsyncSession, agent_id: str, status: str = "active", limit: int = 20
    ) -> List[Listing]:
        """Get all listings for an agent."""
        query = select(Listing).where(Listing.agent_id == agent_id)
        if status:
            query = query.where(Listing.status == status)
        query = query.order_by(Listing.updated_at.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def format_listings_message(
        self, db: AsyncSession, agent_id: str, status: str = "active"
    ) -> str:
        """Format agent's listings as WhatsApp message."""
        listings = await self.list_for_agent(db, agent_id, status, limit=10)

        if not listings:
            return f"No {status} listings found. Send 'add listing: [details]' to create one!"

        active_count = sum(1 for l in listings if l.status == "active")
        uo_count = sum(1 for l in listings if l.status == "under_offer")

        msg = f"📋 *Your {status.upper()} Listings* ({len(listings)})\n"
        if active_count:
            msg += f"   🟢 Active: {active_count}\n"
        if uo_count:
            msg += f"   🟡 Under Offer: {uo_count}\n"
        msg += "\n"

        for l in listings[:8]:
            status_icon = {"active": "🟢", "under_offer": "🟡", "sold": "🔴", "rented": "🔵"}.get(l.status, "⚪")
            msg += (
                f"{status_icon} *{l.title[:40]}*\n"
                f"   📍 {l.suburb or 'N/A'} | 🛏 {l.bedrooms or '?'} bed | 💰 R{l.price:,.0f}\n"
                f"   ID: {l.id[:8]}\n\n"
            )

        if len(listings) > 8:
            msg += f"... and {len(listings) - 8} more"

        return msg

    async def get_stats(self, db: AsyncSession, agent_id: str) -> Dict[str, Any]:
        """Get listing statistics for an agent."""
        from sqlalchemy import func

        result = await db.execute(
            select(
                func.count(),
                func.sum(Listing.status == "active"),
                func.sum(Listing.status == "under_offer"),
                func.sum(Listing.status == "sold"),
                func.avg(Listing.price).filter(Listing.status == "active"),
            ).where(Listing.agent_id == agent_id)
        )
        total, active, uo, sold, avg_price = result.one()
        return {
            "total": total or 0,
            "active": active or 0,
            "under_offer": uo or 0,
            "sold": sold or 0,
            "avg_price": float(avg_price) if avg_price else 0,
        }


# Singleton
listing_service = ListingService()
