"""Convierte modelos Tickets en respuestas API y valida entradas del cliente."""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from .models import Cart, CartItem, Event, Order, OrderItem, Sector, Ticket, Venue
from .permissions import is_master


def user_role(user):
    """Calcula el claim de rol utilizado por la API."""
    if is_master(user):
        return 'maestro'
    if user.is_staff or user.groups.filter(name='Organizador').exists():
        return 'organizador'
    return 'espectador'


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Incluye el rol tanto en la respuesta como en access y refresh."""

    @classmethod
    def get_token(cls, user):
        """Incluye el rol del usuario como claim verificable del JWT."""
        token = super().get_token(user)
        token['role'] = user_role(user)
        return token

    def validate(self, attrs):
        """Devuelve access y refresh junto con el rol calculado del usuario."""
        data = super().validate(attrs)
        data['role'] = user_role(self.user)
        return data


class SpectatorRegistrationSerializer(serializers.Serializer):
    """Valida los datos mínimos para crear una cuenta de espectador."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, username):
        """Rechaza nombres de usuario que ya existen."""
        if get_user_model().objects.filter(username=username).exists():
            raise serializers.ValidationError('Este nombre de usuario ya está registrado.')
        return username

    def validate_password(self, password):
        """Aplica las reglas de contraseña configuradas en Django."""
        try:
            validate_password(password)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        return password

    def create(self, validated_data):
        """Crea una cuenta normal; el rol nunca se acepta desde el cliente."""
        return get_user_model().objects.create_user(**validated_data)


class TokenPairResponseSerializer(serializers.Serializer):
    """Describe los tokens y el rol devueltos al autenticar o registrarse."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    role = serializers.ChoiceField(choices=['espectador', 'organizador', 'maestro'])
    username = serializers.CharField()


class VenueSerializer(serializers.ModelSerializer):
    """Expone los datos del recinto sin permitir cambiar su organizador."""

    organizer = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Venue
        fields = ['id', 'name', 'address', 'capacity', 'organizer']
        read_only_fields = ['id', 'organizer']


class SectorSerializer(serializers.ModelSerializer):
    """Valida la localidad y protege el stock de cambios directos por API."""

    class Meta:
        model = Sector
        fields = ['id', 'event', 'name', 'price', 'total_tickets', 'available_tickets']
        read_only_fields = ['id', 'available_tickets']

    def validate_event(self, event):
        """Evita que una localidad se asocie a eventos de otro organizador."""
        request = self.context.get('request')
        if request and event.organizer_id != request.user.id and not is_master(request.user):
            raise serializers.ValidationError('El evento debe pertenecer al organizador.')
        return event

    def validate(self, attrs):
        """Evita reducir el stock total por debajo de las entradas ya vendidas."""
        if self.instance and 'total_tickets' in attrs:
            sold = self.instance.total_tickets - self.instance.available_tickets
            if attrs['total_tickets'] < sold:
                raise serializers.ValidationError({
                    'total_tickets': f'No puede ser menor que las {sold} entradas ya vendidas.',
                })
        return attrs

    def update(self, instance, validated_data):
        """Ajusta disponibilidad al nuevo total, preservando todas las ventas."""
        new_total = validated_data.get('total_tickets', instance.total_tickets)
        sold = instance.total_tickets - instance.available_tickets
        validated_data['available_tickets'] = new_total - sold
        return super().update(instance, validated_data)


class EventSerializer(serializers.ModelSerializer):
    """Incluye localidades de lectura y valida que el recinto pertenezca al organizador."""

    venue_name = serializers.CharField(source='venue.name', read_only=True)
    organizer = serializers.StringRelatedField(read_only=True)
    sectors = SectorSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'name', 'artist', 'starts_at', 'description', 'venue', 'venue_name', 'organizer', 'sectors', 'is_published']
        read_only_fields = ['id', 'organizer']

    def validate_starts_at(self, starts_at):
        """Rechaza eventos nuevos o reprogramados a una fecha pasada."""
        if starts_at <= timezone.now():
            raise serializers.ValidationError('La fecha y hora deben ser futuras.')
        return starts_at

    def validate_venue(self, venue):
        """Evita asociar un evento a un recinto de otro organizador."""
        request = self.context.get('request')
        if request and venue.organizer_id != request.user.id and not is_master(request.user):
            raise serializers.ValidationError('Solo puedes usar recintos propios.')
        return venue


class CartItemSerializer(serializers.ModelSerializer):
    """Valida el sector y conserva cantidades en el carro asociado al usuario."""

    sector = SectorSerializer(read_only=True)
    sector_id = serializers.PrimaryKeyRelatedField(
        queryset=Sector.objects.all(), source='sector', write_only=True, required=False,
    )

    class Meta:
        model = CartItem
        fields = ['id', 'sector', 'sector_id', 'quantity']
        read_only_fields = ['id']

    def validate(self, attrs):
        """Exige sector al agregar un ítem; las lecturas muestran su detalle."""
        if self.instance is None and 'sector' not in attrs:
            raise serializers.ValidationError({'sector_id': 'Este campo es obligatorio.'})
        if self.instance is None and not attrs['sector'].event.is_published:
            raise serializers.ValidationError({'sector_id': 'El evento no está disponible para la venta.'})
        return attrs

    def create(self, validated_data):
        """Crea el carro si falta y acumula cantidades sin reservar inventario."""
        cart, _ = Cart.objects.get_or_create(user=self.context['request'].user)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            sector=validated_data['sector'],
            defaults={'quantity': validated_data['quantity']},
        )
        if not created:
            item.quantity += validated_data['quantity']
            item.save(update_fields=['quantity'])
        return item


class OrderItemSerializer(serializers.ModelSerializer):
    """Devuelve precio histórico, subtotal y códigos de entradas emitidas."""

    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    tickets = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'event_name', 'sector_name', 'unit_price', 'quantity', 'subtotal', 'tickets']

    def get_tickets(self, obj) -> list[str]:
        """Serializa cada UUID asociado al detalle de compra."""
        return [str(ticket.code) for ticket in obj.tickets.all()]


class OrderSerializer(serializers.ModelSerializer):
    """Representa una orden histórica con todos sus detalles."""

    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'total', 'created_at', 'updated_at', 'items']


class OrderStatusSerializer(serializers.Serializer):
    """Acepta solo estados finales que puede solicitar un organizador."""

    status = serializers.ChoiceField(choices=[Order.Status.DELIVERED, Order.Status.CANCELLED])


class TicketSerializer(serializers.ModelSerializer):
    """Presenta el código único y la información útil para ingresar al evento."""

    event = serializers.CharField(source='order_item.sector.event.name', read_only=True)
    artist = serializers.CharField(source='order_item.sector.event.artist', read_only=True)
    sector = serializers.CharField(source='order_item.sector_name', read_only=True)

    class Meta:
        model = Ticket
        fields = ['code', 'event', 'artist', 'sector', 'status', 'issued_at']