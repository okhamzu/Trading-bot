from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path

from src.config import Settings

LOGGER = logging.getLogger(__name__)


class WhatsAppProvider(ABC):
    @abstractmethod
    def send_text(self, message: str) -> bool: ...

    def send_image(self, path: str | Path, caption: str) -> bool:
        LOGGER.warning("%s does not support local image upload; sending text only", type(self).__name__)
        return self.send_text(caption)


class LoggingProvider(WhatsAppProvider):
    def send_text(self, message: str) -> bool:
        LOGGER.info("DRY-RUN WhatsApp alert:\n%s", message)
        return True


class CallMeBotProvider(WhatsAppProvider):
    def __init__(self, phone: str, api_key: str):
        self.phone, self.api_key = phone, api_key

    def send_text(self, message: str) -> bool:
        try:
            import requests
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install requests to use CallMeBot") from exc
        return _retry(lambda: requests.get("https://api.callmebot.com/whatsapp.php", params={"phone": self.phone, "apikey": self.api_key, "text": message}, timeout=20))


class TwilioProvider(WhatsAppProvider):
    def __init__(self, sid: str, token: str, from_number: str, to_number: str):
        try:
            from twilio.rest import Client
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install twilio to use the Twilio provider") from exc
        self.client, self.from_number, self.to_number = Client(sid, token), from_number, to_number

    def send_text(self, message: str) -> bool:
        return _retry(lambda: self.client.messages.create(body=message, from_=self.from_number, to=self.to_number))


class MetaCloudProvider(WhatsAppProvider):
    def __init__(self, token: str, phone_number_id: str, recipient: str):
        self.token, self.phone_number_id, self.recipient = token, phone_number_id, recipient

    def send_text(self, message: str) -> bool:
        try:
            import requests
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install requests to use Meta Cloud") from exc
        url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages"
        payload = {"messaging_product": "whatsapp", "to": self.recipient, "type": "text", "text": {"body": message}}
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        return _retry(lambda: requests.post(url, json=payload, headers=headers, timeout=20))

    def send_image(self, path: str | Path, caption: str) -> bool:
        try:
            import requests
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install requests to use Meta Cloud") from exc
        headers = {"Authorization": f"Bearer {self.token}"}
        media_url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/media"
        try:
            with Path(path).open("rb") as handle:
                response = requests.post(media_url, headers=headers, data={"messaging_product": "whatsapp", "type": "image/png"}, files={"file": handle}, timeout=30)
            response.raise_for_status()
            media_id = response.json()["id"]
            message_url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages"
            payload = {"messaging_product": "whatsapp", "to": self.recipient, "type": "image", "image": {"id": media_id, "caption": caption[:1024]}}
            response = requests.post(message_url, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=20)
            response.raise_for_status()
            return True
        except Exception:
            LOGGER.exception("Meta Cloud image upload failed; falling back to text")
            return self.send_text(caption)


def _retry(operation, attempts: int = 3) -> bool:
    for attempt in range(attempts):
        try:
            response = operation()
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            return True
        except Exception:
            LOGGER.exception("WhatsApp delivery failed (attempt %d/%d)", attempt + 1, attempts)
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    return False


def build_provider(settings: Settings) -> WhatsAppProvider:
    if not settings.section("mode").get("alerts_enabled", True):
        return LoggingProvider()
    provider = settings.section("alerts").get("provider", "twilio")
    secret = settings.secrets
    if provider == "twilio":
        required = [secret.twilio_account_sid, secret.twilio_auth_token, secret.twilio_whatsapp_from, secret.whatsapp_to]
        if not all(required):
            LOGGER.warning("Twilio credentials are incomplete; alerts will be logged locally")
            return LoggingProvider()
        return TwilioProvider(*required)
    if provider == "callmebot":
        if not secret.whatsapp_to or not secret.callmebot_api_key:
            LOGGER.warning("CallMeBot credentials are incomplete; alerts will be logged locally")
            return LoggingProvider()
        return CallMeBotProvider(secret.whatsapp_to, secret.callmebot_api_key)
    if provider == "meta_cloud":
        if not secret.meta_whatsapp_token or not secret.meta_phone_number_id or not secret.whatsapp_to:
            LOGGER.warning("Meta Cloud credentials are incomplete; alerts will be logged locally")
            return LoggingProvider()
        return MetaCloudProvider(secret.meta_whatsapp_token, secret.meta_phone_number_id, secret.whatsapp_to)
    raise ValueError(f"Unknown WhatsApp provider: {provider}")
