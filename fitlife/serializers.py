"""Conversión y validación de los datos intercambiados por la API REST."""

from rest_framework import serializers
from django.utils import timezone

from .models import Clase, ListaEspera, Membresia, Pago, Plan, RegistroAcceso, Reserva, User


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = "__all__"


class MembresiaSerializer(serializers.ModelSerializer):
    # Son propiedades calculadas por el modelo, no campos editables de la API.
    habilitada = serializers.BooleanField(read_only=True)
    estado_efectivo = serializers.CharField(read_only=True)

    class Meta:
        model = Membresia
        fields = "__all__"

    def validate_socio(self, socio):
        if socio.role != User.Role.SOCIO or not socio.is_active:
            raise serializers.ValidationError("Selecciona un socio activo.")
        return socio

    def validate(self, attrs):
        # En una edicion parcial se conservan las fechas que no se enviaron.
        inicio = attrs.get("inicio", getattr(self.instance, "inicio", None))
        fin = attrs.get("fin", getattr(self.instance, "fin", None))
        hoy = timezone.localdate()
        if "inicio" in attrs and inicio < hoy and (not self.instance or inicio != self.instance.inicio):
            raise serializers.ValidationError({"inicio": "La membresía no puede comenzar antes de hoy."})
        if "fin" in attrs and fin < hoy and (not self.instance or fin != self.instance.fin):
            raise serializers.ValidationError({"fin": "La membresía no puede terminar antes de hoy."})
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError("La fecha final no puede ser anterior a la inicial.")
        return attrs


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = "__all__"

    def validate_fecha(self, fecha):
        if timezone.localtime(fecha).date() < timezone.localdate():
            if not self.instance or fecha != self.instance.fecha:
                raise serializers.ValidationError("La fecha del pago no puede ser anterior a hoy.")
        return fecha


class ClaseSerializer(serializers.ModelSerializer):
    ocupados = serializers.IntegerField(read_only=True)
    en_espera = serializers.IntegerField(read_only=True)

    class Meta:
        model = Clase
        fields = ["id", "nombre", "descripcion", "inicio", "cupo_maximo", "activa", "instructor", "ocupados", "en_espera"]

    def validate_inicio(self, inicio):
        if inicio < timezone.now():
            if not self.instance or inicio != self.instance.inicio:
                raise serializers.ValidationError("La fecha y hora de la clase deben ser futuras.")
        return inicio

    def validate_instructor(self, instructor):
        if instructor and (instructor.role != User.Role.INSTRUCTOR or not instructor.is_active):
            raise serializers.ValidationError("Selecciona un instructor activo.")
        return instructor


class ReservaSerializer(serializers.ModelSerializer):
    # Las inscripciones se modifican mediante acciones que verifican cupos.
    class Meta:
        model = Reserva
        fields = ["id", "socio", "clase", "creada"]
        read_only_fields = fields


class ListaEsperaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListaEspera
        fields = ["id", "socio", "clase", "creada"]
        read_only_fields = fields


class RegistroAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAcceso
        fields = ["id", "socio", "operador", "accion", "permitido", "motivo", "fecha"]
        read_only_fields = fields


class EscaneoSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=1024)
    accion = serializers.ChoiceField(choices=RegistroAcceso.Accion.choices)
