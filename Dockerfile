# ============================================================
# assistant-radiologue-virtuel — Dockerfile
# ============================================================
# Deux services disponibles selon la CMD :
#   - API  : uvicorn api.main:app  (port 8000)
#   - App  : streamlit run app/streamlit_app.py (port 8501)
# ============================================================

# --- Stage 1 : builder (installation des dépendances) -------
FROM python:3.11-slim AS builder

WORKDIR /build

# Dépendances système nécessaires pour OpenCV, pydicom, torch…
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1 \
    git \
 && rm -rf /var/lib/apt/lists/*

# Copier uniquement les fichiers de dépendances d'abord
# → meilleur cache Docker si le code change mais pas les deps
COPY requirements.txt .

# Installer dans un dossier isolé pour le copy final
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt


# --- Stage 2 : image finale (légère) -----------------------
FROM python:3.11-slim AS runtime

LABEL maintainer="MC-Data-7A" \
      description="Assistant radiologue virtuel — prototype pédagogique EFREI"

WORKDIR /app

# Dépendances runtime uniquement (pas de build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1 \
 && rm -rf /var/lib/apt/lists/*

# Copier les packages installés depuis le builder
COPY --from=builder /install /usr/local

# Copier tout le code du projet
COPY . .

# Répertoires de données runtime (montables en volume)
RUN mkdir -p /app/data /app/eval/outputs /app/logs

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/.cache/huggingface \
    # Clé API à surcharger via --env ou .env au runtime
    HF_TOKEN="" \
    # Mode par défaut : toy (pas besoin de GPU ni de données réelles)
    EVAL_MODE=toy

# Ports exposés
EXPOSE 8000 8501

# CMD par défaut : API FastAPI
# Pour lancer l'app Streamlit à la place :
#   docker run ... streamlit run app/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
