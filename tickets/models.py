"""Modelos del catálogo, carro persistente, órdenes y entradas."""

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Venue(models.Model):
    """Recinto perteneciente a un organizador."""

    name = models.CharField(max_length=160)
    address = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='venues')

    def __str__(self):
        return self.name


class Event(models.Model):
    """Evento público con artista, fecha, recinto y organizador."""

    name = models.CharField(max_length=180)
    artist = models.CharField(max_length=180)
    starts_at = models.DateTimeField()
    description = models.TextField(blank=True)
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name='events')
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_events')

    def __str__(self):
        return f'{self.name} - {self.artist}'


class Sector(models.Model):
    """Localidad; el stock cambia únicamente al pagar o cancelar."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='sectors')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    total_tickets = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    available_tickets = models.PositiveIntegerField(validators=[MinValueValidator(0)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['event', 'name'], name='unique_sector_per_event')]
        ordering = ['event__starts_at', 'name']

    def __str__(self):
        return f'{self.event.name} - {self.name}'


class Cart(models.Model):
    """Carro persistente único por usuario, independiente de la sesión."""

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVO', 'Activo'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ticket_cart')
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CartItem(models.Model):
    """Ítem agregado sin reservar ni descontar inventario."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name='cart_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cart', 'sector'], name='unique_sector_per_cart')]


class Order(models.Model):
    """Historial de compra con estados permitidos explícitamente."""

    class Status(models.TextChoices):
        PENDING = 'PENDIENTE', 'Pendiente'
        PAID = 'PAGADO', 'Pagado'
        DELIVERED = 'ENTREGADO', 'Entregado'
        CANCELLED = 'CANCELADO', 'Cancelado'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ticket_orders')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OrderItem(models.Model):
    """Detalle y precio congelado para conservar el valor histórico."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name='order_items')
    sector_name = models.CharField(max_length=100)
    event_name = models.CharField(max_length=180)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class Ticket(models.Model):
    """Entrada individual identificada mediante UUID único."""

    class Status(models.TextChoices):
        VALID = 'VALIDA', 'Válida'
        USED = 'UTILIZADA', 'Utilizada'
        CANCELLED = 'CANCELADA', 'Cancelada'

    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='tickets')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.VALID)
    issued_at = models.DateTimeField(auto_now_add=True)