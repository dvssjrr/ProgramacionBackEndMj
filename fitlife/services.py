"""Reglas de vigencia, reservas y acceso compartidas por las vistas."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Clase, ListaEspera, Membresia, RegistroAcceso, Reserva, User


def tiene_membresia(user):
    """Comprueba si existe una membresía activa dentro de su periodo inclusivo."""
    hoy = timezone.localdate()
    return user.is_active and user.membresias.filter(
        estado=Membresia.Estado.ACTIVA, inicio__lte=hoy, fin__gte=hoy
    ).exists()


@transaction.atomic
def reservar(clase_id, socio):
    """Bloquea la clase y asigna una plaza o una posición en la lista de espera."""
    # El bloqueo evita que solicitudes simultaneas ocupen la misma ultima plaza.
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
    """Cancela la inscripción y promociona la espera cuando queda una plaza."""
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
    """Ocupa las plazas libres en orden; el llamador debe bloquear la clase."""
    if not clase.activa or clase.inicio <= timezone.now():
        return
    while Reserva.objects.filter(clase=clase).count() < clase.cupo_maximo:
        espera = ListaEspera.objects.filter(clase=clase).select_related("socio").first()
        if not espera:
            break
        if tiene_membresia(espera.socio):
            Reserva.objects.create(clase=clase, socio=espera.socio)
        # Quien ya no tiene membresia vigente sale de la cola sin recibir plaza.
        espera.delete()


@transaction.atomic
def registrar_acceso(socio_id, operador, accion):
    """Registra entrada o salida y serializa los cambios de presencia del socio."""
    socio = User.objects.select_for_update().get(pk=socio_id)
    motivo = ""
    if accion == RegistroAcceso.Accion.ENTRADA:
        if socio.dentro:
            motivo = "El socio ya está dentro."
        elif socio.role != User.Role.SOCIO:
            motivo = "Solo los socios pueden registrar entrada."
        elif not tiene_membresia(socio):
            motivo = "Membresía vencida, congelada o inexistente."
    # Se permite salir aunque la membresia haya vencido mientras estaba dentro.
    elif not socio.dentro:
        motivo = "El socio no está dentro."
    if not motivo:
        socio.dentro = accion == RegistroAcceso.Accion.ENTRADA
        socio.save(update_fields=["dentro"])
    return RegistroAcceso.objects.create(
        socio=socio, operador=operador, accion=accion, permitido=not motivo, motivo=motivo
    )
