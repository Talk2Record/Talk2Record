from __future__ import annotations

import logging

import requests
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from talk2record.whatsapp.client import WhatsAppCloudClient
from talk2record.whatsapp.client import WhatsAppCloudClientError
from talk2record.whatsapp.config import load_whatsapp_cloud_settings

logger = logging.getLogger(__name__)


def _test_whatsapp() -> tuple[bool, str]:
    settings = load_whatsapp_cloud_settings()
    if settings is None:
        return False, str(_("WhatsApp settings are missing or disabled."))
    if not settings.access_token.strip():
        return False, str(_("No Graph access token configured."))
    try:
        data = WhatsAppCloudClient(settings).debug_token()
    except WhatsAppCloudClientError as exc:
        return False, str(exc)
    data_ok = data.get("data", {})
    is_valid = data_ok.get("is_valid")
    app_id = data_ok.get("app_id", "")
    if is_valid is True:
        return True, str(_("Graph accepted the access token (app_id=%s).") % app_id)
    return False, str(_("Token debug response: %s") % data)


def test_whatsapp_connection_view(request):
    if request.method != "POST":
        return redirect(reverse("admin:index"))
    ok, detail = _test_whatsapp()
    msg = f"{_('WhatsApp Cloud')}: {detail}"
    if ok:
        messages.success(request, msg)
    else:
        messages.warning(request, msg)
    return redirect(reverse("admin:index"))
