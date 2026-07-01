"""Tests de l'inscription et du profil utilisateur (JWT via simplejwt)."""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class RegisterViewTests(APITestCase):
    url = "/api/auth/register/"

    def test_inscription_reussie(self):
        resp = self.client.post(
            self.url,
            {"username": "alice", "password": "correcthorsebattery9", "email": "alice@example.com"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="alice").exists())
        self.assertEqual(resp.data["email"], "alice@example.com")
        self.assertNotIn("password", resp.data)

    def test_username_deja_pris_renvoie_409(self):
        User.objects.create_user(username="bob", password="correcthorsebattery9")
        resp = self.client.post(self.url, {"username": "bob", "password": "correcthorsebattery9"})
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("detail", resp.data)

    def test_username_ou_password_manquant_renvoie_400(self):
        resp = self.client.post(self.url, {"username": "", "password": "correcthorsebattery9"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        resp2 = self.client.post(self.url, {"username": "charlie", "password": ""})
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mot_de_passe_trop_faible_renvoie_400(self):
        resp = self.client.post(self.url, {"username": "dave", "password": "1234"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", resp.data)
        self.assertFalse(User.objects.filter(username="dave").exists())

    def test_mot_de_passe_uniquement_numerique_rejete(self):
        resp = self.client.post(self.url, {"username": "erin", "password": "20260701123456"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class MeViewTests(APITestCase):
    url = "/api/auth/me/"

    def setUp(self):
        self.user = User.objects.create_user(
            username="frank", password="correcthorsebattery9", email="frank@example.com"
        )

    def test_sans_authentification_renvoie_401(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_avec_authentification_renvoie_le_profil(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "frank")
        self.assertEqual(resp.data["email"], "frank@example.com")
