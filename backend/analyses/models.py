from django.conf import settings
from django.db import models


class Analysis(models.Model):
    """Historique d'une analyse de radio par l'utilisateur."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analyses",
    )
    filename = models.CharField(max_length=255)
    anomaly_present = models.BooleanField(default=False)
    severity = models.PositiveSmallIntegerField(default=0)
    severity_label = models.CharField(max_length=20, default="none")
    region = models.CharField(max_length=255, blank=True, null=True)
    # Sortie complète du service IA (findings, circle, explanation, ...)
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} (sev={self.severity}) par {self.user}"
