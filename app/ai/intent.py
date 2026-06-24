"""
Intent Classifier — determines what the user wants from their WhatsApp message.
Uses LLM (OpenAI or Anthropic) to classify intent and extract entities.

Supports code-switching (Zulu/English/Sotho/Tsotsitaal mixed messages).
"""
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger(__name__)

# ── Intent Types ──────────────────────────────────────

INTENT_PROPERTY_SEARCH = "property_search"
INTENT_LISTING_ADD = "listing_add"
INTENT_LISTING_UPDATE = "listing_update"
INTENT_VIEWING_REQUEST = "viewing_request"
INTENT_VALUATION_REQUEST = "valuation_request"
INTENT_BOND_QUERY = "bond_query"
INTENT_DOCUMENT_REQUEST = "document_request"
INTENT_DEAL_UPDATE = "deal_update"
INTENT_PIPELINE_CHECK = "pipeline_check"
INTENT_RENTAL_QUERY = "rental_query"
INTENT_MAINTENANCE = "maintenance"
INTENT_MARKET_QUERY = "market_query"
INTENT_GENERAL_CHAT = "general_chat"
INTENT_GREETING = "greeting"
INTENT_UNKNOWN = "unknown"


@dataclass
class ClassifiedIntent:
    """Result of intent classification."""
    intent: str
    confidence: float = 0.0
    entities: Dict[str, Any] = field(default_factory=dict)
    original_message: str = ""
    needs_human: bool = False
    reasoning: str = ""


# ── Classification Prompt ─────────────────────────────

CLASSIFICATION_SYSTEM_PROMPT = """You are the intent classifier for iGosa, a WhatsApp AI assistant for South African estate agents.

Your job: Analyze the user's WhatsApp message and determine their INTENT and extract ENTITIES.

The user may be:
1. An estate AGENT using iGosa to manage their business
2. A BUYER/CLIENT looking for property (the agent forwards these to iGosa)

Context about South African township real estate:
- Areas include Soweto, Pimville, Diepkloof, Meadowlands, Orlando, Protea Glen, Alexandra, Tembisa, Katlehong, Vosloorus, Lenasia, Eldorado Park, Cosmo City, Diepsloot
- RDP houses are government-subsidized houses with resale restrictions (8-year rule)
- Prices are in South African Rand (R)
- FLISP is a government housing subsidy
- Messages may contain Zulu, Sotho, Tsotsitaal, and English mixed together (code-switching)
- "bond" means mortgage/home loan in SA context
- "OTP" means Offer to Purchase
- "FICA" means identity/address verification documents

INTENTS (pick ONE):

property_search: Looking for properties to buy or rent
  Entities: bedrooms, bathrooms, min_price, max_price, area (suburb/region), property_type (house/apartment/rdp/land/room), price_type (sale/rent)
  Examples: "2 bed Pimville under R400K", "ngifuna i-house eSoweto 3 bedroom", "what do you have in Diepkloof?"

listing_add: Adding a new property listing
  Entities: title, bedrooms, bathrooms, price, area/suburb, property_type, features
  Examples: "add listing: 3 bed Pimville R450K", "new property: 2 bedroom flat in Hillbrow R280K"

viewing_request: Requesting to view a property
  Entities: listing_reference (number or address), preferred_time
  Examples: "I want to see number 2", "can I view the Pimville house?"

valuation_request: Asking for property valuation
  Entities: bedrooms, bathrooms, area, floor_area_sqm, features
  Examples: "value: 3 bed Diepkloof Zone 4", "how much is my house worth?"

bond_query: Questions about home loans / mortgage / FLISP
  Entities: income (monthly), property_price
  Examples: "can I afford R400K?", "I earn R15000 what bond can I get?"

deal_update: Updating a deal's status
  Entities: deal_id, new_stage, amount
  Examples: "update deal #14 accepted R415K", "offer accepted on Thabo's deal"

pipeline_check: Checking deal pipeline
  Entities: none critical
  Examples: "pipeline", "how many deals?", "what's my pipeline?"

rental_query: Questions about rental properties or tenant management
  Entities: query_type (payment/maintenance/lease/tenant)
  Examples: "did tenant 4 pay?", "rent overdue unit 3"

maintenance: Reporting or checking maintenance issues
  Entities: unit_number, issue_description
  Examples: "geyser leaking unit 2", "maintenance request for flat 5"

market_query: Questions about market trends, competitor activity
  Entities: area, query_type (trends/sales/comparables)
  Examples: "what's selling in Pimville?", "market report Soweto"

greeting: Simple greeting/hello
  Examples: "hi", "hello", "sawubona", "dumela", "hallo"

general_chat: Casual conversation not fitting other intents

Return JSON ONLY, no other text:
{
  "intent": "property_search",
  "confidence": 0.95,
  "entities": {
    "bedrooms": 2,
    "max_price": 400000,
    "area": "Pimville",
    "property_type": "house",
    "price_type": "sale"
  },
  "needs_human": false,
  "reasoning": "User is searching for a 2-bedroom house in Pimville under R400K"
}

For code-switched messages, understand the mix and extract entities correctly:
"Sawubona, ngifuna i-house eSoweto, like 3 bedroom under R500K maybe"
→ intent: property_search, entities: {bedrooms: 3, max_price: 500000, area: "Soweto", property_type: "house"}

If intent is truly unclear, set intent to "unknown" and needs_human to true."""


# ── AI Client ─────────────────────────────────────────

class IntentClassifier:
    """Classifies WhatsApp messages into intents and extracts entities."""

    def __init__(self):
        self.client = None  # AsyncOpenAI (lazy-loaded)
        self._client_initialized = False
        self.model = settings.openai_model

    async def _ensure_client(self):
        """Lazy-load the OpenAI client only when API key is available."""
        if not self._client_initialized:
            if settings.openai_api_key:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            self._client_initialized = True

    async def classify(self, message: str, sender_role: str = "unknown") -> ClassifiedIntent:
        """
        Classify a WhatsApp message.
        
        Args:
            message: The text content of the WhatsApp message
            sender_role: "agent" or "client" — helps contextualize
        
        Returns:
            ClassifiedIntent with intent, entities, and confidence
        """
        await self._ensure_client()
        if not self.client:
            logger.warning("No AI client configured — using fallback classification")
            return self._fallback_classify(message)

        # Build context about the sender
        role_context = ""
        if sender_role == "agent":
            role_context = "\nThe sender is an ESTATE AGENT using iGosa to manage their business."
        elif sender_role == "client":
            role_context = "\nThe sender is a PROPERTY BUYER/CLIENT looking for property."

        user_prompt = f"Message: \"{message}\"{role_context}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Low temp for consistent classification
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            return ClassifiedIntent(
                intent=result.get("intent", INTENT_UNKNOWN),
                confidence=result.get("confidence", 0.0),
                entities=result.get("entities", {}),
                original_message=message,
                needs_human=result.get("needs_human", False),
                reasoning=result.get("reasoning", ""),
            )

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return self._fallback_classify(message)

    def _fallback_classify(self, message: str) -> ClassifiedIntent:
        """
        Rule-based fallback when LLM is unavailable.
        Handles the most common patterns.
        """
        msg_lower = message.lower().strip()

        # Check explicit commands FIRST (before broad keyword matching)
        
        # Listing add (check before property_search to avoid "bed" false match)
        if any(k in msg_lower for k in ["add listing", "new listing", "new property", "new house", "post listing"]):
            return ClassifiedIntent(intent=INTENT_LISTING_ADD, confidence=0.7, original_message=message)

        # Valuation
        if any(k in msg_lower for k in ["value:", "valuation", "how much is", "what's it worth", "estimate", "comparative"]):
            return ClassifiedIntent(intent=INTENT_VALUATION_REQUEST, confidence=0.7, original_message=message)

        # Bond (before property_search to avoid "house" false match)
        if any(k in msg_lower for k in ["bond", "mortgage", "home loan", "afford", "pre-approv", "flisp", "qualify"]):
            return ClassifiedIntent(intent=INTENT_BOND_QUERY, confidence=0.7, original_message=message)

        # Viewing (before property_search to avoid "house" false match)
        if any(k in msg_lower for k in ["viewing", "view the", "see the", "show me the", "visit the", "book a viewing"]):
            return ClassifiedIntent(intent=INTENT_VIEWING_REQUEST, confidence=0.7, original_message=message)

        # Deal update
        if any(k in msg_lower for k in ["update deal", "offer accepted", "offer made", "deal closed", "mark as sold"]):
            return ClassifiedIntent(intent=INTENT_DEAL_UPDATE, confidence=0.7, original_message=message)

        # Pipeline
        if any(k in msg_lower for k in ["pipeline", "my deals", "deal status"]):
            return ClassifiedIntent(intent=INTENT_PIPELINE_CHECK, confidence=0.8, original_message=message)

        # Market query
        if any(k in msg_lower for k in ["market", "selling in", "trend", "what's moving", "report", "sold in"]):
            return ClassifiedIntent(intent=INTENT_MARKET_QUERY, confidence=0.6, original_message=message)

        # Greetings (short messages only)
        if any(g in msg_lower for g in ["hi", "hello", "sawubona", "dumela", "hallo", "hey", "good morning", "good afternoon"]):
            if len(msg_lower.split()) <= 3:
                return ClassifiedIntent(intent=INTENT_GREETING, confidence=0.9, original_message=message)

        # Property search indicators (broad — catch remaining)
        search_keywords = ["looking for", "do you have", "i need", "ngifuna", "available", "what's available", "find me"]
        if any(k in msg_lower for k in search_keywords) or any(
            word in msg_lower for word in ["bedroom", "bed", "house", "apartment", "flat", "rdp", "room"]
        ):
            entities = self._extract_basic_entities(message)
            return ClassifiedIntent(
                intent=INTENT_PROPERTY_SEARCH,
                confidence=0.7,
                entities=entities,
                original_message=message,
            )

        # Rental
        if any(k in msg_lower for k in ["rent", "tenant", "landlord", "lease", "deposit", "rental"]):
            return ClassifiedIntent(intent=INTENT_RENTAL_QUERY, confidence=0.6, original_message=message)

        # Maintenance
        if any(k in msg_lower for k in ["leaking", "broken", "repair", "maintenance", "geyser", "leak", "fix"]):
            return ClassifiedIntent(intent=INTENT_MAINTENANCE, confidence=0.7, original_message=message)

        # Fallback
        return ClassifiedIntent(intent=INTENT_UNKNOWN, confidence=0.3, needs_human=True, original_message=message)

    def _extract_basic_entities(self, message: str) -> Dict[str, Any]:
        """Crude entity extraction for fallback mode."""
        import re
        entities = {}
        msg_lower = message.lower()

        # Bedrooms
        bed_match = re.search(r'(\d+)\s*bed', msg_lower)
        if bed_match:
            entities["bedrooms"] = int(bed_match.group(1))

        # Bathrooms
        bath_match = re.search(r'(\d+)\s*bath', msg_lower)
        if bath_match:
            entities["bathrooms"] = int(bath_match.group(1))

        # Price
        price_match = re.search(r'[Rr]\s*(\d[\d\s]*[KkMm]?)', message)
        if price_match:
            price_str = price_match.group(1).replace(" ", "")
            if 'k' in price_str.lower():
                entities["max_price"] = float(price_str.lower().replace('k', '')) * 1000
            elif 'm' in price_str.lower():
                entities["max_price"] = float(price_str.lower().replace('m', '')) * 1000000
            else:
                entities["max_price"] = float(price_str)

        # Price type
        if "rent" in msg_lower:
            entities["price_type"] = "rent"

        # Areas — common Johannesburg townships/suburbs
        areas = [
            "soweto", "pimville", "diepkloof", "meadowlands", "orlando", "protea glen",
            "protea", "jabulani", "dube", "rockville", "mapetla", "zola", "chris hani",
            "baragwanath", "alexandra", "alex", "tembisa", "katlehong", "vosloorus",
            "lenasia", "eldorado", "cosmo city", "diepsloot", "midrand", "ivory park",
            "hillbrow", "berea", "yeoville", "braamfontein", "johannesburg", "joburg",
            "randburg", "sandton", "roodepoort", "florida", "alberton", "germiston",
            "rosettenville", "turffontein", "malvern", "ormonde", "bramley", "alexandra",
        ]
        for area in areas:
            if area in msg_lower:
                entities["area"] = area.title()
                break

        return entities


# Singleton classifier
classifier = IntentClassifier()
