from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from talk2record.ai.runtime import get_ai_credential_plaintext


def _test_ai() -> tuple[bool, str]:
    secret = get_ai_credential_plaintext() or ""
    if not secret.strip():
        return False, str(_("No AI API credential stored or AI settings disabled."))
    return True, str(_("AI credential is present (provider-specific live calls are not executed)."))


def test_ai_connection_view(request):
    if request.method != "POST":
        return redirect(reverse("admin:index"))
    ok, detail = _test_ai()
    msg = f"{_('AI')}: {detail}"
    if ok:
        messages.success(request, msg)
    else:
        messages.warning(request, msg)
    return redirect(reverse("admin:index"))
