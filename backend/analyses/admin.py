from django.contrib import admin

from .models import Analysis


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ("filename", "user", "severity", "severity_label", "created_at")
    list_filter = ("severity_label", "anomaly_present")
    search_fields = ("filename", "region", "user__username")
