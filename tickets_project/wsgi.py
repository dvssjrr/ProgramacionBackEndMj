"""Punto de entrada WSGI para servir Tickets."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')

application = get_wsgi_application()
