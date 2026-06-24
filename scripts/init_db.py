"""
Script: Initialize the database and create a demo agent.
Run: python scripts/init_db.py
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.database import init_db, AsyncSessionLocal, Agent
from sqlalchemy import select


async def main():
    """Initialize database and optionally create a demo agent."""
    print("🗄️  Initializing database...")
    await init_db()
    print("✅ Database tables created!")

    # Check if any agents exist
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Agent).limit(1))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"📋 Agent already exists: {existing.display_name} ({existing.whatsapp_number})")
            return

        # ── Create demo agent ──────────────────────
        import json

        demo_agent = Agent(
            whatsapp_number="27820000000",  # Replace with your WhatsApp number
            display_name="Demo Agent",
            business_name="iGosa Test Properties",
            areas=json.dumps(["Soweto", "Pimville", "Diepkloof"]),
            property_types=json.dumps(["house", "apartment", "rdp"]),
            price_range_min=150000,
            price_range_max=1500000,
            subscription_tier="pro",
            subscription_status="active",
            is_active=True,
        )
        session.add(demo_agent)
        await session.commit()
        print(f"✅ Created demo agent: {demo_agent.display_name}")
        print(f"   WhatsApp: {demo_agent.whatsapp_number}")
        print(f"   ⚠️  Update the WhatsApp number in the database before using!")


if __name__ == "__main__":
    asyncio.run(main())
