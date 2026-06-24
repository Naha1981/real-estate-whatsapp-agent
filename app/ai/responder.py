"""
Smart Responder — generates contextually appropriate WhatsApp responses
based on classified intent and extracted entities.

Handles code-switching and SA township real estate context.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass



from app.config import settings
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

logger = logging.getLogger(__name__)


RESPONDER_SYSTEM_PROMPT = """You are iGosa, a friendly WhatsApp AI assistant for South African estate agents.

Your personality:
- Warm, professional, efficient
- Use conversational South African English (mix in occasional Zulu/Sotho greetings naturally)
- Keep messages concise — this is WhatsApp, not email
- Use emojis sparingly but naturally 🏠🔑📍
- Be helpful, never pushy

Context you know:
- You help estate agents manage listings, leads, deals, rentals, and documents
- You assist property buyers finding homes in Johannesburg townships and suburbs
- Areas: Soweto, Pimville, Diepkloof, Meadowlands, Orlando, Alexandra, Tembisa, Katlehong, Lenasia, etc.
- You understand RDP houses, FLISP subsidies, bond (mortgage) applications
- Prices in South African Rand (R)

Response guidelines:
- If offering property listings: include key details (beds, baths, price, area)
- If the user asks something you can't do yet: be honest, offer to connect them with their agent
- If greeting: respond warmly, remind them what you can help with
- Never make up property listings or prices
- If unsure: ask a clarifying question

Keep responses under 300 characters unless showing multiple listings."""


@dataclass
class GeneratedResponse:
    """Response from the AI responder."""
    text: str
    should_send_media: bool = False
    media_urls: List[str] = None
    handoff_to_human: bool = False
    handoff_reason: str = ""

    def __post_init__(self):
        if self.media_urls is None:
            self.media_urls = []


class SmartResponder:
    """Generates WhatsApp responses based on intent and context."""

    def __init__(self):
        self.client = None  # AsyncOpenAI (lazy-loaded)
        self.model = settings.openai_model

    async def respond(
        self,
        classified: ClassifiedIntent,
        context: Dict[str, Any] = None,
    ) -> GeneratedResponse:
        """
        Generate an appropriate response for the classified intent.
        
        Args:
            classified: The classified intent with entities
            context: Additional context (agent info, listing results, etc.)
        """
        if not self.client:
            return self._fallback_response(classified)

        return await self._ai_response(classified, context or {})

    async def _ai_response(
        self, classified: ClassifiedIntent, context: Dict[str, Any]
    ) -> GeneratedResponse:
        """Generate response using LLM."""
        intent = classified.intent
        entities = classified.entities
        message = classified.original_message

        # Build a focused prompt based on intent
        scenario = self._build_scenario(intent, entities, context, message)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": RESPONDER_SYSTEM_PROMPT},
                    {"role": "user", "content": scenario},
                ],
                temperature=0.7,  # Warmer for natural conversation
                max_tokens=500,
            )
            text = response.choices[0].message.content.strip()
            return GeneratedResponse(text=text)

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return self._fallback_response(classified)

    def _build_scenario(
        self, intent: str, entities: Dict[str, Any], context: Dict[str, Any], message: str
    ) -> str:
        """Build a prompt scenario for the LLM based on intent."""
        entity_str = json.dumps(entities, indent=2)
        context_str = json.dumps(context, indent=2) if context else "{}"

        base = f"User message: \"{message}\"\nIntent: {intent}\nExtracted entities: {entity_str}"

        handlers = {
            INTENT_PROPERTY_SEARCH: f"""
{base}
Additional context (matching listings): {context_str}

The user is looking for property. 
- If context has matching_listings with properties, present up to 3 of them as numbered options with key details
- If no matching listings, let them know and ask if they want to save the search
- Ask qualifying questions if info is missing (budget, area preference)""",

            INTENT_GREETING: f"""
{base}

The user is greeting you. Respond warmly in SA style. Briefly remind them you can help with:
- Finding properties
- Property valuations
- Bond affordability checks
- Viewing bookings
- And more — just ask!""",

            INTENT_VALUATION_REQUEST: f"""
{base}

The user wants a property valuation. Acknowledge the request. 
Ask for any missing details (bedrooms, bathrooms, area, floor size in sqm, special features).
Let them know you'll prepare a valuation report.""",

            INTENT_BOND_QUERY: f"""
{base}
Additional context: {context_str}

The user is asking about bond/mortgage affordability.
If they gave income info, calculate rough affordability (monthly income × 30% for repayment).
Mention FLISP subsidy if their income is under R22,000/month.
Offer to connect with a bond originator.""",

            INTENT_LISTING_ADD: f"""
{base}

The user wants to add a new property listing. Acknowledge and confirm the details you extracted.
Ask for anything missing: bedrooms, bathrooms, price, area, photos, property type, features.""",

            INTENT_VIEWING_REQUEST: f"""
{base}
Additional context: {context_str}

The user wants to view a property. Confirm which property they want to see.
Ask for preferred day/time. Let them know you'll check with the agent.""",

            INTENT_DEAL_UPDATE: f"""
{base}

The user is updating a deal. Acknowledge the update.
If the deal stage is "accepted" — congratulate! Ask about next steps (bond, transfer).
If other stage — confirm and offer next actions.""",

            INTENT_PIPELINE_CHECK: f"""
{base}
Additional context (pipeline data): {context_str}

The user wants to see their deal pipeline. If context has pipeline data, summarize it clearly.
If no data available, let them know.""",

            INTENT_RENTAL_QUERY: f"""
{base}
Additional context: {context_str}

Rental-related query. Respond helpfully based on context.
If they're asking about rent payments, provide status if available.
If general rental questions, answer or escalate.""",

            INTENT_MAINTENANCE: f"""
{base}

Maintenance issue reported. Acknowledge the issue empathetically.
Confirm the unit/property and issue details.
Let them know you've logged it and the agent/landlord will arrange repairs.""",

            INTENT_MARKET_QUERY: f"""
{base}

Market intelligence query. If you have market data in context, share it.
Otherwise, let them know you'll compile a report and send it shortly.""",

            INTENT_UNKNOWN: f"""
{base}

Intent unclear. Apologize politely, ask them to rephrase or be more specific.
Offer examples of what you can help with.""",

            INTENT_GENERAL_CHAT: f"""
{base}

Casual conversation. Be friendly, conversational, and helpful.
If they ask something you can help with (real estate related), steer toward that.
Otherwise, chat naturally.""",
        }

        return handlers.get(intent, handlers[INTENT_UNKNOWN])

    def _fallback_response(self, classified: ClassifiedIntent) -> GeneratedResponse:
        """Rule-based fallback responses when LLM is unavailable."""
        intent = classified.intent
        entities = classified.entities

        responses = {
            INTENT_GREETING: "Hello! 👋 I'm iGosa, your property assistant. I can help you find properties, check bond affordability, book viewings, and more. What can I help you with today?",
            
            INTENT_PROPERTY_SEARCH: self._fallback_search_response(entities),
            
            INTENT_VALUATION_REQUEST: "I can help with a property valuation! 📊 To give you an accurate estimate, I'll need: number of bedrooms & bathrooms, the area/suburb, floor size (sqm), and any special features. Can you share those details?",
            
            INTENT_BOND_QUERY: "Let me help you figure out what you can afford! 🏦 What's your gross monthly income? Do you have any existing loans or accounts? And what price range are you looking at?",
            
            INTENT_LISTING_ADD: "Let's add your listing! 🏠 I'll need: number of bedrooms & bathrooms, price, area/suburb, property type, and a short description. Photos help too — you can send them here.",
            
            INTENT_VIEWING_REQUEST: "I'd love to book a viewing for you! 📅 Which property are you interested in? And what day/time works best for you?",
            
            INTENT_DEAL_UPDATE: "Got it — I've noted that update. 📋 I'll keep tracking this deal for you.",
            
            INTENT_PIPELINE_CHECK: "Let me pull up your pipeline... 📊 One moment. (Pipeline tracking is being set up — your agent will have full visibility soon!)",
            
            INTENT_RENTAL_QUERY: "Let me check on that rental query for you. 🏢 Could you give me a bit more detail — which property or tenant is this about?",
            
            INTENT_MAINTENANCE: "Thanks for reporting this. 🔧 I've logged the maintenance issue. The agent will arrange for someone to look at it. Could you confirm which property/unit this is for?",
            
            INTENT_MARKET_QUERY: "Market intel coming your way! 📈 I can provide area reports, recent sales, and price trends. Which area are you interested in?",
            
            INTENT_UNKNOWN: "I'm not quite sure what you need. 🤔 Could you rephrase that? I can help with: finding properties, valuations, bond checks, viewings, listings, and more!",
            
            INTENT_GENERAL_CHAT: "I'm here to help with all things property! 🏠 Whether you're buying, selling, renting, or just curious about the market — ask away!",
        }

        text = responses.get(intent, responses[INTENT_UNKNOWN])
        return GeneratedResponse(text=text)

    def _fallback_search_response(self, entities: Dict[str, Any]) -> str:
        """Build a natural fallback property search response."""
        area = entities.get("area", "your area")
        beds = entities.get("bedrooms", "")
        max_price = entities.get("max_price", "")

        beds_str = f"{beds}-bedroom " if beds else ""
        price_str = f" under R{max_price:,.0f}" if max_price else ""

        return (
            f"Let me search for {beds_str}properties in {area}{price_str}... 🔍\n\n"
            f"I'm setting up the full listing database now. In the meantime, your agent will be notified "
            f"and can send you matching properties directly. Can I also ask — what's your budget range "
            f"and are you pre-approved for a bond?"
        )


# Singleton
responder = SmartResponder()
