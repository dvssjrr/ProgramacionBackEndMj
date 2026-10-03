"""Permisos por rol para el catálogo y las operaciones de organizador."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_master(user):
    """Indica si el usuario tiene privilegios de superusuario."""
    return bool(user and user.is_authenticated and user.is_superuser)


def is_organizer(user):
    """Reconoce al maestro, a staff o a miembros del grupo Organizador."""
    return bool(
        user and user.is_authenticated
        and (is_master(user) or user.is_staff or user.groups.filter(name='Organizador').exists())
    )


class IsOrganizer(BasePermission):
    """Restringe operaciones de gestión al maestro o a un organizador."""

    def has_permission(self, request, view):
        """Autoriza al maestro y a cuentas con permisos de organizador."""
        return is_organizer(request.user)


class PublicReadOrganizerWrite(BasePermission):
    """Permite leer el catálogo públicamente y exige rol para modificarlo."""

    def has_permission(self, request, view):
        """Permite lectura pública y restringe escrituras a organizadores."""
        return request.method in SAFE_METHODS or is_organizer(request.user)