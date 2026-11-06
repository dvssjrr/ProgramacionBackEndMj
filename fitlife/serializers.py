from rest_framework import serializers

from .models import Clase, ListaEspera, Membresia, Pago, Plan, RegistroAcceso, Reserva, User


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = "__all__"


class MembresiaSerializer(serializers.ModelSerializer):
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
        inicio = attrs.get("inicio", getattr(self.instance, "inicio", None))
        fin = attrs.get("fin", getattr(self.instance, "fin", None))
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError("La fecha final no puede ser anterior a la inicial.")
        return attrs


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = "__all__"


class ClaseSerializer(serializers.ModelSerializer):
    ocupados = serializers.IntegerField(read_only=True)
    en_espera = serializers.IntegerField(read_only=True)

    class Meta:
        model = Clase
        fields = ["id", "nombre", "descripcion", "inicio", "cupo_maximo", "activa", "instructor", "ocupados", "en_espera"]

    def validate_instructor(self, instructor):
        if instructor and (instructor.role != User.Role.INSTRUCTOR or not instructor.is_active):
            raise serializers.ValidationError("Selecciona un instructor activo.")
        return instructor


class ReservaSerializer(serializers.ModelSerializer):
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
