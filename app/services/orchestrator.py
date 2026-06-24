"""
Orchestrator — routes classified intents to the correct service handler.
This is the "brain" that connects intent → action → response.
"""
import json
import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.intent import (
    ClassifiedIntent,
    INTENT_PROPERTY_SEARCH,
    INTENT_LISTING_ADD,
    INTENT_VIEWING_REQUEST,
    INTENT_VALUATION_REQUEST,
    INTENT_BOND_QUERY,
    INTENT_DEAL_UPDATE,
    INTENT_PIPELINE_CHECK,
    INTENT_RENTAL_QUERY,
    INTENT_MAINTENANCE,
    INTENT_MARKET_QUERY,
    INTENT_GREETING,
    INTENT_GENERAL_CHAT,
    INTENT_UNKNOWN,
)
from app.ai.responder import responder, GeneratedResponse
from app.services.evolution import evolution
from app.services.search import search
from app.services.listings import listing_service
from app.services.deals import deal_tracker
from app.services.valuation import valuation_service
from app.services.bond import bond_calculator
from app.services.documents import document_service
from app.services.rentals import rental_manager
from app.services.market import market_watch
from app.services.social import social_poster
from app.services.followup import follow_up_manager, trigger_follow_up_on_new_lead

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Routes classified intents to appropriate service handlers.
    Each handler returns a response string that gets sent via WhatsApp.
    """

    async def handle(
        self,
        db: AsyncSession,
        classified: ClassifiedIntent,
        agent_id: str,
        sender_phone: str,
        sender_role: str,
        lead_id: Optional[str] = None,
    ) -> str:
        """
        Main dispatch: route intent to correct handler.
        Returns: response text to send back via WhatsApp.
        """
        intent = classified.intent
        entities = classified.entities
        message = classified.original_message

        logger.info(f"🎯 Orchestrator routing: {intent} (from {sender_role})")

        handlers = {
            INTENT_PROPERTY_SEARCH: self._handle_property_search,
            INTENT_LISTING_ADD: self._handle_listing_add,
            INTENT_VIEWING_REQUEST: self._handle_viewing_request,
            INTENT_VALUATION_REQUEST: self._handle_valuation,
            INTENT_BOND_QUERY: self._handle_bond_query,
            INTENT_DEAL_UPDATE: self._handle_deal_update,
            INTENT_PIPELINE_CHECK: self._handle_pipeline_check,
            INTENT_RENTAL_QUERY: self._handle_rental_query,
            INTENT_MAINTENANCE: self._handle_maintenance,
            INTENT_MARKET_QUERY: self._handle_market_query,
            INTENT_GREETING: self._handle_greeting,
            INTENT_GENERAL_CHAT: self._handle_general_chat,
            INTENT_UNKNOWN: self._handle_unknown,
        }

        handler = handlers.get(intent, self._handle_unknown)

        try:
            response_text = await handler(
                db, classified, agent_id, sender_phone, sender_role, lead_id, message
            )
        except Exception as e:
            logger.error(f"❌ Handler failed for {intent}: {e}", exc_info=True)
            response_text = "Sorry, something went wrong! 😕 Your agent has been notified. They'll get back to you shortly."

        return response_text

    # ── Intent Handlers ────────────────────────────────────

    async def _handle_property_search(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle property search intent."""
        entities = classified.entities

        # Search listings
        results = await search.search(db, agent_id, message, entities, limit=5)

        if results:
            # Format listing cards
            parts = [f"🏠 *Found {len(results)} matching properties:*\n"]
            for i, listing in enumerate(results, 1):
                card = (
                    f"*{i}. {listing.title or 'Property'}*\n"
                    f"📍 {listing.suburb or 'N/A'}\n"
                    f"🛏 {listing.bedrooms or '?'} bed | 🛁 {listing.bathrooms or '?'} bath\n"
                    f"💰 R{listing.price:,.0f}\n"
                )
                if listing.features:
                    feats = json.loads(listing.features)[:3]
                    if feats:
                        card += f"✨ {', '.join(feats)}\n"
                parts.append(card)

            response = "\n" + "─" * 25 + "\n".join(parts)
            response += f"\n{'─' * 25}\n_Reply with the number (1-{len(results)}) to book a viewing or get more details! 📅_"

            # Schedule follow-up for this lead
            if lead_id:
                await trigger_follow_up_on_new_lead(db, lead_id, agent_id, entities)

        else:
            response = (
                f"I searched for matching properties but didn't find any right now. 🔍\n\n"
                f"I've saved your search and will alert you when something comes up!\n\n"
                f"In the meantime, could you share your budget range and preferred areas? "
                f"That helps me find the best match for you. 🏠"
            )

            # Schedule follow-up
            if lead_id:
                await trigger_follow_up_on_new_lead(db, lead_id, agent_id, entities)

        return response

    async def _handle_listing_add(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle adding a new listing."""
        if sender_role != "agent":
            return "This feature is for agents only. I'll let your agent know you're interested in listing a property!"

        entities = classified.entities

        # Check what's missing
        missing = []
        if not entities.get("price"):
            missing.append("price")
        if not entities.get("bedrooms"):
            missing.append("number of bedrooms")
        if not entities.get("suburb") and not entities.get("area"):
            missing.append("area/suburb")

        if missing and sender_role == "agent":
            return (
                f"Almost there! I just need a bit more info:\n"
                f"• {chr(10).join('• ' + m for m in missing)}\n\n"
                f"Reply with the details and I'll add your listing. 📝"
            )

        # Create the listing
        listing = await listing_service.create_from_entities(db, agent_id, entities)

        return (
            f"✅ *Listing Created!*\n\n"
            f"🏠 {listing.title}\n"
            f"📍 {listing.suburb or 'N/A'}\n"
            f"🛏 {listing.bedrooms or '?'} bed | 🛁 {listing.bathrooms or '?'} bath\n"
            f"💰 R{listing.price:,.0f}\n"
            f"🔑 Status: Active\n"
            f"🆔 ID: {listing.id[:8]}\n\n"
            f"Send photos to add them to this listing. 📸\n"
            f"Reply 'post {listing.id[:8]}' to share on social media."
        )

    async def _handle_viewing_request(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle viewing request."""
        # Load agent info
        from app.services.database import Agent
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()

        agent_name = agent.display_name if agent else "your agent"

        return (
            f"📅 *Viewing Request Received!*\n\n"
            f"I've let {agent_name} know you want to view this property.\n\n"
            f"To help book the perfect time, what day works best for you?\n"
            f"• Weekday morning\n"
            f"• Weekday afternoon\n"
            f"• Saturday\n"
            f"• Sunday\n\n"
            f"Your agent will confirm the exact time. 🕐"
        )

    async def _handle_valuation(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle valuation request."""
        entities = classified.entities

        # Check if we have enough info
        if not entities.get("suburb") and not entities.get("area"):
            return (
                "To give you an accurate valuation, I need to know the area. 📍\n\n"
                "Reply with: area, bedrooms, bathrooms, and floor size (if you know it).\n"
                "Example: '3 bed Diepkloof Zone 4, 120sqm'"
            )

        valuation = valuation_service.estimate_value(entities)
        return valuation_service.format_valuation_message(valuation)

    async def _handle_bond_query(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle bond / affordability query."""
        entities = classified.entities

        # If we have income, calculate
        income = entities.get("monthly_income")
        if not income:
            return (
                "Let me help you figure out what you can afford! 🏦\n\n"
                "I just need a few details:\n"
                "• Your gross monthly income (before deductions)\n"
                "• Any existing monthly loan payments\n"
                "• The property price you're looking at (if you have one in mind)\n\n"
                "Reply with your info and I'll crunch the numbers! 📊"
            )

        existing_debt = entities.get("monthly_debt_payments", 0)
        property_price = entities.get("property_price")

        if property_price and property_price > 0:
            result = bond_calculator.calculate_for_property(income, property_price, existing_debt)
        else:
            result = bond_calculator.calculate(income, existing_debt)

        return bond_calculator.format_bond_message(result, property_price)

    async def _handle_deal_update(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle deal stage update."""
        entities = classified.entities

        new_stage = entities.get("new_stage", "")
        amount = entities.get("amount")

        # Try to find the deal
        deal_ref = entities.get("deal_reference", "")
        if not deal_ref:
            return "Which deal are you updating? Reply with 'update deal [ID or number]'"

        from app.services.database import Deal
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(Deal).where(Deal.id.like(f"{deal_ref}%"))
        )
        deal = result.scalar_one_or_none()

        if not deal:
            return f"Deal '{deal_ref}' not found. Check the ID and try again."

        # Update the deal
        if new_stage:
            deal = await deal_tracker.update_stage(db, deal.id, new_stage)

        if amount and deal:
            deal.deal_value = amount
            await db.commit()

        stage_emoji = {"lead": "🔍", "viewing": "👁️", "offer": "💰", "negotiation": "🤝",
                       "accepted": "✅", "bond_pending": "🏦", "closed": "🎉", "lost": "❌"}

        response = f"{stage_emoji.get(deal.deal_stage if deal else '', '📋')} *Deal Updated!*\n\n"
        if deal:
            response += f"Deal: {deal.id[:8]}\n"
            response += f"Stage: {deal.deal_stage.upper()}\n"
            response += f"Value: R{deal.deal_value:,.0f}\n" if deal.deal_value else ""

        # Special handling for accepted → prompt next steps
        if new_stage == "accepted":
            response += "\n🎉 Congratulations! Next steps:\n"
            response += "• Collect buyer & seller FICA docs\n"
            response += "• Sign OTP (Offer to Purchase)\n"
            response += "• Submit bond application\n"
            response += "\nReply 'docs [deal_id]' to start document collection."

        return response

    async def _handle_pipeline_check(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle pipeline status check."""
        if sender_role != "agent":
            return "Your agent is tracking all deals. They'll update you on the status of your offer!"

        return await deal_tracker.format_pipeline_message(db, agent_id)

    async def _handle_rental_query(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle rental-related queries."""
        if sender_role != "agent":
            return (
                "I can help with rental queries! 🏢\n\n"
                "Are you looking to rent a property, or do you have a question about your current rental?"
            )

        # Agent checking their portfolio
        return await rental_manager.format_portfolio_message(db, agent_id)

    async def _handle_maintenance(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle maintenance request."""
        entities = classified.entities

        issue = entities.get("issue_description", message)
        urgency = entities.get("urgency", "medium")
        unit_ref = entities.get("unit_reference", "")

        if unit_ref:
            # Try to find the unit
            from app.services.database import RentalUnit
            from sqlalchemy import select as sa_select
            result = await db.execute(
                sa_select(RentalUnit).where(
                    RentalUnit.agent_id == agent_id,
                    RentalUnit.id.like(f"{unit_ref}%")
                )
            )
            unit = result.scalar_one_or_none()
            if unit:
                await rental_manager.log_maintenance(db, unit.id, issue, urgency)

        return (
            f"🔧 *Maintenance Logged*\n\n"
            f"Issue: {issue[:200]}\n"
            f"Urgency: {urgency.upper()}\n\n"
            f"✅ Your agent has been notified. Someone will contact you within 24 hours.\n"
            f"Reference: {unit_ref or 'logged'}"
        )

    async def _handle_market_query(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle market intelligence query."""
        entities = classified.entities
        area = entities.get("area", "")

        if area:
            summary = await market_watch.get_area_summary(area)
            if "status" in summary:
                return summary["status"]

            trend = {"up": "📈 Rising", "stable": "📊 Stable", "down": "📉 Declining"}
            return (
                f"📊 *{area.title()} Market Snapshot*\n\n"
                f"💰 Avg House: R{summary['avg_house_price']:,}\n"
                f"📐 Per sqm: R{summary['avg_price_per_sqm']:,}\n"
                f"📈 Trend: {trend.get(summary['market_trend'], summary['market_trend'])}\n\n"
                f"_For a full weekly report, reply 'weekly report'_"
            )

        # General market query — show hot areas
        hot = await market_watch.get_hot_areas()
        msg = "🔥 *Hot Areas — Johannesburg Townships*\n\n"
        for area in hot:
            trend_icon = {"up": "📈", "stable": "📊", "down": "📉"}.get(area["trend"], "")
            msg += f"{trend_icon} *{area['area']}* — Avg R{area['avg']:,}\n"

        msg += "\nReply with a specific area for detailed stats. 📊"
        return msg

    async def _handle_greeting(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle greetings."""
        if sender_role == "agent":
            return (
                "Hello! 👋 Ready to work?\n\n"
                "Here's what I can do for you today:\n"
                "🏠 'listings' — View your properties\n"
                "📊 'pipeline' — Check your deals\n"
                "🔍 'add listing' — Add new property\n"
                "📈 'valuation' — Get property value\n"
                "🏢 'rentals' — Manage tenants\n"
                "📱 'post [id]' — Share on social media\n\n"
                "What would you like to do?"
            )

        return (
            "Hello! 👋 I'm iGosa, your property assistant.\n\n"
            "I can help you:\n"
            "🏠 *Find properties* — Just tell me what you're looking for\n"
            "💰 *Check affordability* — See what bond you qualify for\n"
            "📊 *Get valuations* — Know what a property is worth\n"
            "📅 *Book viewings* — Pick a time that works\n\n"
            "What can I help you with today?"
        )

    async def _handle_general_chat(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle casual conversation."""
        return (
            "I'm here to help with all things property! 🏠\n\n"
            "Whether you're buying, selling, renting, or just curious about the market — ask away!\n\n"
            "Try saying:\n"
            "• '2 bed Soweto under R500K'\n"
            "• 'Can I afford R400K?'\n"
            "• 'What's my pipeline?'\n"
            "• 'Value my house in Pimville'"
        )

    async def _handle_unknown(
        self, db, classified, agent_id, sender_phone, sender_role, lead_id, message
    ) -> str:
        """Handle unknown intents."""
        return (
            "I'm not quite sure what you need. 🤔\n\n"
            "Here are things I can help with:\n"
            "🏠 *Find property* — '2 bed Pimville under R400K'\n"
            "💰 *Affordability* — 'Can I afford R500K?'\n"
            "📊 *Valuation* — 'Value my house in Soweto'\n"
            "📋 *Pipeline* — 'Show my pipeline'\n"
            "🔧 *Maintenance* — 'Geyser leaking unit 3'\n\n"
            "Try rephrasing, or just tell me what you need!"
        )


# Singleton
orchestrator = Orchestrator()
