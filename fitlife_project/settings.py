"""Configuración independiente de FitLife."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("FITLIFE_DEBUG", "false").lower() in {"1", "true", "yes"}
SECRET_KEY = os.environ.get("FITLIFE_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Define FITLIFE_SECRET_KEY antes de iniciar FitLife.")
    SECRET_KEY = "django-insecure-solo-desarrollo-fitlife"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("FITLIFE_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "fitlife",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "fitlife_project.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "fitlife_templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "fitlife_project.wsgi.application"
ASGI_APPLICATION = "fitlife_project.asgi.application"

DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("FITLIFE_DB_NAME", "fitlife_db"),
    "USER": os.environ.get("FITLIFE_DB_USER", "fitlife_user"),
    "PASSWORD": os.environ.get("FITLIFE_DB_PASSWORD", ""),
    "HOST": os.environ.get("FITLIFE_DB_HOST", "localhost"),
    "PORT": os.environ.get("FITLIFE_DB_PORT", "5432"),
}}
AUTH_USER_MODEL = "fitlife.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
LANGUAGE_CODE = "es"
TIME_ZONE = os.environ.get("FITLIFE_TIME_ZONE", "America/Santiago")
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "fitlife_static"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/login/"
CSRF_FAILURE_VIEW = "fitlife.pages.csrf_failure"
LOGIN_REDIRECT_URL = "/panel/"
LOGOUT_REDIRECT_URL = "/"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = os.environ.get("FITLIFE_HTTPS", "false").lower() == "true"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_SSL_REDIRECT = SESSION_COOKIE_SECURE
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if SESSION_COOKIE_SECURE else None
CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.environ.get("FITLIFE_CSRF_TRUSTED_ORIGINS", "").split(",") if v.strip()]
