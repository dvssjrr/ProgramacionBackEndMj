#!/usr/bin/env python
"""Herramienta de línea de comandos para administrar el proyecto Django."""
import os
import sys


def main():
    """Configura Django y ejecuta el comando solicitado."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            'No se pudo importar Django. Comprueba que esté instalado y disponible '
            'en PYTHONPATH, y que el entorno virtual esté activado.'
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
