from __future__ import annotations

import logging

import requests
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from talk2record.billing.stripe_runtime import get_stripe_secret_plaintext

logger = logging.getLogger(__name__)


def _test_stripe() -> tuple[bool, str]:
    secret = get_stripe_secret_plaintext() or ""
    if not secret.strip():
        return False, str(_("No Stripe secret key stored or Stripe settings disabled."))
    try:
        resp = requests.get(
            "https://api.stripe.com/v1/balance",
            auth=(secret.strip(), ""),
            timeout=15,
        )
    except requests.RequestException as exc:
        logger.warning("Stripe credential test failed: %s", exc)
        return False, str(_("Network error: %s") % exc)
    if resp.status_code == 200:
        return True, str(_("Stripe API accepted the secret key."))
    return False, str(_("Stripe HTTP %(status)s: %(body)s")) % {
        "status": resp.status_code,
        "body": resp.text[:300],
    }


def test_stripe_connection_view(request):
    if request.method != "POST":
        return redirect(reverse("admin:index"))
    ok, detail = _test_stripe()
    msg = f"{_('Stripe')}: {detail}"
    if ok:
        messages.success(request, msg)
    else:
        messages.warning(request, msg)
    return redirect(reverse("admin:index"))
