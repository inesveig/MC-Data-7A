"""Upload d'une radio -> appel du service IA -> persistance -> réponse."""
import requests
from django.conf import settings
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Analysis
from .serializers import AnalysisSerializer


class AnalyzeView(APIView):
    """POST une image (DICOM/PNG) -> renvoie l'analyse et l'enregistre."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "Aucun fichier 'file' fourni."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        record = Analysis.objects.create(
            user=request.user,
            filename=upload.name,
            anomaly_present=bool(analysis.get("anomaly_present")),
            severity=int(analysis.get("severity", 0) or 0),
            severity_label=analysis.get("severity_label", "none"),
            region=analysis.get("region"),
            # On stocke l'analyse complète, pas l'image (trop lourde en base).
            result=analysis,
        )

        # On renvoie au front l'analyse + l'image convertie pour l'affichage.
        return Response(
            {"id": record.id, **payload}, status=status.HTTP_201_CREATED
        )


class AnalysisListView(ListAPIView):
    serializer_class = AnalysisSerializer

    def get_queryset(self):
        return Analysis.objects.filter(user=self.request.user)


class AnalysisDetailView(RetrieveAPIView):
    serializer_class = AnalysisSerializer

    def get_queryset(self):
        return Analysis.objects.filter(user=self.request.user)


def _safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return resp.text[:500]
