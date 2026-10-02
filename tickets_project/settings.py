"""Configuración del proyecto Tickets."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Ruta principal del proyecto, usada para localizar plantillas y recursos.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


# Ajustes locales de desarrollo; cambia SECRET_KEY y DEBUG antes de publicar.

# Clave interna de Django; debe cambiarse antes de publicar en producción.
SECRET_KEY = 'django-insecure-gpug60+5#kh3+pz($^dc0()c3)!0s$rhvbgzx)+-g(7c)8tx#m'

# DEBUG solo se activa explícitamente desde .env.
DEBUG = os.getenv('DEBUG', 'false').strip().lower() in {'1', 'true', 'yes'}

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']


# Aplicaciones instaladas: API de tickets, DRF y componentes de Django.

INSTALLED_APPS = [
    'tickets.apps.TicketsConfig',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'drf_spectacular',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tickets_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'tickets.context_processors.footer_details',
            ],
        },
    },
]

WSGI_APPLICATION = 'tickets_project.wsgi.application'


# PostgreSQL almacena los eventos, carritos y órdenes del sistema.
# Las credenciales se inyectan mediante variables de entorno.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'ticketing'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Conserva las migraciones ya aplicadas con el label original de la app.
MIGRATION_MODULES = {'ticketing': 'tickets.migrations'}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'TOKEN_OBTAIN_SERIALIZER': 'tickets.serializers.RoleTokenObtainPairSerializer',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Tickets API',
    'DESCRIPTION': 'API de eventos, reservas persistentes y venta de entradas.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

STUDENT_FULL_NAME = os.getenv('STUDENT_FULL_NAME', 'Nombre Completo del Estudiante')
STUDENT_SECTION = os.getenv('STUDENT_SECTION', 'Sección')
STUDENT_YEAR = os.getenv('STUDENT_YEAR', '2026')


# Reglas mínimas para las contraseñas de cuentas locales.

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Idioma y zona horaria usados por fechas y formatos.

LANGUAGE_CODE = 'es'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# URL base para los recursos estáticos del proyecto.

STATIC_URL = 'static/'


