"""Tests du backend analyses : mapping, garde-fous de la vue, KPI, avis médecin.

Le service IA est *toujours* mocké ici : on teste la logique Django (dérivation
3 classes, robustesse de la vue, concordance), pas MedGemma.
"""
import base64
from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from .mapping import (
    DIAG_INCERTAIN,
    DIAG_MALADE,
    DIAG_SAIN,
    clamp_severity,
    concordance,
    derive_diagnosis,
)
from .models import Analysis


# --------------------------------------------------------------------------- #
# Logique pure : mapping IA -> 3 classes
# --------------------------------------------------------------------------- #
class MappingTests(APITestCase):
    def test_clamp_severity_borne_et_tolere_les_entrees_sales(self):
        self.assertEqual(clamp_severity(5), 5)
        self.assertEqual(clamp_severity("7"), 7)   # chaîne numérique
        self.assertEqual(clamp_severity(3.9), 3)   # flottant tronqué
        self.assertEqual(clamp_severity(-4), 0)    # borne basse
        self.assertEqual(clamp_severity(99), 10)   # borne haute
        self.assertEqual(clamp_severity("high"), 0)  # non numérique -> 0
        self.assertEqual(clamp_severity(None), 0)
        self.assertEqual(clamp_severity(""), 0)

    def test_derive_sain_quand_pas_anomalie(self):
        diag, conf = derive_diagnosis({"anomaly_present": False, "severity": 0})
        self.assertEqual(diag, DIAG_SAIN)
        self.assertEqual(conf, 1.0)

    def test_derive_incertain_pour_gravite_faible(self):
        diag, _ = derive_diagnosis({"anomaly_present": True, "severity": 2})
        self.assertEqual(diag, DIAG_INCERTAIN)

    def test_derive_malade_pour_gravite_elevee(self):
        diag, conf = derive_diagnosis({"anomaly_present": True, "severity": 8})
        self.assertEqual(diag, DIAG_MALADE)
        self.assertEqual(conf, 0.8)

    def test_derive_ne_plante_pas_sur_severity_non_numerique(self):
        diag, _ = derive_diagnosis({"anomaly_present": True, "severity": "grave"})
        # "grave" -> 0 -> pas d'anomalie exploitable -> Sain (pas de crash)
        self.assertEqual(diag, DIAG_SAIN)

    def test_concordance(self):
        self.assertEqual(concordance(DIAG_MALADE, "Malade"), ("Concordant", 100))
        self.assertEqual(concordance(DIAG_SAIN, "Malade"), ("Discordant", 0))
        self.assertEqual(
            concordance(DIAG_INCERTAIN, "Malade"),
            ("Non comparable (IA incertaine)", 50),
        )
        self.assertEqual(concordance(DIAG_MALADE, None), (None, None))


# --------------------------------------------------------------------------- #
# Vue d'analyse : auth, validation d'upload, proxy IA, persistance
# --------------------------------------------------------------------------- #
def _fake_ai_response(status_code=200, analysis=None, image_b64="cE5n"):
    """Fabrique un objet type `requests.Response` minimal pour mocker l'IA."""
    class _Resp:
        def __init__(self):
            self.status_code = status_code
            self._payload = {
                "analysis": analysis
                if analysis is not None
                else {
                    "anomaly_present": True,
                    "findings": ["Opacité"],
                    "region": "lobe inférieur droit",
                    "severity": 7,
                    "severity_label": "high",
                },
                "image_png_base64": image_b64,
            }
            self.text = "ai error"

        def json(self):
            return self._payload

    return _Resp()


class AnalyzeViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("demo", password="demo12345")
        self.url = "/api/analyses/analyze/"

    def _login(self):
        self.client.force_authenticate(user=self.user)

    def _png(self, name="radio.png"):
        return SimpleUploadedFile(name, b"fake-bytes", content_type="image/png")

    def test_requiert_authentification(self):
        resp = self.client.post(self.url, {"file": self._png()}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refuse_sans_fichier(self):
        self._login()
        resp = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refuse_extension_non_supportee(self):
        self._login()
        bad = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        resp = self.client.post(self.url, {"file": bad}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("analyses.views.requests.post")
    def test_analyse_ok_persiste_et_derive_diagnostic(self, mock_post):
        mock_post.return_value = _fake_ai_response()
        self._login()
        resp = self.client.post(
            self.url,
            {"file": self._png(), "analysis_name": "cas 1"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["diagnosis"], DIAG_MALADE)
        self.assertEqual(resp.data["severity"], 7)
        self.assertEqual(Analysis.objects.filter(user=self.user).count(), 1)

    @patch("analyses.views.requests.post")
    def test_severity_sale_ne_plante_pas_la_vue(self, mock_post):
        mock_post.return_value = _fake_ai_response(
            analysis={"anomaly_present": True, "severity": "high"}
        )
        self._login()
        resp = self.client.post(self.url, {"file": self._png()}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["severity"], 0)

    @patch("analyses.views.requests.post")
    def test_base64_corrompu_nempeche_pas_lenregistrement(self, mock_post):
        mock_post.return_value = _fake_ai_response(image_b64="!!not-base64!!")
        self._login()
        resp = self.client.post(self.url, {"file": self._png()}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    @patch("analyses.views.requests.post", side_effect=__import__("requests").RequestException("down"))
    def test_service_ia_injoignable_renvoie_502(self, _mock):
        self._login()
        resp = self.client.post(self.url, {"file": self._png()}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)


# --------------------------------------------------------------------------- #
# KPI et avis médecin
# --------------------------------------------------------------------------- #
class StatsAndReviewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("demo", password="demo12345")
        self.client.force_authenticate(user=self.user)

    def _make(self, diagnosis, severity=7, doctor=None):
        return Analysis.objects.create(
            user=self.user,
            filename="r.png",
            diagnosis=diagnosis,
            severity=severity,
            doctor_diagnosis=doctor,
        )

    def test_stats_compte_et_concordance(self):
        self._make(DIAG_MALADE, doctor="Malade")   # concordant
        self._make(DIAG_SAIN, doctor="Malade")     # discordant
        self._make(DIAG_INCERTAIN)                 # sans avis
        resp = self.client.get("/api/analyses/stats/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total"], 3)
        self.assertEqual(resp.data["avec_avis_medecin"], 2)
        self.assertEqual(resp.data["concordants"], 1)
        self.assertEqual(resp.data["taux_concordance"], 50.0)

    def test_stats_taux_none_sans_avis(self):
        self._make(DIAG_SAIN)
        resp = self.client.get("/api/analyses/stats/")
        self.assertIsNone(resp.data["taux_concordance"])

    def test_patch_avis_medecin_met_a_jour_concordance_et_date(self):
        a = self._make(DIAG_MALADE)
        resp = self.client.patch(
            f"/api/analyses/{a.id}/",
            {"doctor_diagnosis": "Malade", "doctor_notes": "confirmé"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["concordance_status"], "Concordant")
        self.assertIsNotNone(resp.data["doctor_recorded_at"])

    def test_un_user_ne_voit_pas_les_analyses_dun_autre(self):
        other = User.objects.create_user("autre", password="x")
        Analysis.objects.create(user=other, filename="o.png", diagnosis=DIAG_SAIN)
        resp = self.client.get("/api/analyses/")
        self.assertEqual(len(resp.data), 0)
