"""Permisos por rol para el catálogo y las operaciones de organizador."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_master(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def is_organizer(user):
    """Reconoce staff y miembros del grupo Organizador."""
    return bool(
        user and user.is_authenticated
        and (is_master(user) or user.is_staff or user.groups.filter(name='Organizador').exists())
    )


class IsOrganizer(BasePermission):
    def has_permission(self, request, view):
        """Autoriza usuarios staff o integrantes del grupo Organizador."""
        return is_organizer(request.user)


class PublicReadOrganizerWrite(BasePermission):
    def has_permission(self, request, view):
        """Permite lectura pública y restringe escrituras a organizadores."""
        return request.method in SAFE_METHODS or is_organizer(request.user)