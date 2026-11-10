"""Comprobaciones compartidas de roles para las páginas y la API."""

from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import User


def es_equipo(user):
    return user.is_authenticated and (user.is_superuser or user.role in {User.Role.ADMIN, User.Role.STAFF})


def es_administrador(user):
    return user.is_authenticated and (user.is_superuser or user.role == User.Role.ADMIN)


class Equipo(BasePermission):
    def has_permission(self, request, view):
        return es_equipo(request.user)


class LecturaOEquipo(BasePermission):
    def has_permission(self, request, view):
        # Los metodos seguros permiten consultar; los cambios requieren equipo.
        return request.user.is_authenticated and (request.method in SAFE_METHODS or es_equipo(request.user))
