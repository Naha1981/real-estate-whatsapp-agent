"""
Entity Extractor — extracts structured data from WhatsApp messages.
Used for extracting listing details, deal info, and lead profiles from natural language.

This runs AFTER intent classification — it extracts fine-grained entities specific to the intent.
"""
import json
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta



from app.config import settings

logger = logging.getLogger(__name__)


EXTRACTION_SYSTEM_PROMPT = """You are an entity extractor for iGosa, a WhatsApp AI for SA estate agents.

Extract structured data from the message based on the INTENT TYPE provided.
Handle South African township real estate context:
- Prices in Rand (R)
- Areas: Soweto, Pimville, Diepkloof, Meadowlands, Orlando, Alexandra, Tembisa, Katlehong, Lenasia, Eldorado Park, Cosmo City, Diepsloot, etc.
- RDP = government housing with 8-year resale restriction
- Bond = mortgage/home loan
- OTP = Offer to Purchase
- FICA = identity verification documents
- FLISP = government housing subsidy

Return ONLY valid JSON. If a field is not found, use null (not "unknown" or "N/A")."""


EXTRACTION_PROMPTS = {
    "listing_add": """
Extract property listing details from this message:
{message}

Return JSON:
{{
  "title": "catchy title or null",
  "bedrooms": number or null,
  "bathrooms": number or null, 
  "price": number (Rands) or null,
  "price_type": "sale" or "rent",
  "property_type": "house"/"apartment"/"rdp"/"land"/"room",
  "suburb": "area name or null",
  "address": "full address or null",
  "floor_area_sqm": number or null,
  "erf_size_sqm": number or null,
  "features": ["list", "of", "features"] or [],
  "description": "full description or null"
}}""",

    "valuation_request": """
Extract property details for valuation:
{message}

Return JSON:
{{
  "bedrooms": number or null,
  "bathrooms": number or null,
  "suburb": "area name or null",
  "floor_area_sqm": number or null,
  "features": ["list"] or [],
  "property_type": "house"/"apartment"/"rdp" or null
}}""",

    "deal_update": """
Extract deal update information:
{message}

Return JSON:
{{
  "deal_reference": "deal number/name or null",
  "new_stage": "lead/viewing/offer/negotiation/accepted/bond_pending/closed/lost",
  "amount": number (Rands) or null,
  "notes": "any additional context"
}}""",

    "bond_query": """
Extract bond affordability query:
{message}

Return JSON:
{{
  "monthly_income": number (Rands) or null,
  "property_price": number (Rands) or null,
  "has_existing_loans": true/false/null,
  "monthly_debt_payments": number or null,
  "deposit_amount": number or null,
  "interested_in_flisp": true/false
}}""",

    "maintenance": """
Extract maintenance request:
{message}

Return JSON:
{{
  "unit_reference": "unit/flat number or address or null",
  "issue_type": "plumbing/electrical/structural/appliance/other",
  "issue_description": "what's wrong",
  "urgency": "low/medium/high/emergency"
}}""",
}


class EntityExtractor:
    """Extracts structured entities from natural language messages."""

    def __init__(self):
        self.client = None  # AsyncOpenAI (lazy-loaded)
        self.model = settings.openai_model

    async def extract(self, message: str, intent: str) -> Dict[str, Any]:
        """
        Extract entities specific to the intent type.
        Falls back to regex-based extraction if LLM unavailable.
        """
        if intent not in EXTRACTION_PROMPTS:
            return {}

        if self.client:
            return await self._llm_extract(message, intent)
        else:
            return self._regex_extract(message, intent)

    async def _llm_extract(self, message: str, intent: str) -> Dict[str, Any]:
        """Use LLM to extract entities."""
        prompt_template = EXTRACTION_PROMPTS[intent]
        user_prompt = prompt_template.format(message=message)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return self._regex_extract(message, intent)

    def _regex_extract(self, message: str, intent: str) -> Dict[str, Any]:
        """Basic regex extraction for when LLM is unavailable."""
        result = {}

        # Bedrooms
        bed_match = re.search(r'(\d+)\s*b[ee]d', message.lower())
        if bed_match:
            result["bedrooms"] = int(bed_match.group(1))

        # Bathrooms
        bath_match = re.search(r'(\d+)\s*bath', message.lower())
        if bath_match:
            result["bathrooms"] = int(bath_match.group(1))

        # Price
        price_match = re.search(r'[Rr]\s*(\d[\d\s]*[KkMm]?)', message)
        if price_match:
            price_str = price_match.group(1).replace(" ", "")
            if price_str.lower().endswith('k'):
                result["price"] = float(price_str[:-1]) * 1000
            elif price_str.lower().endswith('m'):
                result["price"] = float(price_str[:-1]) * 1000000
            else:
                result["price"] = float(price_str)

        # Area
        areas = [
            "soweto", "pimville", "diepkloof", "meadowlands", "orlando",
            "protea glen", "alexandra", "tembisa", "katlehong", "lenasia",
            "eldorado", "cosmo city", "diepsloot", "hillbrow",
        ]
        for area in areas:
            if area in message.lower():
                result["suburb"] = area.title()
                break

        # Property type
        if "rdp" in message.lower():
            result["property_type"] = "rdp"
        elif "apartment" in message.lower() or "flat" in message.lower():
            result["property_type"] = "apartment"
        elif "house" in message.lower():
            result["property_type"] = "house"
        elif "land" in message.lower() or "stand" in message.lower():
            result["property_type"] = "land"

        # Price type
        if "rent" in message.lower():
            result["price_type"] = "rent"

        # Income (for bond queries)
        income_match = re.search(r'[Rr]\s*(\d[\d\s]*[Kk]?)\s*(?:income|salary|earn|gross)', message.lower())
        if not income_match:
            income_match = re.search(r'(?:earn|income|salary)\s*[Rr]?\s*(\d[\d\s]*[Kk]?)', message.lower())
        if income_match:
            inc_str = income_match.group(1).replace(" ", "")
            if inc_str.lower().endswith('k'):
                result["monthly_income"] = float(inc_str[:-1]) * 1000
            else:
                result["monthly_income"] = float(inc_str)

        return result


# Singleton
extractor = EntityExtractor()
