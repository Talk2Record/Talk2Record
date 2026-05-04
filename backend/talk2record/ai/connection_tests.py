from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from talk2record.ai.models import AITask
from talk2record.ai.resolver import resolve


def _test_ai() -> tuple[bool, str]:
    """Ping the active chat provider with a minimal extraction request.

    Uses the same resolution path as production (``resolve(EXTRACTION)`` →
    ``build_chat_provider().extract(...)``), so a success means credentials,
    base URL, and model id work against the remote API. The ``mock`` provider
    answers locally without HTTP.
    """

    resolution = resolve(task=AITask.EXTRACTION)
    if resolution is None:
        return False, str(
            _(
                "No active chat AI provider or model is configured. "
                "Add an AI provider (category: chat), set it active, "
                "enter the API key, and ensure default model or an extraction task binding exists.",
            ),
        )

    if resolution.provider_slug != "mock" and not (resolution.api_key or "").strip():
        return False, str(
            _("Active chat provider has no API key. Save one in Django admin."),
        )

    ping_transcript = str(
        _(
            'Return only valid JSON with keys customer_name, product, quantity, amount, currency, '
            'payment_method — use empty strings and 0 where unknown. For this test set product to "ping".',
        ),
    )
    try:
        provider = resolution.build_chat_provider()
        result = provider.extract(
            transcript=ping_transcript,
            context={},
            prompt_version="admin-connection-test",
        )
    except Exception as exc:  # noqa: BLE001 — surface any transport/API error to staff.
        return False, f"{type(exc).__name__}: {exc}"

    if resolution.provider_slug == "mock":
        return True, str(
            _("Mock provider responded locally (no remote HTTP). Model: %(model)s.")
            % {"model": result.model},
        )

    return True, str(
        _("Remote AI responded. Provider=%(provider)s model=%(model)s.")
        % {"provider": result.provider, "model": result.model},
    )


def test_ai_connection_view(request):
    if request.method != "POST":
        return redirect(reverse("admin:index"))
    ok, detail = _test_ai()
    msg = f"{_('AI')}: {detail}"
    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect(reverse("admin:index"))
