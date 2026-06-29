"""Upload d'une radio -> appel du service IA -> persistance -> réponse.

Django est la source de vérité unique : il dérive le diagnostic 3 classes,
stocke l'image normalisée, l'historique, et l'avis médecin.
"""
import base64

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .mapping import concordance, derive_diagnosis
from .models import Analysis
from .serializers import AnalysisSerializer


class AnalyzeView(APIView):
    """POST une image (DICOM/PNG) + un nom -> analyse IA, enregistrée."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "Aucun fichier 'file' fourni."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        analysis_name = (request.data.get("analysis_name") or "").strip()

        try:
            ai_resp = requests.post(
                f"{settings.AI_SERVICE_URL}/analyze",
                files={"file": (upload.name, upload.read(), upload.content_type)},
                timeout=300,
            )
        except requests.RequestException as exc:
            return Response(
                {"detail": f"Service IA injoignable : {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if ai_resp.status_code != 200:
            return Response(
                {"detail": "Erreur du service IA.", "ai": _safe_json(ai_resp)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payload = ai_resp.json()
        analysis = payload.get("analysis", {})
        diagnosis, confidence = derive_diagnosis(analysis)

        record = Analysis(
            user=request.user,
            filename=upload.name,
            analysis_name=analysis_name,
            diagnosis=diagnosis,
            confidence=confidence,
            anomaly_present=bool(analysis.get("anomaly_present")),
            severity=int(analysis.get("severity", 0) or 0),
            severity_label=analysis.get("severity_label", "none"),
            region=analysis.get("region"),
            result=analysis,
        )

        # On stocke le PNG normalisé renvoyé par l'IA (toujours affichable).
        png_b64 = payload.get("image_png_base64")
        if png_b64:
            record.image.save(
                f"radio_{upload.name.rsplit('.', 1)[0]}.png",
                ContentFile(base64.b64decode(png_b64)),
                save=False,
            )
        record.save()

        serialized = AnalysisSerializer(record, context={"request": request}).data
        # On renvoie aussi l'image base64 + le cercle pour l'affichage immédiat.
        return Response(
            {**serialized, "image_png_base64": png_b64},
            status=status.HTTP_201_CREATED,
        )


class AnalysisListView(ListAPIView):
    serializer_class = AnalysisSerializer

    def get_queryset(self):
        return Analysis.objects.filter(user=self.request.user)


class AnalysisDetailView(RetrieveUpdateDestroyAPIView):
    """GET (détail), PATCH (avis médecin), DELETE (suppression)."""

    serializer_class = AnalysisSerializer

    def get_queryset(self):
        return Analysis.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(doctor_recorded_at=timezone.now())


class StatsView(APIView):
    """KPI agrégés pour l'utilisateur connecté."""

    def get(self, request: Request):
        qs = Analysis.objects.filter(user=request.user)
        avec_avis = qs.exclude(doctor_diagnosis__isnull=True).exclude(
            doctor_diagnosis=""
        )

        concordants = sum(
            1
            for a in avec_avis
            if concordance(a.diagnosis, a.doctor_diagnosis)[0] == "Concordant"
        )
        nb_avis = avec_avis.count()

        return Response(
            {
                "total": qs.count(),
                "sain": qs.filter(diagnosis="Sain").count(),
                "malade": qs.filter(diagnosis="Malade").count(),
                "incertain": qs.filter(diagnosis="Incertain").count(),
                "avec_avis_medecin": nb_avis,
                "concordants": concordants,
                "taux_concordance": round(concordants / nb_avis * 100, 1)
                if nb_avis
                else None,
            }
        )


def _safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return resp.text[:500]
