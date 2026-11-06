from io import BytesIO

import qrcode
from django.core import signing
from django.db import transaction
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.cache import add_never_cache_headers
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Clase, Configuracion, ListaEspera, Membresia, Pago, Plan, RegistroAcceso, Reserva, User
from .permissions import Equipo, LecturaOEquipo, es_equipo
from .serializers import (ClaseSerializer, EscaneoSerializer, ListaEsperaSerializer,
                          MembresiaSerializer, PagoSerializer, PlanSerializer,
                          RegistroAccesoSerializer, ReservaSerializer)
from .services import cancelar, promover_espera, registrar_acceso, reservar, tiene_membresia

QR_SALT = "fitlife.acceso"
QR_MAX_AGE = 120


class ProtectedDeleteMixin:
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as exc:
            raise ValidationError("No se puede eliminar porque existen registros asociados.") from exc


class PlanViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = Plan.objects.all().order_by("nombre")
    serializer_class = PlanSerializer
    permission_classes = [LecturaOEquipo]


class MembresiaViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    serializer_class = MembresiaSerializer

    def get_queryset(self):
        qs = Membresia.objects.select_related("socio", "plan").order_by("-fin")
        return qs if es_equipo(self.request.user) else qs.filter(socio=self.request.user)

    def get_permissions(self):
        return [IsAuthenticated()] if self.action in {"list", "retrieve"} else [Equipo()]


class PagoViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    serializer_class = PagoSerializer

    def get_queryset(self):
        qs = Pago.objects.select_related("membresia", "membresia__socio").order_by("-fecha")
        return qs if es_equipo(self.request.user) else qs.filter(membresia__socio=self.request.user)

    def get_permissions(self):
        return [IsAuthenticated()] if self.action in {"list", "retrieve"} else [Equipo()]


class ClaseViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    serializer_class = ClaseSerializer
    permission_classes = [LecturaOEquipo]

    def get_queryset(self):
        qs = Clase.objects.annotate(ocupados=Count("reservas", distinct=True), en_espera=Count("esperas", distinct=True))
        return qs if es_equipo(self.request.user) else qs.filter(activa=True)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        clase = get_object_or_404(Clase.objects.select_for_update(), pk=kwargs["pk"])
        serializer = self.get_serializer(clase, data=request.data, partial=kwargs.pop("partial", False))
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("cupo_maximo", clase.cupo_maximo) < clase.reservas.count():
            raise ValidationError("El cupo no puede ser inferior a las reservas existentes.")
        self.perform_update(serializer)
        promover_espera(clase)
        clase = self.get_queryset().get(pk=clase.pk)
        return Response(self.get_serializer(clase).data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        clase = get_object_or_404(Clase.objects.select_for_update(), pk=kwargs["pk"])
        self.perform_destroy(clase)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def reservar(self, request, pk=None):
        get_object_or_404(Clase, pk=pk)
        resultado, objeto = reservar(pk, request.user)
        serializer = ReservaSerializer(objeto) if resultado == "reservada" else ListaEsperaSerializer(objeto)
        return Response({"estado": resultado, "detalle": serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def cancelar(self, request, pk=None):
        get_object_or_404(Clase, pk=pk)
        cancelar(pk, request.user)
        return Response({"detalle": "Inscripción cancelada."})


class ReservaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReservaSerializer

    def get_queryset(self):
        qs = Reserva.objects.select_related("socio", "clase")
        return qs if es_equipo(self.request.user) else qs.filter(socio=self.request.user)


class EsperaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ListaEsperaSerializer

    def get_queryset(self):
        qs = ListaEspera.objects.select_related("socio", "clase")
        return qs if es_equipo(self.request.user) else qs.filter(socio=self.request.user)


class AccesoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RegistroAccesoSerializer
    permission_classes = [Equipo]
    queryset = RegistroAcceso.objects.select_related("socio", "operador")

    @action(detail=False, methods=["post"])
    def escanear(self, request):
        serializer = EscaneoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            socio_id = signing.loads(serializer.validated_data["token"], salt=QR_SALT, max_age=QR_MAX_AGE)
            if not isinstance(socio_id, int) or isinstance(socio_id, bool):
                raise signing.BadSignature("Token inválido")
            get_object_or_404(User, pk=socio_id)
        except (signing.BadSignature, Http404):
            raise ValidationError({"token": "El código QR no es válido o ha caducado."})
        registro = registrar_acceso(socio_id, request.user, serializer.validated_data["accion"])
        return Response(RegistroAccesoSerializer(registro).data, status=200 if registro.permitido else 403)


@api_view(["GET"])
def perfil(request):
    token = signing.dumps(request.user.pk, salt=QR_SALT)
    response = Response({
        "id": request.user.pk, "username": request.user.username, "role": request.user.role,
        "rol_visible": "Administrador" if request.user.is_superuser else request.user.get_role_display(),
        "es_socio": request.user.role == User.Role.SOCIO and not request.user.is_superuser,
        "puede_usar_admin": request.user.is_staff,
        "es_equipo": es_equipo(request.user), "dentro": request.user.dentro,
        "membresia_vigente": tiene_membresia(request.user),
        "qr_token": token, "qr_validez_segundos": QR_MAX_AGE,
    })
    add_never_cache_headers(response)
    return response


@api_view(["GET"])
def qr(request):
    token = signing.dumps(request.user.pk, salt=QR_SALT)
    buffer = BytesIO()
    qrcode.make(token).save(buffer, format="PNG")
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    add_never_cache_headers(response)
    return response


@api_view(["GET"])
@permission_classes([Equipo])
def aforo(request):
    capacidad = Configuracion.objects.filter(pk=1).values_list("capacidad", flat=True).first()
    if capacidad is None or capacidad < 1:
        return Response({"detalle": "Configura una capacidad válida en el panel de administración."}, status=503)
    dentro = User.objects.filter(dentro=True).count()
    return Response({"dentro": dentro, "capacidad": capacidad, "porcentaje": round(dentro * 100 / capacidad, 2)})
