from django.urls import path

from .views import (
    AnalysisDetailView,
    AnalysisListView,
    AnalyzeView,
    StatsView,
)

urlpatterns = [
    path("", AnalysisListView.as_view(), name="analysis-list"),
    path("analyze/", AnalyzeView.as_view(), name="analyze"),
    path("stats/", StatsView.as_view(), name="analysis-stats"),
    path("<int:pk>/", AnalysisDetailView.as_view(), name="analysis-detail"),
]
