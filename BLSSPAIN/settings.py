"""
Django settings for BLSSPAIN project.
Optimized for Docker and environment variable-based configuration.
"""
import os
from pathlib import Path
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- CORE SETTINGS ---
# SECRET_KEY, DEBUG, and ALLOWED_HOSTS are read from environment variables

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("La variable d'environnement SECRET_KEY doit être définie.")

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS_STRING = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,bls.fortibtech.com')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'celery',
    'encrypted_model_fields',
    'django_countries',
    
    # Local apps
    'app.apps.BLSSpainConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Whitenoise Middleware for serving static files efficiently
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'app.middleware.OrganisationMiddleware',
]

ROOT_URLCONF = 'BLSSPAIN.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # If you have a global templates folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'BLSSPAIN.wsgi.application'


# --- DATABASE CONFIGURATION ---
# Reads database settings from environment variables. Falls back to SQLite for local dev.
DB_ENGINE = os.getenv('SQL_ENGINE')
if DB_ENGINE:
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': os.getenv('SQL_DATABASE'),
            'USER': os.getenv('SQL_USER'),
            'PASSWORD': os.getenv('SQL_PASSWORD'),
            'HOST': os.getenv('SQL_HOST'),
            'PORT': int(os.getenv('SQL_PORT', 5432)),
        }
    }
else:
    # Default to SQLite if no environment variables are set
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# --- PASSWORD VALIDATION ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# --- STATIC & MEDIA FILES ---
# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'app' / 'static',
]
# For serving static files in production with Whitenoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User-uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# --- CELERY & REDIS CONFIGURATION ---
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6380/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True


# --- ENCRYPTION KEY CONFIGURATION ---
key_str = os.getenv('FIELD_ENCRYPTION_KEY')
if not key_str:
    if DEBUG:
        print("ATTENTION: FIELD_ENCRYPTION_KEY n'est pas définie. Utilisation d'une clé temporaire. Les données chiffrées ne seront pas persistantes après un redémarrage.")
        FIELD_ENCRYPTION_KEY = Fernet.generate_key()
    else:
        raise ImproperlyConfigured("La variable d'environnement FIELD_ENCRYPTION_KEY doit être définie en production.")
else:
    try:
        FIELD_ENCRYPTION_KEY = key_str.encode('utf-8')
        Fernet(FIELD_ENCRYPTION_KEY) # Validate the key
    except Exception as e:
        raise ImproperlyConfigured(f"La valeur de FIELD_ENCRYPTION_KEY n'est pas une clé Fernet valide. Erreur: {e}")


# --- CUSTOM PROJECT SETTINGS ---

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/'

# Admin site customization
ADMIN_SITE_HEADER = "BLS Rapido"
ADMIN_SITE_TITLE = "BLS Rapido Portal"
ADMIN_INDEX_TITLE = "Gestion des rendez-vous"

# VISA SERVICES CONFIGURATION
VISA_SERVICES = {
    'blsspain': {
        'base_url': 'https://www.blsspainmorocco.net',
        'timeout': 60, # Increased timeout for containerized environments
    },
    'tlsfrance': {
        'base_url': 'https://france-visas.gouv.fr',
        'timeout': 60,
    },
    'vfsglobal': {
        'base_url': 'https://visa.vfsglobal.com',
        'timeout': 60,
    }
}
CAPTCHA_API_KEY = os.getenv('CAPTCHA_API_KEY') # Read from env, can be None


# --- SECURITY SETTINGS ---
# These settings are more robust for production when DEBUG=False

if not DEBUG:
    SECURE_HSTS_SECONDS = 2592000 # 30 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    # Read trusted origins for CSRF from environment variable
    CSRF_TRUSTED_ORIGINS_STRING = os.getenv('CSRF_TRUSTED_ORIGINS', '')
    CSRF_TRUSTED_ORIGINS = [url.strip() for url in CSRF_TRUSTED_ORIGINS_STRING.split(',') if url.strip()]
else:
    # For local development with Docker
    CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

# Recommended cookie settings for better security
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax' # 'Strict' can be too restrictive
CSRF_COOKIE_SAMESITE = 'Lax'

# For running behind a reverse proxy (like Nginx, Traefik, etc.)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Logging (optional but recommended)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO' if not DEBUG else 'DEBUG',
    },
}