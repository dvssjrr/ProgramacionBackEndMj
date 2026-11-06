from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Clase, ListaEspera, Membresia, RegistroAcceso, Reserva, User


def tiene_membresia(user):
    hoy = timezone.localdate()
    return user.is_active and user.membresias.filter(
        estado=Membresia.Estado.ACTIVA, inicio__lte=hoy, fin__gte=hoy
    ).exists()


@transaction.atomic
def reservar(clase_id, socio):
    clase = get_object_or_404(Clase.objects.select_for_update(), pk=clase_id)
    if not clase.activa or clase.inicio <= timezone.now():
        raise ValidationError("La clase no está disponible.")
    if not tiene_membresia(socio):
        raise ValidationError("Necesitas una membresía activa y vigente.")
    if Reserva.objects.filter(clase=clase, socio=socio).exists() or ListaEspera.objects.filter(clase=clase, socio=socio).exists():
        raise ValidationError("Ya tienes una reserva o estás en lista de espera.")
    if Reserva.objects.filter(clase=clase).count() < clase.cupo_maximo:
        return "reservada", Reserva.objects.create(clase=clase, socio=socio)
    return "espera", ListaEspera.objects.create(clase=clase, socio=socio)


@transaction.atomic
def cancelar(clase_id, socio):
    clase = get_object_or_404(Clase.objects.select_for_update(), pk=clase_id)
    if clase.inicio <= timezone.now():
        raise ValidationError("No se puede cancelar una clase iniciada.")
    reserva = Reserva.objects.filter(clase=clase, socio=socio).first()
    espera = ListaEspera.objects.filter(clase=clase, socio=socio).first()
    if not reserva and not espera:
        raise ValidationError("No tienes una reserva o espera para esta clase.")
    if espera:
        espera.delete()
        return
    reserva.delete()
    promover_espera(clase)


def promover_espera(clase):
    if not clase.activa or clase.inicio <= timezone.now():
        return
    while Reserva.objects.filter(clase=clase).count() < clase.cupo_maximo:
        espera = ListaEspera.objects.filter(clase=clase).select_related("socio").first()
        if not espera:
            break
        if tiene_membresia(espera.socio):
            Reserva.objects.create(clase=clase, socio=espera.socio)
        espera.delete()


@transaction.atomic
def registrar_acceso(socio_id, operador, accion):
    socio = User.objects.select_for_update().get(pk=socio_id)
    motivo = ""
    if accion == RegistroAcceso.Accion.ENTRADA:
        if socio.dentro:
            motivo = "El socio ya está dentro."
        elif socio.role != User.Role.SOCIO:
            motivo = "Solo los socios pueden registrar entrada."
        elif not tiene_membresia(socio):
            motivo = "Membresía vencida, congelada o inexistente."
    elif not socio.dentro:
        motivo = "El socio no está dentro."
    if not motivo:
        socio.dentro = accion == RegistroAcceso.Accion.ENTRADA
        socio.save(update_fields=["dentro"])
    return RegistroAcceso.objects.create(
        socio=socio, operador=operador, accion=accion, permitido=not motivo, motivo=motivo
    )
