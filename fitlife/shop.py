"""Operaciones transaccionales del carrito y la venta con pago en recepción."""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import CarritoItem, Membresia, Pago, Pedido, PedidoItem, Plan, Producto, User


def exigir_socio(user):
    """Limita las compras a cuentas activas de socios."""
    if not user.is_active or user.is_superuser or user.role != User.Role.SOCIO:
        raise ValidationError("Solo los socios pueden realizar compras.")


@transaction.atomic
def agregar(socio, tipo, pk):
    """Añade un artículo o sustituye el plan existente del carrito."""
    # El bloqueo coordina los cambios simultaneos en el carrito del mismo socio.
    socio = User.objects.select_for_update().get(pk=socio.pk)
    exigir_socio(socio)
    if tipo == "plan":
        plan = get_object_or_404(Plan, pk=pk, activo=True)
        CarritoItem.objects.filter(socio=socio, plan__isnull=False).delete()
        CarritoItem.objects.create(socio=socio, plan=plan)
    elif tipo == "producto":
        producto = get_object_or_404(Producto, pk=pk, activo=True)
        item = CarritoItem.objects.filter(socio=socio, producto=producto).first()
        cantidad = (item.cantidad if item else 0) + 1
        if cantidad > 10000 or cantidad > producto.stock:
            raise ValidationError("No hay suficientes unidades disponibles o se alcanzó el límite por producto.")
        if item:
            item.cantidad = cantidad
            item.save(update_fields=["cantidad"])
        else:
            CarritoItem.objects.create(socio=socio, producto=producto)
    else:
        raise ValidationError("El artículo no es válido.")


@transaction.atomic
def cambiar_cantidad(socio, item_id, cantidad):
    """Actualiza un producto del carrito; cero elimina cualquier artículo."""
    socio = User.objects.select_for_update().get(pk=socio.pk)
    exigir_socio(socio)
    item = get_object_or_404(CarritoItem.objects.select_related("producto"), pk=item_id, socio=socio)
    if cantidad == 0:
        item.delete()
    elif not item.producto or cantidad < 1 or cantidad > item.producto.stock or not item.producto.activo:
        raise ValidationError("Cantidad inválida o stock insuficiente.")
    else:
        item.cantidad = cantidad
        item.save(update_fields=["cantidad"])


@transaction.atomic
def crear_pedido(socio):
    """Fija precios y duración en un pedido pendiente, sin reservar inventario."""
    socio = User.objects.select_for_update().get(pk=socio.pk)
    exigir_socio(socio)
    items = list(CarritoItem.objects.filter(socio=socio).select_related("plan", "producto"))
    if not items:
        raise ValidationError("El carrito está vacío.")
    # Bloquear el catálogo para fijar precios y disponibilidad coherentes.
    planes = {p.pk: p for p in Plan.objects.select_for_update().filter(pk__in=[i.plan_id for i in items if i.plan_id]).order_by("pk")}
    productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=[i.producto_id for i in items if i.producto_id]).order_by("pk")}
    lineas = []
    for item in items:
        articulo = planes[item.plan_id] if item.plan_id else productos[item.producto_id]
        if not articulo.activo:
            raise ValidationError(f"{articulo.nombre} ya no está disponible. Retíralo del carrito.")
        if item.producto_id and item.cantidad > articulo.stock:
            raise ValidationError(f"No hay suficiente stock de {articulo.nombre}.")
        lineas.append((item, articulo))
    total = sum((articulo.precio * item.cantidad for item, articulo in lineas), Decimal("0"))
    if total > Decimal("9999999999.99"):
        raise ValidationError("El total supera el límite permitido para un pedido.")
    # Los precios y la duracion quedan guardados aunque luego cambie el catalogo.
    pedido = Pedido.objects.create(socio=socio, total=total)
    for item, articulo in lineas:
        PedidoItem.objects.create(
            pedido=pedido, plan=articulo if item.plan_id else None,
            producto=articulo if item.producto_id else None,
            nombre=articulo.nombre, precio=articulo.precio, cantidad=item.cantidad,
            duracion_dias=articulo.duracion_dias if item.plan_id else None,
        )
    CarritoItem.objects.filter(socio=socio).delete()
    return pedido


@transaction.atomic
def simular_pago(pedido_id, socio, metodo, resultado):
    """Guarda el resultado demostrativo sin cobrar ni confirmar la compra."""
    socio = User.objects.select_for_update().get(pk=socio.pk)
    exigir_socio(socio)
    pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_id, socio=socio)
    if pedido.estado != Pedido.Estado.PENDIENTE:
        raise ValidationError("Solo se pueden simular pagos de pedidos pendientes.")
    if metodo not in Pedido.MetodoPagoSimulado.values:
        raise ValidationError("Selecciona tarjeta de crédito o débito.")
    if resultado not in Pedido.ResultadoPagoSimulado.values:
        raise ValidationError("El resultado de la simulación no es válido.")
    pedido.metodo_pago_simulado = metodo
    pedido.resultado_pago_simulado = resultado
    pedido.simulacion_actualizada = timezone.now()
    pedido.save(update_fields=[
        "metodo_pago_simulado", "resultado_pago_simulado", "simulacion_actualizada",
    ])
    return pedido


@transaction.atomic
def confirmar_pedido(pedido_id, operador):
    """Valida stock y membresía, y confirma toda la venta en una transacción."""
    pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_id)
    if pedido.estado != Pedido.Estado.PENDIENTE:
        raise ValidationError("Este pedido ya no está pendiente.")
    socio = User.objects.select_for_update().get(pk=pedido.socio_id)
    exigir_socio(socio)
    items = list(pedido.items.all().order_by("pk"))
    planes = [i for i in items if i.plan_id]
    if len(planes) > 1 or not items:
        raise ValidationError("El pedido contiene artículos inválidos.")
    hoy = timezone.localdate()
    if planes and Membresia.objects.filter(socio=socio, fin__gte=hoy).filter(
        Q(estado=Membresia.Estado.ACTIVA) | Q(estado=Membresia.Estado.CONGELADA)
    ).exists():
        raise ValidationError("El socio ya tiene una membresía activa, futura o congelada.")
    if planes:
        plan = Plan.objects.select_for_update().get(pk=planes[0].plan_id)
        if not plan.activo:
            raise ValidationError("El plan del pedido ya no está disponible.")
    # El stock se comprueba y descuenta solo al confirmar el pago en recepcion.
    productos = {p.pk: p for p in Producto.objects.select_for_update().filter(
        pk__in=[i.producto_id for i in items if i.producto_id]
    ).order_by("pk")}
    for item in items:
        if item.producto_id:
            producto = productos[item.producto_id]
            if not producto.activo or producto.stock < item.cantidad:
                raise ValidationError(f"No hay stock suficiente de {item.nombre}. El pedido sigue pendiente.")
    for item in items:
        if item.producto_id:
            producto = productos[item.producto_id]
            producto.stock -= item.cantidad
            producto.save(update_fields=["stock"])
    if planes:
        linea = planes[0]
        # El pago de membresia incluye el plan; el pedido conserva el total completo.
        membresia = Membresia.objects.create(socio=socio, plan=plan, inicio=hoy,
            fin=hoy + timedelta(days=linea.duracion_dias - 1), estado=Membresia.Estado.ACTIVA)
        Pago.objects.create(membresia=membresia, monto=linea.precio, referencia=f"Pedido #{pedido.pk}")
        pedido.membresia = membresia
    pedido.estado = Pedido.Estado.CONFIRMADO
    pedido.confirmado_por = operador
    pedido.confirmado_en = timezone.now()
    pedido.save(update_fields=["membresia", "estado", "confirmado_por", "confirmado_en"])
    return pedido


@transaction.atomic
def cancelar_pedido(pedido_id, actor, equipo=False):
    """Cancela un pedido pendiente del socio o gestionado por el equipo."""
    pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_id)
    if not equipo and pedido.socio_id != actor.pk:
        raise ValidationError("No puedes cancelar este pedido.")
    if pedido.estado != Pedido.Estado.PENDIENTE:
        raise ValidationError("Solo se pueden cancelar pedidos pendientes.")
    pedido.estado = Pedido.Estado.CANCELADO
    pedido.save(update_fields=["estado"])
