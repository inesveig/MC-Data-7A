import os

import requests

API_BASE_URL = os.getenv("DJANGO_API_URL", "http://localhost:8000/api/auth")


def register(username: str, password: str, email: str = ""):
    try:
        response = requests.post(
            f"{API_BASE_URL}/register/",
            json={"username": username, "password": password, "email": email},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        return False, "Impossible de contacter le serveur Django. Est-il bien lancé (port 8000) ?"

    if response.status_code == 201:
        return True, "Compte créé avec succès. Tu peux maintenant te connecter."
    if response.status_code == 409:
        return False, "Ce nom d'utilisateur existe déjà."
    if response.status_code == 400:
        detail = response.json().get("detail", "Champs invalides.")
        return False, detail
    return False, f"Erreur inattendue ({response.status_code})."


def login(username: str, password: str):
    try:
        response = requests.post(
            f"{API_BASE_URL}/login/",
            json={"username": username, "password": password},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        return False, "Impossible de contacter le serveur Django. Est-il bien lancé (port 8000) ?"

    if response.status_code == 200:
        return True, response.json()
    return False, "Nom d'utilisateur ou mot de passe incorrect."


def get_me(access_token: str):
    try:
        response = requests.get(
            f"{API_BASE_URL}/me/",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        return None

    if response.status_code == 200:
        return response.json()
    return None


def refresh_access_token(refresh_token: str):
    try:
        response = requests.post(
            f"{API_BASE_URL}/refresh/",
            json={"refresh": refresh_token},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        return None

    if response.status_code == 200:
        return response.json().get("access")
    return None