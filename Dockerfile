# ./Dockerfile
FROM python:3.11-slim

# Python env vars
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System dependencies (PostgreSQL, Chrome, OpenCV)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    libpq-dev \
    # Chrome/Webdriver dependencies
    libglib2.0-0 libnss3 libfontconfig1 libx11-6 libxext6 \
    libxfixes3 libxi6 libxrandr2 libxrender1 libcups2 libasound2 xdg-utils \
    # Extra chrome dependencies for Debian Trixie
    fonts-liberation libu2f-udev libxshmfence1 libatk1.0-0 \
    # PostgreSQL
    postgresql-client \
    # OpenCV dependencies
    libgl1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Chrome (compatible with Debian)
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && apt-get install -y --no-install-recommends ./google-chrome-stable_current_amd64.deb || \
    apt --fix-broken install -y && \
    rm google-chrome-stable_current_amd64.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Install python deps
COPY requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Download OCR / ML models during build
COPY download_models.py .
RUN python download_models.py

# Copy project source
COPY . .
