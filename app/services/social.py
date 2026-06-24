"""
Social Poster — Facebook auto-posting for property listings.
Generates optimized posts and posts to configured Facebook groups.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


POST_TEMPLATES = {
    "urgency": "🔥 *JUST LISTED!* {title} — {suburb}\n\n{description}\n\n💰 R{price:,.0f}\n🛏 {bedrooms} bed | 🛁 {bathrooms} bath\n📍 {suburb}\n\nThis won't last! DM or WhatsApp for viewing.\n\n#PropertyForSale #{suburb_hashtag} #JohannesburgProperty",
    
    "feature": "🏠 *{title}*\n\n{description}\n\n✨ Features: {features}\n💰 Price: R{price:,.0f}\n🛏 {bedrooms} bed | 🛁 {bathrooms} bath\n📍 {suburb}\n\nMove-in ready! Contact for viewing.\n\n#{suburb_hashtag} #HouseForSale #Joburg",
    
    "community": "🗝️ Your new home awaits in {suburb}!\n\n{title}\n{description}\n\n💰 R{price:,.0f} | 🛏 {bedrooms} bed | 🛁 {bathrooms} bath\n\nContact me for a viewing! 📲\n\n#{suburb_hashtag} #NewListing #PropertySA",
}


class SocialPoster:
    """Generates and manages social media posts for listings."""

    def generate_posts(self, listing_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate 3 post variations for a listing."""
        suburb = listing_data.get("suburb", "Johannesburg")
        suburb_hashtag = suburb.replace(" ", "").replace("-", "")
        features = listing_data.get("features", "")
        if isinstance(features, list):
            features = ", ".join(features[:4])

        data = {
            **listing_data,
            "suburb_hashtag": suburb_hashtag,
            "features": features or "Contact for details",
        }

        variations = []
        for style, template in POST_TEMPLATES.items():
            try:
                text = template.format(**data)
                variations.append({
                    "style": style,
                    "text": text,
                    "best_time": {"urgency": "07:00", "feature": "12:00", "community": "18:00"}[style],
                })
            except KeyError as e:
                logger.warning(f"Missing key in template: {e}")

        return variations

    async def format_for_review(self, listing_data: Dict[str, Any]) -> str:
        """Format posts for agent review via WhatsApp."""
        posts = self.generate_posts(listing_data)
        
        msg = f"📱 *Post Preview — {listing_data.get('title', 'Listing')[:40]}*\n\n"
        msg += "_Reply with the number to post, or 'all' to post all._\n\n"
        
        for i, post in enumerate(posts, 1):
            msg += f"*Option {i}* ({post['style']}) — Best at {post['best_time']}\n"
            msg += f"```{post['text'][:300]}```\n\n"

        return msg

    async def schedule_posts(
        self, db: "AsyncSession", agent_id: str, listing_id: str, selected: List[int] = None
    ):
        """Schedule posts for publishing. selected=None means all variations."""
        # Stub — requires Facebook Graph API integration
        # In production, this would queue posts via Facebook API
        logger.info(f"📱 Scheduled posts for listing {listing_id}, variations: {selected or 'all'}")
        return {"scheduled": len(selected) if selected else 3, "status": "pending"}


# Singleton
social_poster = SocialPoster()
