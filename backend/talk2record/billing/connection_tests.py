"""Admin-side connectivity check for the Paddle integration.

Wired into the Unfold dashboard ("Test Paddle" button) and the URL
``admin_test_paddle_connection``.
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from talk2record.billing.paddle_service import PaddleBillingService

logger = logging.getLogger(__name__)


def test_paddle_connection_view(request):
    if request.method != "POST":
        return redirect(reverse("admin:index"))
    ok, detail = PaddleBillingService().test_credentials()
    msg = f"{_('Paddle')}: {detail}"
    if ok:
        messages.success(request, msg)
    else:
        messages.warning(request, msg)
    return redirect(reverse("admin:index"))
