from http import HTTPStatus

import pytest
from django.urls import reverse

from talk2record.analytics.services import AnalyticsService


@pytest.mark.django_db
def test_event_and_daily_metric_str(organization, daily_metric):
    event = AnalyticsService.track_event(
        name="record_stored",
        category="records",
        organization=organization,
        properties={"count": 1},
    )

    assert str(event) == "record_stored"
    assert str(daily_metric) == f"{organization.name} @ {daily_metric.metric_date}"


@pytest.mark.django_db
def test_analytics_service_persists_properties(organization):
    event = AnalyticsService.track_event(
        name="legal_documents_accepted",
        category="legal",
        organization=organization,
        properties={"count": 2},
    )

    assert event.properties == {"count": 2}


@pytest.mark.django_db
def test_analytics_admin_pages(admin_client, daily_metric):
    urls = [
        reverse("admin:analytics_event_changelist"),
        reverse("admin:analytics_dailymetric_changelist"),
    ]

    for url in urls:
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK
