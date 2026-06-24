"""
Document Service — FICA collection, OTP generation, compliance tracking.
Manages document workflows via WhatsApp.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.database import Deal, Lead
from app.services.evolution import evolution

logger = logging.getLogger(__name__)


DOCUMENT_CHECKLIST = {
    "buyer": [
        {"name": "ID Copy", "key": "buyer_id", "description": "Certified copy of your SA ID (both sides)"},
        {"name": "Proof of Address", "key": "buyer_poa", "description": "Not older than 3 months (utility bill, bank statement)"},
        {"name": "Bank Statements", "key": "buyer_bank", "description": "Last 3 months' bank statements"},
    ],
    "seller": [
        {"name": "ID Copy", "key": "seller_id", "description": "Certified copy of your SA ID (both sides)"},
        {"name": "Proof of Address", "key": "seller_poa", "description": "Not older than 3 months"},
        {"name": "Title Deed", "key": "title_deed", "description": "Original title deed or deed search result"},
    ],
    "compliance": [
        {"name": "Electrical CoC", "key": "elec_coc", "description": "Electrical Certificate of Compliance"},
        {"name": "Gas CoC", "key": "gas_coc", "description": "Gas Certificate (if applicable)"},
        {"name": "Entomologist", "key": "entomologist", "description": "Wood borer/termite certificate (if applicable)"},
        {"name": "Plumbing CoC", "key": "plumbing_coc", "description": "Plumbing certificate (City of Joburg requirement)"},
    ],
}

OTP_TEMPLATE = """OFFER TO PURCHASE

1. PARTIES
Seller: {seller_name}
ID Number: {seller_id}
Buyer: {buyer_name}
ID Number: {buyer_id}

2. PROPERTY
Address: {property_address}
Erf Number: {erf_number}
Size: {erf_size}

3. PURCHASE PRICE
Purchase Price: R{purchase_price:,.0f}
Deposit: R{deposit:,.0f}
Balance: R{balance:,.0f}

4. CONDITIONS
This offer is subject to:
- Bond approval within {bond_days} days
- Property inspection
- {special_conditions}

5. OCCUPATION
Occupation date: {occupation_date}
Occupational rent: R{occupational_rent:,.0f}/month (if applicable)

6. ACCEPTANCE
This offer is valid until: {offer_expiry}

Signed at ________________ on this ___ day of __________ 20___

_________________________
BUYER

_________________________
SELLER
"""


class DocumentService:
    """Manages document collection and OTP generation."""

    async def request_documents(
        self, db: AsyncSession, deal_id: str, party: str, whatsapp_number: str
    ):
        """Request documents from a party via WhatsApp."""
        checklist = DOCUMENT_CHECKLIST.get(party, DOCUMENT_CHECKLIST["buyer"])

        msg = f"📄 *Documents Needed — {party.upper()}*\n\n"
        msg += "Please send clear photos or PDFs of:\n\n"
        for i, doc in enumerate(checklist, 1):
            msg += f"{i}. *{doc['name']}*\n   _{doc['description']}_\n\n"
        msg += "📸 You can take photos and send them right here on WhatsApp.\n"
        msg += "📌 Mark each photo with the document type (e.g., 'ID Front', 'Proof of Address')"

        await evolution.send_text(whatsapp_number, msg)

        # Update deal document tracking
        result = await db.execute(select(Deal).where(Deal.id == deal_id))
        deal = result.scalar_one_or_none()
        if deal:
            docs = json.loads(deal.documents_collected or "{}")
            for doc in checklist:
                docs[f"{party}_{doc['key']}"] = "requested"
            deal.documents_collected = json.dumps(docs)
            await db.commit()

        logger.info(f"📄 Document requests sent to {whatsapp_number} for deal {deal_id}")

    async def mark_document_received(
        self, db: AsyncSession, deal_id: str, doc_key: str
    ):
        """Mark a document as received."""
        result = await db.execute(select(Deal).where(Deal.id == deal_id))
        deal = result.scalar_one_or_none()
        if not deal:
            return

        docs = json.loads(deal.documents_collected or "{}")
        docs[doc_key] = "received"
        deal.documents_collected = json.dumps(docs)
        await db.commit()

    async def get_document_status(self, db: AsyncSession, deal_id: str) -> Dict[str, Any]:
        """Get document collection status for a deal."""
        result = await db.execute(select(Deal).where(Deal.id == deal_id))
        deal = result.scalar_one_or_none()
        if not deal:
            return {"error": "Deal not found"}

        docs = json.loads(deal.documents_collected or "{}")

        status = {
            "buyer": {},
            "seller": {},
            "compliance": {},
        }

        for party in ["buyer", "seller"]:
            for doc in DOCUMENT_CHECKLIST[party]:
                key = doc["key"]
                status[party][doc["name"]] = docs.get(f"{party}_{key}", "not_requested")

        for doc in DOCUMENT_CHECKLIST["compliance"]:
            status["compliance"][doc["name"]] = docs.get(doc["key"], "not_requested")

        # Calculate completion
        all_keys = []
        for p in ["buyer", "seller", "compliance"]:
            for d in DOCUMENT_CHECKLIST[p]:
                all_keys.append(d["key"] if p == "compliance" else f"{p}_{d['key']}")

        received = sum(1 for k in all_keys if docs.get(k) == "received")
        total = len(all_keys)
        status["progress"] = f"{received}/{total} ({int(received/total*100)}%)"

        return status

    def generate_otp(self, deal_data: Dict[str, Any]) -> str:
        """Generate Offer to Purchase document text."""
        return OTP_TEMPLATE.format(
            **deal_data,
            balance=deal_data.get("purchase_price", 0) - deal_data.get("deposit", 0),
            special_conditions=deal_data.get("special_conditions", "Standard terms and conditions apply."),
        )

    async def format_doc_status_message(self, db: AsyncSession, deal_id: str) -> str:
        """Format document status as WhatsApp message."""
        status = await self.get_document_status(db, deal_id)

        if "error" in status:
            return "❌ Deal not found."

        msg = f"📄 *Document Status — Deal {deal_id[:8]}*\n"
        msg += f"Progress: {status['progress']}\n\n"

        emoji = {"received": "✅", "requested": "⏳", "not_requested": "⬜"}

        for party, docs in [("Buyer", status["buyer"]), ("Seller", status["seller"]), ("Compliance", status["compliance"])]:
            msg += f"*{party}:*\n"
            for doc_name, doc_status in docs.items():
                e = emoji.get(doc_status, "⬜")
                msg += f"  {e} {doc_name}\n"
            msg += "\n"

        return msg


# Singleton
document_service = DocumentService()
