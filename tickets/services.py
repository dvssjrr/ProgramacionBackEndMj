"""Operaciones transaccionales de compra, inventario y estados de órdenes."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Cart, Order, OrderItem, Sector, Ticket


@transaction.atomic
def pay_cart(user):
    """Valida stock con bloqueos, crea orden pagada, descuenta y emite tickets."""
    cart, _ = Cart.objects.get_or_create(user=user)
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    cart_items = list(cart.items.select_related('sector', 'sector__event').order_by('sector_id'))
    if not cart_items:
        raise ValidationError('El carro está vacío.')

    # Bloquea sectores en orden fijo para evitar que pagos simultáneos vendan el mismo stock.
    sectors = {
        sector.pk: sector
        for sector in Sector.objects.select_for_update().filter(
            pk__in=[item.sector_id for item in cart_items]
        ).order_by('pk')
    }
    for item in cart_items:
        if item.quantity > sectors[item.sector_id].available_tickets:
            raise ValidationError(f'Stock insuficiente para {sectors[item.sector_id].name}.')

    order = Order.objects.create(user=user)
    total = Decimal('0.00')
    for item in cart_items:
        sector = sectors[item.sector_id]
        order_item = OrderItem.objects.create(
            order=order, sector=sector, sector_name=sector.name,
            event_name=sector.event.name, unit_price=sector.price, quantity=item.quantity,
        )
        total += order_item.subtotal
        sector.available_tickets -= item.quantity
        sector.save(update_fields=['available_tickets'])
        Ticket.objects.bulk_create([Ticket(order_item=order_item) for _ in range(item.quantity)])

    order.total = total
    order.status = Order.Status.PAID
    order.save(update_fields=['total', 'status', 'updated_at'])
    cart.items.all().delete()
    return order


@transaction.atomic
def change_order_status(order, new_status):
    """Limita transiciones y devuelve stock solo en la primera cancelación pagada."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    transitions = {
        Order.Status.PAID: {Order.Status.DELIVERED, Order.Status.CANCELLED},
        Order.Status.DELIVERED: set(),
        Order.Status.CANCELLED: set(),
        Order.Status.PENDING: {Order.Status.CANCELLED},
    }
    if new_status not in transitions[order.status]:
        raise ValidationError(f'Transición no permitida: {order.status} a {new_status}.')

    # Solo un pedido pagado consumió inventario; los estados terminales no permiten duplicar la devolución.
    if new_status == Order.Status.CANCELLED and order.status == Order.Status.PAID:
        items = list(order.items.select_related('sector').order_by('sector_id'))
        sectors = {
            sector.pk: sector
            for sector in Sector.objects.select_for_update().filter(
                pk__in=[item.sector_id for item in items]
            ).order_by('pk')
        }
        for item in items:
            sectors[item.sector_id].available_tickets += item.quantity
            sectors[item.sector_id].save(update_fields=['available_tickets'])
        Ticket.objects.filter(order_item__order=order).update(status=Ticket.Status.CANCELLED)
    elif new_status == Order.Status.DELIVERED:
        Ticket.objects.filter(order_item__order=order).update(status=Ticket.Status.USED)

    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])
    return order