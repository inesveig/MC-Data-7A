from django.contrib import admin

from .models import Analysis


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "filename",
        "user",
        "diagnosis",
        "confidence",
        "severity",
        "doctor_diagnosis",
        "created_at",
    )
    list_filter = ("diagnosis", "severity_label", "anomaly_present")
    search_fields = ("filename", "analysis_name", "region", "user__username")
