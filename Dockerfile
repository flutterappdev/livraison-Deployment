FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System dependencies (Chrome, PostgreSQL, OpenCV)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    libpq-dev \
    libglib2.0-0 libnss3 libfontconfig1 libx11-6 libxext6 \
    libxfixes3 libxi6 libxrandr2 libxrender1 libcups2 libasound2 xdg-utils \
    fonts-liberation libu2f-udev libxshmfence1 libatk1.0-0 \
    postgresql-client \
    libgl1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && apt-get install -y --no-install-recommends ./google-chrome-stable_current_amd64.deb || \
    apt --fix-broken install -y && \
    rm google-chrome-stable_current_amd64.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY download_models.py .
RUN python download_models.py

# Copy full project
COPY . .

# Start Django with Gunicorn on Railway
CMD ["gunicorn", "BLSSPAIN.wsgi:application", "--bind", "0.0.0.0:8000"]
