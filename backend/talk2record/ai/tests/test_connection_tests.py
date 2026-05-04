from __future__ import annotations

import pytest

from talk2record.ai.connection_tests import _test_ai
from talk2record.ai.models import AICategory
from talk2record.ai.models import AIProvider
from talk2record.ai.models import AITask
from talk2record.ai.models import AITaskBinding


@pytest.mark.django_db
def test_ai_connection_test_uses_mock_without_http():
    AIProvider.objects.create(
        name="Mock chat",
        slug="mock",
        category=AICategory.CHAT,
        models_available=["mock-extractor-v1"],
        default_model="mock-extractor-v1",
        is_active=True,
    )
    AITaskBinding.objects.create(
        task=AITask.EXTRACTION,
        category=AICategory.CHAT,
        model="mock-extractor-v1",
    )
    ok, detail = _test_ai()
    assert ok is True
    assert "mock" in detail.lower()
