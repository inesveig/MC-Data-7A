from django.urls import path

from .views import AnalysisDetailView, AnalysisListView, AnalyzeView

urlpatterns = [
    path("", AnalysisListView.as_view(), name="analysis-list"),
    path("analyze/", AnalyzeView.as_view(), name="analyze"),
    path("<int:pk>/", AnalysisDetailView.as_view(), name="analysis-detail"),
]
