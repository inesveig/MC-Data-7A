from rest_framework import serializers

from .mapping import concordance
from .models import Analysis


class AnalysisSerializer(serializers.ModelSerializer):
    """Lecture d'une analyse + écriture de l'avis médecin uniquement."""

    image_url = serializers.SerializerMethodField()
    concordance_status = serializers.SerializerMethodField()
    concordance_pct = serializers.SerializerMethodField()

    class Meta:
        model = Analysis
        fields = [
            "id",
            "filename",
            "analysis_name",
            "image_url",
            "diagnosis",
            "confidence",
            "anomaly_present",
            "severity",
            "severity_label",
            "region",
            "result",
            "doctor_diagnosis",
            "doctor_notes",
            "doctor_recorded_at",
            "concordance_status",
            "concordance_pct",
            "created_at",
        ]
        # Tout est en lecture seule sauf l'avis médecin (saisi via PATCH).
        read_only_fields = [
            f for f in fields if f not in ("doctor_diagnosis", "doctor_notes")
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url

    def get_concordance_status(self, obj):
        return concordance(obj.diagnosis, obj.doctor_diagnosis)[0]

    def get_concordance_pct(self, obj):
        return concordance(obj.diagnosis, obj.doctor_diagnosis)[1]
