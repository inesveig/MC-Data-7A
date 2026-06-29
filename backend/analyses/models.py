from django.conf import settings
from django.db import models


class Analysis(models.Model):
    """Historique d'une analyse de radio par l'utilisateur (source de vérité)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analyses",
    )
    filename = models.CharField(max_length=255)
    # Nom libre donné par l'utilisateur pour retrouver l'analyse.
    analysis_name = models.CharField(max_length=255, blank=True, default="")

    # PNG normalisé renvoyé par l'IA, stocké pour l'affichage de l'historique.
    image = models.FileField(upload_to="radios/", null=True, blank=True)

    # --- Diagnostic 3 classes dérivé de la sortie IA (cf. mapping.py) ---
    diagnosis = models.CharField(max_length=20, default="Incertain")
    confidence = models.FloatField(default=0.0)

    # --- Sortie brute du service IA ---
    anomaly_present = models.BooleanField(default=False)
    severity = models.PositiveSmallIntegerField(default=0)
    severity_label = models.CharField(max_length=20, default="none")
    region = models.CharField(max_length=255, blank=True, null=True)
    # Analyse complète (findings, circle, explanation, recommendation, ...).
    result = models.JSONField(default=dict)

    # --- Avis médecin (saisi a posteriori) ---
    doctor_diagnosis = models.CharField(max_length=255, blank=True, null=True)
    doctor_notes = models.TextField(blank=True, null=True)
    doctor_recorded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} ({self.diagnosis}, sev={self.severity}) par {self.user}"
