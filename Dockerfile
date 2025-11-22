# ./Dockerfile
FROM python:3.11-slim

# Variables d'environnement pour Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Dépendances système (y compris pour PostgreSQL et Chrome)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    libpq-dev \
    # Dépendances pour Chrome/Webdriver
    libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libx11-6 libxext6 \
    libxfixes3 libxi6 libxrandr2 libxrender1 libcups2 libasound2 xdg-utils \
    # Ajout de postgresql-client pour pg_isready
    postgresql-client \
    # --- SOLUTION : DÉPENDANCES POUR OPENCV/KERAS-OCR ---
    libgl1-mesa-glx \
    libglib2.0-0 \
    # ---------------------------------------------------
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Installer Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update && apt-get install -y --no-install-recommends ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Optionally set proxy environment variables if needed
# ENV HTTP_PROXY=http://your-proxy:port
# ENV HTTPS_PROXY=http://your-proxy:port
# ENV NO_PROXY=localhost,127.0.0.1

# Copier les requirements et installer les dépendances Python
COPY requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# --- SOLUTION : PRÉ-TÉLÉCHARGEMENT DES MODÈLES ---
# Copier le script de téléchargement
COPY download_models.py .
# Exécuter le script pour télécharger les modèles DANS l'image
RUN python download_models.py
# ------------------------------------------------

# Copier le reste du code source
COPY . .