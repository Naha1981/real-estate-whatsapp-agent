"""
Webhook Router v2 — receives WhatsApp messages from Evolution API,
processes through the full AI pipeline with orchestrator dispatch.
"""
import json
import logging
import hashlib
import hmac
import base64
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.services.evolution import evolution
from app.services.database import get_db, Agent, Lead, Conversation
from app.services.orchestrator import orchestrator
from app.services.followup import follow_up_manager, trigger_follow_up_on_new_lead
from app.ai.intent import classifier, ClassifiedIntent, INTENT_UNKNOWN

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


# ── Helpers ───────────────────────────────────────────

def clean_phone(jid: str) -> str:
    return jid.split("@")[0] if "@" in jid else jid


def extract_message_text(data: Dict[str, Any]) -> tuple:
    message = data.get("message", {})
    msg_type = message.get("messageType", "conversation") if isinstance(message, dict) else "conversation"

    if msg_type in ("conversation", "extendedTextMessage"):
        if isinstance(message, dict):
            text = message.get("conversation") or message.get("extendedTextMessage", {}).get("text", "") or message.get("text", {}).get("text", "")
        else:
            text = str(message)
        return text, "text"

    if msg_type == "audioMessage":
        return "[Voice Note]", "voice"
    if msg_type == "imageMessage":
        caption = (message.get("imageMessage", {}) or {}).get("caption", "") if isinstance(message, dict) else ""
        return caption or "[Image]", "image"
    if msg_type == "videoMessage":
        caption = (message.get("videoMessage", {}) or {}).get("caption", "") if isinstance(message, dict) else ""
        return caption or "[Video]", "video"
    if msg_type == "documentMessage":
        caption = (message.get("documentMessage", {}) or {}).get("caption", "") if isinstance(message, dict) else ""
        return caption or "[Document]", "document"
    if msg_type == "locationMessage":
        return "[Location Shared]", "location"
    if msg_type == "contactMessage":
        return "[Contact Shared]", "contact"

    return "[Unsupported Message]", "other"


async def get_or_create_agent(db: AsyncSession, phone: str) -> Optional[Agent]:
    result = await db.execute(select(Agent).where(Agent.whatsapp_number == phone, Agent.is_active == True))
    return result.scalar_one_or_none()


async def get_or_create_lead(db: AsyncSession, agent_id: str, phone: str, entities: Dict = None) -> Lead:
    result = await db.execute(
        select(Lead).where(Lead.agent_id == agent_id, Lead.whatsapp_number == phone)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        import json as _json
        lead = Lead(
            agent_id=agent_id,
            whatsapp_number=phone,
            lead_status="new",
            preferred_areas=_json.dumps([entities.get("area")]) if entities and entities.get("area") else None,
            budget_min=entities.get("min_price") if entities else None,
            budget_max=entities.get("max_price") if entities else None,
            bedrooms_min=entities.get("bedrooms") if entities else None,
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
    return lead


async def log_conversation(db, lead_id, agent_id, direction, text, msg_type, intent=None, ai_resp=False, ai_text=None):
    conv = Conversation(
        lead_id=lead_id,
        agent_id=agent_id,
        direction=direction,
        message_type=msg_type,
        message_text=text[:2000] if text else None,
        intent_classified=intent,
        ai_responded=ai_resp,
        ai_response=ai_text[:2000] if ai_text else None,
    )
    db.add(conv)
    await db.commit()


# ── Webhook Endpoints ─────────────────────────────────

@router.post("/evolution")
async def evolution_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Main Evolution API webhook — processes all incoming WhatsApp messages."""
    body = await request.body()

    if settings.environment != "development":
        signature = request.headers.get("x-webhook-signature", "")
        if signature and settings.webhook_secret:
            expected = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle webhookBase64: Evolution API encodes the 'data' field as base64
    data = payload.get("data", {})
    if isinstance(data, str) and len(data) > 10:
        try:
            decoded = base64.b64decode(data).decode('utf-8')
            data = json.loads(decoded)
            logger.info("🔓 Decoded base64 webhook data")
        except Exception:
            pass  # Not base64, use as-is

    event = payload.get("event", "")

    if event == "messages.upsert":
        await handle_message(data, db)
    elif event == "connection.update":
        status = data.get("status", "unknown")
        logger.info(f"📡 Connection: {status}")
    elif event == "qrcode.update":
        logger.info("📱 QR code received")

    return {"status": "ok"}


@router.get("/evolution")
async def webhook_verify():
    return {"status": "healthy", "service": "igosa-webhook"}


# ── Message Handler ───────────────────────────────────

async def handle_message(data: Dict[str, Any], db: AsyncSession):
    """Process an incoming WhatsApp message through the full AI pipeline."""
    key = data.get("key", {})
    remote_jid = key.get("remoteJid", "")
    from_me = key.get("fromMe", False)

    if from_me:
        return
    if not remote_jid:
        return

    sender_phone = clean_phone(remote_jid)
    
    # Skip group messages for now
    if "@g.us" in remote_jid:
        return
    
    message_text, message_type = extract_message_text(data)

    if not message_text or message_type == "other":
        return

    message_text = message_text.strip()
    if not message_text:
        return

    logger.info(f"📩 {sender_phone}: {message_text[:100]}")

    # ── Find or default agent ──
    agent = await get_or_create_agent(db, sender_phone)
    sender_role = "agent" if agent else "client"

    if not agent:
        # Use first active agent as fallback (pilot mode)
        result = await db.execute(select(Agent).where(Agent.is_active == True).limit(1))
        agent = result.scalar_one_or_none()

    if not agent:
        await evolution.send_text(sender_phone, "Hi! 👋 iGosa is being set up. We'll be with you soon!")
        return

    # ── AI Pipeline ──────────────────────────────
    # 1. Classify intent
    classified = await classifier.classify(message_text, sender_role)
    logger.info(f"🎯 Intent: {classified.intent} ({classified.confidence:.2f})")

    # 2. Get/create lead
    lead = None
    if classified.intent not in ["greeting", "general_chat", "unknown"]:
        lead = await get_or_create_lead(db, agent.id, sender_phone, classified.entities)

    # 3. Handle voice notes
    if message_type == "voice":
        if sender_role == "agent":
            response = "I received your voice note. 🎤 Voice transcription is coming soon! For now, please type your message and I'll help right away."
        else:
            response = "I received your voice note! 🎤 Please type your request and I'll help you find properties, check affordability, or book viewings."
        await evolution.send_text(sender_phone, response)
        return

    # 4. Dispatch to orchestrator
    response_text = await orchestrator.handle(
        db, classified, agent.id, sender_phone, sender_role, lead.id if lead else None
    )

    # 5. Log conversation
    if lead:
        await log_conversation(db, lead.id, agent.id, "inbound", message_text, message_type, intent=classified.intent)
        await log_conversation(db, lead.id, agent.id, "outbound", response_text, "text", ai_resp=True, ai_text=response_text)

    # 6. Send response
    try:
        # Handle long messages (> 4096 chars — WhatsApp limit)
        if len(response_text) > 4000:
            parts = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            for part in parts:
                await evolution.send_text(sender_phone, part)
        else:
            await evolution.send_text(sender_phone, response_text)
        logger.info(f"✅ Response sent to {sender_phone}")
    except Exception as e:
        logger.error(f"❌ Failed to send: {e}")

    # 7. Handoff to human if classifier is unsure
    if classified.needs_human:
        await evolution.send_text(
            agent.whatsapp_number,
            f"🔔 *Needs attention*\nFrom: {sender_phone}\nMessage: {message_text[:200]}\nIntent: {classified.intent}"
        )


# ── Health Check ──────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "healthy", "service": "igosa", "version": "0.2.0"}
