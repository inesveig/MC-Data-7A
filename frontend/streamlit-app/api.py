"""Client de l'API Django : Django est la source de vérité unique.

Toutes les analyses, l'historique, l'avis médecin et les stats passent par
le backend Django (qui appelle lui-même le service IA / MedGemma).
"""
import os

import requests

API_ROOT = os.getenv("DJANGO_API_ROOT", "http://localhost:8000/api")
TIMEOUT = 300  # l'analyse IA peut être longue (modèle réel)

_CONN_ERR = "Impossible de contacter le serveur Django. Est-il lancé (port 8000) ?"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def analyze(token: str, file_bytes: bytes, filename: str, analysis_name: str):
    """Envoie la radio au backend -> (ok, données|message)."""
    try:
        resp = requests.post(
            f"{API_ROOT}/analyses/analyze/",
            headers=_headers(token),
            files={"file": (filename, file_bytes)},
            data={"analysis_name": analysis_name},
            timeout=TIMEOUT,
        )
    except requests.exceptions.ConnectionError:
        return False, _CONN_ERR
    except requests.exceptions.RequestException as exc:
        return False, f"Erreur réseau : {exc}"

    if resp.status_code == 201:
        return True, resp.json()
    if resp.status_code == 401:
        return False, "Session expirée, reconnecte-toi."
    return False, _detail(resp)


def list_analyses(token: str):
    try:
        resp = requests.get(
            f"{API_ROOT}/analyses/", headers=_headers(token), timeout=30
        )
    except requests.exceptions.ConnectionError:
        return False, _CONN_ERR
    if resp.status_code == 200:
        return True, resp.json()
    return False, _detail(resp)


def get_stats(token: str):
    try:
        resp = requests.get(
            f"{API_ROOT}/analyses/stats/", headers=_headers(token), timeout=30
        )
    except requests.exceptions.ConnectionError:
        return False, _CONN_ERR
    if resp.status_code == 200:
        return True, resp.json()
    return False, _detail(resp)


def set_doctor_opinion(token: str, analysis_id: int, diagnosis: str, notes: str):
    try:
        resp = requests.patch(
            f"{API_ROOT}/analyses/{analysis_id}/",
            headers=_headers(token),
            json={"doctor_diagnosis": diagnosis, "doctor_notes": notes},
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        return False, _CONN_ERR
    if resp.status_code == 200:
        return True, resp.json()
    return False, _detail(resp)


def delete_analysis(token: str, analysis_id: int):
    try:
        resp = requests.delete(
            f"{API_ROOT}/analyses/{analysis_id}/",
            headers=_headers(token),
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        return False, _CONN_ERR
    if resp.status_code in (200, 204):
        return True, None
    return False, _detail(resp)


def _detail(resp) -> str:
    try:
        return resp.json().get("detail", f"Erreur ({resp.status_code}).")
    except Exception:
        return f"Erreur ({resp.status_code})."
