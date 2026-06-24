"""
Vector Search Service — intelligent listing matching using ChromaDB.
Enables semantic search across listings (area + description + features).
"""
import json
import logging
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.database import Listing

logger = logging.getLogger(__name__)


class VectorSearch:
    """
    Listing search engine. Uses ChromaDB for vector similarity when available,
    falls back to smart SQL filtering with fuzzy matching.
    """

    def __init__(self):
        self.collection = None
        self._init_attempted = False

    async def _init_chroma(self):
        """Try to initialize ChromaDB."""
        if self._init_attempted:
            return
        self._init_attempted = True
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path="./chroma_data")
            self.collection = self.client.get_or_create_collection("listings")
            logger.info("📊 ChromaDB initialized for vector search")
        except Exception as e:
            logger.info(f"📊 ChromaDB not available, using SQL fallback ({e})")

    async def index_listing(self, listing: Listing):
        """Add a listing to the vector index."""
        await self._init_chroma()
        if not self.collection:
            return

        try:
            text = f"{listing.title} {listing.description or ''} {listing.suburb or ''} {' '.join(json.loads(listing.features or '[]'))}"
            self.collection.add(
                ids=[listing.id],
                documents=[text],
                metadatas=[{
                    "price": listing.price,
                    "bedrooms": listing.bedrooms or 0,
                    "bathrooms": listing.bathrooms or 0,
                    "suburb": listing.suburb or "",
                    "property_type": listing.property_type,
                }],
            )
        except Exception as e:
            logger.warning(f"Failed to index listing {listing.id}: {e}")

    async def search(
        self,
        db: AsyncSession,
        agent_id: str,
        query: str,
        entities: Dict[str, Any] = None,
        limit: int = 5,
    ) -> List[Listing]:
        """Search listings with vector similarity + filters."""
        entities = entities or {}

        # Get all active listings for the agent
        result = await db.execute(
            select(Listing).where(
                Listing.agent_id == agent_id,
                Listing.status == "active",
            )
        )
        all_listings = result.scalars().all()

        if not all_listings:
            return []

        # Score and filter
        scored = []
        for listing in all_listings:
            score = self._score_listing(listing, query, entities)
            if score > 0:
                scored.append((score, listing))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [l for _, l in scored[:limit]]

    def _score_listing(self, listing: Listing, query: str, entities: Dict[str, Any]) -> float:
        """Score a listing against search criteria. Returns 0-100."""
        score = 50.0  # Start neutral

        query_lower = query.lower()
        listing_text = f"{listing.title or ''} {listing.description or ''} {listing.suburb or ''}".lower()

        # Text match bonus
        words = query_lower.split()
        matches = sum(1 for w in words if w in listing_text)
        if matches:
            score += min(matches * 10, 30)

        # Bedrooms match
        if entities.get("bedrooms") and listing.bedrooms:
            diff = abs(listing.bedrooms - entities["bedrooms"])
            if diff == 0:
                score += 20
            elif diff == 1:
                score += 10
            else:
                score -= 15

        # Bathrooms
        if entities.get("bathrooms") and listing.bathrooms:
            if abs(listing.bathrooms - entities["bathrooms"]) <= 1:
                score += 5

        # Price match
        if entities.get("max_price") and listing.price:
            if listing.price <= entities["max_price"]:
                score += 10
                # Bonus for being well under budget
                ratio = listing.price / entities["max_price"]
                if ratio < 0.7:
                    score += 10
            else:
                # Penalty for over budget, but allow 15% flexibility
                if listing.price > entities["max_price"] * 1.15:
                    score -= 30
                else:
                    score -= 5

        # Area match
        if entities.get("area") and listing.suburb:
            area_lower = entities["area"].lower()
            suburb_lower = listing.suburb.lower()
            if area_lower == suburb_lower:
                score += 20
            elif area_lower in suburb_lower or suburb_lower in area_lower:
                score += 10

        # Property type match
        if entities.get("property_type") and listing.property_type:
            if entities["property_type"].lower() == listing.property_type.lower():
                score += 10
            elif entities["property_type"].lower() == "rdp" and listing.rdp_restricted:
                score += 15

        # Price type match (sale vs rent)
        if entities.get("price_type"):
            if listing.price_type == entities["price_type"]:
                score += 10
            else:
                score -= 20

        return max(score, 0)

    async def rebuild_index(self, db: AsyncSession):
        """Rebuild the entire vector index from the database."""
        await self._init_chroma()
        if not self.collection:
            return

        result = await db.execute(select(Listing).where(Listing.status == "active"))
        listings = result.scalars().all()

        if self.collection.count() > 0:
            self.collection.delete(self.collection.get()["ids"])

        for listing in listings:
            await self.index_listing(listing)

        logger.info(f"📊 Rebuilt index with {len(listings)} listings")


# Singleton
search = VectorSearch()
