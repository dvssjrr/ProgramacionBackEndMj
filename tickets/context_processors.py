"""Datos comunes del alumno visibles en las páginas HTML."""

from django.conf import settings


def footer_details(request):
    """Expone nombre, sección y año configurados en el footer."""
    return {
        'STUDENT_FULL_NAME': settings.STUDENT_FULL_NAME,
        'STUDENT_SECTION': settings.STUDENT_SECTION,
        'STUDENT_YEAR': settings.STUDENT_YEAR,
    }