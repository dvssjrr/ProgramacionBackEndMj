"""Rutas de la API REST y acciones de acceso y reservas."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# El router genera las rutas de cada recurso y sus acciones REST.
router = DefaultRouter()
router.register("planes", views.PlanViewSet)
router.register("membresias", views.MembresiaViewSet, basename="membresia")
router.register("pagos", views.PagoViewSet, basename="pago")
router.register("clases", views.ClaseViewSet, basename="clase")
router.register("reservas", views.ReservaViewSet, basename="reserva")
router.register("esperas", views.EsperaViewSet, basename="espera")
router.register("accesos", views.AccesoViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("perfil/", views.perfil),
    path("perfil/qr/", views.qr),
    path("aforo/", views.aforo),
]
