from rest_framework import serializers

from .models import Analysis


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analysis
        fields = [
            "id",
            "filename",
            "anomaly_present",
            "severity",
            "severity_label",
            "region",
            "result",
            "created_at",
        ]
        read_only_fields = fields
