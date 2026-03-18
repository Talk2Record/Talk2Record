from collections import Counter
from decimal import Decimal

from django.db.models import Count
from django.db.models import Q
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.views import APIView

from talk2record.analytics.models import DailyMetric
from talk2record.analytics.serializers import DailyMetricSerializer
from talk2record.organizations.models import Membership
from talk2record.records.models import Record


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
            total_revenue=Sum("amount"),
            review_count=Count("id", filter=Q(status=Record.Status.REVIEW)),
            failed_count=Count("id", filter=Q(status=Record.Status.FAILED)),
        )
        active_users = Membership.objects.filter(
            organization=organization,
            status=Membership.Status.ACTIVE,
        ).count()
        activities = [
            {
                "id": str(record.pk),
                "customer": record.customer_name,
                "transcriptSnippet": record.voice_transcript or "Transcript not available yet.",
                "status": _presentation_status(record.status),
                "createdAt": record.created_at,
            }
            for record in records_queryset.order_by("-created_at")[:5]
        ]
        metrics = [
            {
                "label": "Voice notes processed",
                "value": str(totals["record_count"] or 0),
                "delta": f"{totals['record_count'] or 0} total records",
                "tone": "positive",
            },
            {
                "label": "Revenue captured",
                "value": str(totals["total_revenue"] or Decimal("0")),
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
                }
            )

        daily_metrics = list(
            DailyMetric.objects.filter(organization=organization).order_by("-metric_date")[:7]
        )
        daily_metrics.reverse()
        sales_per_day = [
            {"label": metric.metric_date.strftime("%a"), "value": metric.records_created}
            for metric in daily_metrics
        ]

        product_counts = Counter(
            Record.objects.filter(organization=organization).values_list("product", flat=True)
        )
        sales_per_product = [
            {"label": label, "value": value}
            for label, value in product_counts.most_common(5)
            if label
        ]

        revenue_trends = [
            {"label": entry["month"].strftime("%b"), "value": float(entry["revenue"] or 0)}
            for entry in (
                Record.objects.filter(organization=organization)
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(revenue=Sum("amount"))
                .order_by("month")
            )
            if entry["month"] is not None
        ]

        status_counts = Counter(
            Record.objects.filter(organization=organization).values_list("status", flat=True)
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
                    * 100
                ),
            },
            {
                "label": "Review",
                "value": round(status_counts.get(Record.Status.REVIEW, 0) / total_status * 100),
            },
            {
                "label": "Failed",
                "value": round(status_counts.get(Record.Status.FAILED, 0) / total_status * 100),
            },
        ]

        heatmap_summary = [
            f"{sum(metric.voice_processed for metric in daily_metrics)} voice notes tracked in recent metrics.",
            f"{len(sales_per_product)} product categories currently active in extracted records.",
            f"{Membership.objects.filter(organization=organization, status=Membership.Status.ACTIVE).count()} active operators contributing to the workspace.",
        ]

        return Response(
            {
                "salesPerDay": sales_per_day,
                "salesPerProduct": sales_per_product,
                "revenueTrends": revenue_trends,
                "processingStats": processing_stats,
                "heatmapSummary": heatmap_summary,
            }
        )
