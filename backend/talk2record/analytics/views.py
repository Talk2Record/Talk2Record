from __future__ import annotations

import contextlib
from collections import Counter
from collections import defaultdict
from decimal import Decimal

from django.db.models import Count
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from talk2record.analytics.models import DailyMetric
from talk2record.analytics.serializers import DailyMetricSerializer
from talk2record.organizations.models import Membership
from talk2record.records.models import Record
from talk2record.records.models import RecordArtifact


def _presentation_status(status: str) -> str:
    if status in {Record.Status.TRANSCRIBED, Record.Status.STORED}:
        return "processed"
    if status == Record.Status.REVIEW:
        return "review"
    if status == Record.Status.FAILED:
        return "failed"
    return "processed"


class DailyMetricViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DailyMetricSerializer

    def get_queryset(self):
        return DailyMetric.objects.filter(
            organization__memberships__user=self.request.user,
        ).select_related("organization")


class DashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = request.user.current_organization
        if organization is None:
            membership = request.user.memberships.select_related("organization").first()
            organization = membership.organization if membership else None

        if organization is None:
            return Response({"metrics": [], "activities": []})

        records_queryset = Record.objects.filter(organization=organization)
        totals = records_queryset.aggregate(
            record_count=Count("id"),
            review_count=Count("id", filter=Q(status=Record.Status.REVIEW)),
            failed_count=Count("id", filter=Q(status=Record.Status.FAILED)),
        )
        active_users = Membership.objects.filter(
            organization=organization,
            status=Membership.Status.ACTIVE,
        ).count()

        recent_records = list(
            records_queryset.prefetch_related("artifacts").order_by("-created_at")[:5],
        )
        activities = []
        for record in recent_records:
            extraction = record.get_artifact("extraction")
            transcript = record.get_artifact("transcript")
            customer = (
                (extraction.content.get("customer_name") or "Unknown")
                if extraction
                else "Unknown"
            )
            snippet = (transcript.content.get("text") or "") if transcript else ""
            activities.append(
                {
                    "id": str(record.pk),
                    "customer": customer,
                    "transcriptSnippet": snippet or "Transcript not available yet.",
                    "status": _presentation_status(record.status),
                    "createdAt": record.created_at,
                },
            )

        # Revenue from extraction artifacts
        total_revenue = _sum_revenue_from_artifacts(organization)

        metrics = [
            {
                "label": "Voice notes processed",
                "value": str(totals["record_count"] or 0),
                "delta": f"{totals['record_count'] or 0} total records",
                "tone": "positive",
            },
            {
                "label": "Revenue captured",
                "value": str(total_revenue),
                "delta": "Live revenue from extracted records",
                "tone": "positive",
            },
            {
                "label": "Review queue",
                "value": str(totals["review_count"] or 0),
                "delta": f"{totals['failed_count'] or 0} failed records",
                "tone": "neutral",
            },
            {
                "label": "Active operators",
                "value": str(active_users),
                "delta": "Active workspace memberships",
                "tone": "neutral",
            },
        ]
        return Response({"metrics": metrics, "activities": activities})


class AnalyticsSnapshotView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = request.user.current_organization
        if organization is None:
            membership = request.user.memberships.select_related("organization").first()
            organization = membership.organization if membership else None

        if organization is None:
            return Response(
                {
                    "salesPerDay": [],
                    "salesPerProduct": [],
                    "revenueTrends": [],
                    "processingStats": [],
                    "heatmapSummary": [],
                },
            )

        daily_metrics = list(
            DailyMetric.objects.filter(organization=organization).order_by(
                "-metric_date",
            )[:7],
        )
        daily_metrics.reverse()
        sales_per_day = [
            {
                "label": metric.metric_date.strftime("%a"),
                "value": metric.records_created,
            }
            for metric in daily_metrics
        ]

        # Product counts from extraction artifacts
        record_ids = list(
            Record.objects.filter(organization=organization).values_list(
                "id",
                flat=True,
            ),
        )
        product_counts: Counter = Counter()
        for artifact in RecordArtifact.objects.filter(
            record_id__in=record_ids,
            key="extraction",
        ):
            product = artifact.content.get("product", "")
            if product:
                product_counts[product] += 1
        sales_per_product = [
            {"label": label, "value": value}
            for label, value in product_counts.most_common(5)
            if label
        ]

        # Revenue trends from extraction artifacts (by month)
        revenue_trends = _build_revenue_trends(record_ids)

        status_counts = Counter(
            Record.objects.filter(organization=organization).values_list(
                "status",
                flat=True,
            ),
        )
        total_status = sum(status_counts.values()) or 1
        processing_stats = [
            {
                "label": "Processed",
                "value": round(
                    (
                        status_counts.get(Record.Status.TRANSCRIBED, 0)
                        + status_counts.get(Record.Status.STORED, 0)
                    )
                    / total_status
                    * 100,
                ),
            },
            {
                "label": "Review",
                "value": round(
                    status_counts.get(Record.Status.REVIEW, 0) / total_status * 100,
                ),
            },
            {
                "label": "Failed",
                "value": round(
                    status_counts.get(Record.Status.FAILED, 0) / total_status * 100,
                ),
            },
        ]

        active_operators = Membership.objects.filter(
            organization=organization,
            status=Membership.Status.ACTIVE,
        ).count()
        heatmap_summary = [
            (
                f"{sum(metric.voice_processed for metric in daily_metrics)} "
                "voice notes tracked in recent metrics."
            ),
            (
                f"{len(sales_per_product)} product categories "
                "currently active in extracted records."
            ),
            (f"{active_operators} active operators contributing to the workspace."),
        ]

        return Response(
            {
                "salesPerDay": sales_per_day,
                "salesPerProduct": sales_per_product,
                "revenueTrends": revenue_trends,
                "processingStats": processing_stats,
                "heatmapSummary": heatmap_summary,
            },
        )


def _sum_revenue_from_artifacts(organization) -> Decimal:
    record_ids = list(
        Record.objects.filter(organization=organization).values_list("id", flat=True),
    )
    total = Decimal("0.00")
    for artifact in RecordArtifact.objects.filter(
        record_id__in=record_ids,
        key="extraction",
    ):
        with contextlib.suppress(Exception):
            total += Decimal(str(artifact.content.get("amount", "0") or "0"))
    return total


def _build_revenue_trends(record_ids: list) -> list:
    monthly: dict = defaultdict(Decimal)
    for artifact in RecordArtifact.objects.filter(
        record_id__in=record_ids,
        key="extraction",
    ).select_related("record"):
        month_label = artifact.record.created_at.strftime("%b")
        with contextlib.suppress(Exception):
            monthly[month_label] += Decimal(
                str(artifact.content.get("amount", "0") or "0"),
            )
    return [{"label": label, "value": float(val)} for label, val in monthly.items()]
