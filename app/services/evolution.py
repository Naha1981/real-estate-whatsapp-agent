"""
Evolution API client v2.x — WhatsApp messaging via Evolution API.
Supports Evolution API v2.3.7 URL patterns.

Docs: https://doc.evolution-api.com
"""
import httpx
import logging
import os
from typing import Optional, Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)


class EvolutionClient:
    """Client for Evolution API v2.x (Baileys-based WhatsApp)."""

    def __init__(self):
        self.base_url = settings.evolution_api_url.rstrip("/")
        self.instance = settings.evolution_instance_name
        self.api_key = settings.evolution_api_key
        # Instance token for message operations
        self.instance_token = os.getenv("EVOLUTION_INSTANCE_TOKEN", self.api_key)
        self.webhook_secret = settings.webhook_secret

    @property
    def _headers(self) -> dict:
        return {
            "apikey": self.instance_token,
            "Content-Type": "application/json",
        }

    @property
    def _mgr_headers(self) -> dict:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    # ── MESSAGE SENDING (v2: /message/sendText/{instance}) ──

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def send_text(self, to: str, text: str, delay: int = 1200) -> Dict[str, Any]:
        payload = {"number": to, "text": text, "delay": delay}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                json=payload, headers=self._headers,
            )
            if resp.status_code >= 400:
                logger.warning(f"Send text failed ({resp.status_code}): {resp.text[:300]}")
            resp.raise_for_status()
            return resp.json()

    async def send_image(self, to: str, image_url: str, caption: Optional[str] = None) -> Dict[str, Any]:
        payload = {"number": to, "mediatype": "image", "media": image_url}
        if caption:
            payload["caption"] = caption
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/message/sendMedia/{self.instance}",
                json=payload, headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def send_document(self, to: str, document_url: str, filename: str, caption: Optional[str] = None) -> Dict[str, Any]:
        payload = {"number": to, "mediatype": "document", "media": document_url, "fileName": filename}
        if caption:
            payload["caption"] = caption
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/message/sendMedia/{self.instance}",
                json=payload, headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def send_voice(self, to: str, audio_url: str) -> Dict[str, Any]:
        payload = {"number": to, "mediatype": "audio", "media": audio_url}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/message/sendMedia/{self.instance}",
                json=payload, headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def send_listing_card(self, to: str, listings: List[Dict[str, Any]]) -> None:
        if not listings:
            await self.send_text(to, "I don't have any matching properties right now. I'll save your search and alert you when something comes up! 🏠")
            return
        parts = []
        for i, listing in enumerate(listings[:5], 1):
            card = (
                f"*{i}. {listing.get('title', 'Property')}*\n"
                f"📍 {listing.get('suburb', '')}\n"
                f"🛏 {listing.get('bedrooms', '?')} bed | 🛁 {listing.get('bathrooms', '?')} bath\n"
                f"💰 R{listing.get('price', 0):,.0f}\n"
            )
            if listing.get("features"):
                card += f"✨ {', '.join(listing['features'][:3])}\n"
            parts.append(card)
        message = "\n" + "─" * 25 + "\n".join(parts)
        message += f"\n{'─' * 25}\nReply with the number (1-{len(listings)}) for more details or to book a viewing! 📅"
        await self.send_text(to, message)

    # ── INSTANCE MANAGEMENT (v2) ────────────

    async def get_instance_status(self) -> Dict[str, Any]:
        """Check connection state of the instance."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/instance/connectionState/{self.instance}",
                headers=self._headers,
            )
            return resp.json()

    async def connect_instance(self) -> Dict[str, Any]:
        """Get QR code to connect WhatsApp."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.base_url}/instance/connect/{self.instance}",
                headers=self._headers,
            )
            return resp.json()

    async def set_webhook(self, webhook_url: str, events: List[str] = None) -> Dict[str, Any]:
        """Configure webhook for the instance."""
        if events is None:
            events = ["MESSAGES_UPSERT"]
        payload = {
            "webhook": {
                "enabled": True,
                "url": webhook_url,
                "events": events,
                "webhookByEvents": False,
            }
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.base_url}/webhook/set/{self.instance}",
                json=payload, headers=self._headers,
            )
            return resp.json()

    async def check_webhook(self) -> Dict[str, Any]:
        """Check current webhook configuration."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/webhook/find/{self.instance}",
                headers=self._headers,
            )
            return resp.json()


# Singleton
evolution = EvolutionClient()
