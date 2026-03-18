from rest_framework import serializers

from talk2record.analytics.models import DailyMetric


class DailyMetricSerializer(serializers.ModelSerializer[DailyMetric]):
    class Meta:
        model = DailyMetric
        fields = [
            "id",
            "metric_date",
            "voice_processed",
            "records_created",
            "revenue",
            "feature_usage",
            "active_users",
        ]
