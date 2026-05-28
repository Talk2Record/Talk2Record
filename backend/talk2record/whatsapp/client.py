from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

import requests

if TYPE_CHECKING:
    from talk2record.whatsapp.config import WhatsAppCloudSettings

logger = logging.getLogger(__name__)

_GRAPH_HOST = "https://graph.facebook.com"


class WhatsAppCloudClientError(Exception):
    """Raised when the client is misconfigured or the Graph API returns an error."""


class WhatsAppCloudClient:
    """
    Minimal WhatsApp Cloud / Graph API client aligned with the official
    Postman collection.
    Paths follow ``https://graph.facebook.com/{{Version}}/...``.
    """

    def __init__(self, settings: WhatsAppCloudSettings, *, timeout: int = 30) -> None:
        self._settings = settings
        self._timeout = timeout

    def _require_token(self) -> str:
        token = self._settings.access_token.strip()
        if not token:
            msg = "WhatsApp Graph access token is not configured on the integration."
            raise WhatsAppCloudClientError(msg)
        return token

    def _url(self, *path_segments: str) -> str:
        version = self._settings.graph_api_version.strip().strip("/")
        parts = "/".join(str(p).strip("/") for p in path_segments if str(p).strip())
        return f"{_GRAPH_HOST}/{version}/{parts}"

    def _request(
        self,
        method: str,
        *path_segments: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = self._require_token()
        url = self._url(*path_segments)
        headers = {"Authorization": f"Bearer {token}"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        resp = requests.request(
            method,
            url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=self._timeout,
        )
        try:
            data = resp.json()
        except ValueError:
            data = {}
        if not resp.ok:
            logger.warning(
                "WhatsApp Graph API error %s %s: %s",
                method,
                url,
                resp.text[:500],
            )
            msg = f"Graph API {resp.status_code}: {data or resp.text[:200]}"
            raise WhatsAppCloudClientError(msg)
        if not isinstance(data, dict):
            return {"data": data}
        return data

    # --- Get Started / WABA (Postman: Get Started, WhatsApp Business Accounts) ---

    def subscribe_waba(self, waba_id: str | None = None) -> dict[str, Any]:
        wid = (waba_id or self._settings.waba_id).strip()
        if not wid:
            msg = "waba_id is not configured on the integration."
            raise WhatsAppCloudClientError(
                msg,
            )
        return self._request("POST", wid, "subscribed_apps")

    def list_waba_phone_numbers(self, waba_id: str | None = None) -> dict[str, Any]:
        wid = (waba_id or self._settings.waba_id).strip()
        if not wid:
            msg = "waba_id is not configured on the integration."
            raise WhatsAppCloudClientError(
                msg,
            )
        return self._request("GET", wid, "phone_numbers")

    def get_waba(self, waba_id: str | None = None) -> dict[str, Any]:
        wid = (waba_id or self._settings.waba_id).strip()
        if not wid:
            msg = "waba_id is not configured on the integration."
            raise WhatsAppCloudClientError(
                msg,
            )
        return self._request("GET", wid)

    def owned_wabas(self, business_id: str | None = None) -> dict[str, Any]:
        bid = (business_id or self._settings.business_id).strip()
        if not bid:
            msg = "business_id is not configured on the integration."
            raise WhatsAppCloudClientError(
                msg,
            )
        return self._request("GET", bid, "owned_whatsapp_business_accounts")

    def shared_wabas(self, business_id: str | None = None) -> dict[str, Any]:
        bid = (business_id or self._settings.business_id).strip()
        if not bid:
            msg = "business_id is not configured on the integration."
            raise WhatsAppCloudClientError(
                msg,
            )
        return self._request("GET", bid, "client_whatsapp_business_accounts")

    # --- Phone registration (Postman: Registration, Phone Numbers) ---

    def register_phone(
        self,
        pin: str,
        phone_number_id: str | None = None,
    ) -> dict[str, Any]:
        pid = (phone_number_id or self._settings.phone_number_id).strip()
        if not pid:
            msg = "phone_number_id is not configured on the integration."
            raise WhatsAppCloudClientError(
                msg,
            )
        body = {"messaging_product": "whatsapp", "pin": pin}
        return self._request("POST", pid, "register", json_body=body)

    def deregister_phone(self, phone_number_id: str | None = None) -> dict[str, Any]:
        pid = (phone_number_id or self._settings.phone_number_id).strip()
        if not pid:
            msg = "phone_number_id is not configured on the integration."
            raise WhatsAppCloudClientError(
                msg,
            )
        return self._request("POST", pid, "deregister")

    def get_phone_number(self, phone_number_id: str | None = None) -> dict[str, Any]:
        pid = (phone_number_id or self._settings.phone_number_id).strip()
        if not pid:
            msg = "phone_number_id is not configured on the integration."
            raise WhatsAppCloudClientError(
                msg,
            )
        return self._request("GET", pid)

    # --- Messaging (Postman: Send messages) ---

    def send_message(
        self,
        payload: dict[str, Any],
        phone_number_id: str | None = None,
    ) -> dict[str, Any]:
        pid = (phone_number_id or self._settings.phone_number_id).strip()
        if not pid:
            msg = "phone_number_id is not configured on the integration."
            raise WhatsAppCloudClientError(
                msg,
            )
        return self._request("POST", pid, "messages", json_body=payload)

    def send_template_message(
        self,
        to_e164: str,
        template_name: str = "hello_world",
        language_code: str = "en_US",
        phone_number_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "to": to_e164,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        return self.send_message(payload, phone_number_id=phone_number_id)

    # --- Debug (Postman: Debug Access Token) ---

    def debug_token(self, input_token: str | None = None) -> dict[str, Any]:
        token = (input_token or self._settings.access_token).strip()
        if not token:
            msg = "No token to debug."
            raise WhatsAppCloudClientError(msg)
        return self._request("GET", "debug_token", params={"input_token": token})
