"""Páginas de tienda y acciones de compra con mensajes para el usuario."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import CarritoItem, Pedido, Plan, Producto, User
from .forms import FiltroProductosForm
from .permissions import es_equipo
from .shop import (agregar, cambiar_cantidad, cancelar_pedido, confirmar_pedido,
                   crear_pedido, exigir_socio, simular_pago)


def tienda(request):
    # El catalogo es publico, pero solo los socios activos pueden comprar.
    productos = Producto.objects.filter(activo=True).order_by("nombre")
    filtros = FiltroProductosForm(request.GET or None)
    if filtros.is_bound:
        if filtros.is_valid():
            busqueda = filtros.cleaned_data["q"]
            categoria = filtros.cleaned_data["categoria"]
            if busqueda:
                productos = productos.filter(Q(nombre__icontains=busqueda) | Q(descripcion__icontains=busqueda))
            if categoria:
                productos = productos.filter(categoria=categoria)
        else:
            productos = productos.none()
    return render(request, "fitlife/tienda.html", {
        "planes": Plan.objects.filter(activo=True).order_by("precio"),
        "productos": productos,
        "filtros": filtros,
        "puede_comprar": request.user.is_authenticated and request.user.role == User.Role.SOCIO and not request.user.is_superuser,
    })


@login_required
def carrito(request):
    try:
        exigir_socio(request.user)
    except ValidationError:
        raise PermissionDenied
    items = list(CarritoItem.objects.filter(socio=request.user).select_related("plan", "producto"))
    return render(request, "fitlife/carrito.html", {
        "items": items, "total": sum(item.subtotal for item in items),
        "pedidos": request.user.pedidos.prefetch_related("items")[:20],
    })


@login_required
@require_POST
def agregar_articulo(request, tipo, pk):
    try:
        agregar(request.user, tipo, pk)
        messages.success(request, "Artículo agregado al carrito.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("tienda")


@login_required
@require_POST
def actualizar_item(request, pk):
    try:
        cantidad = int(request.POST.get("cantidad", ""))
        if cantidad < 0 or cantidad > 10000:
            raise ValueError
        cambiar_cantidad(request.user, pk, cantidad)
        messages.success(request, "Carrito actualizado.")
    except ValueError:
        messages.error(request, "Introduce una cantidad válida.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("carrito")


@login_required
@require_POST
def solicitar(request):
    # El pedido pendiente abre el simulador, que nunca cobra ni confirma la venta.
    try:
        pedido = crear_pedido(request.user)
        return redirect("pagar_pedido", pk=pedido.pk)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("carrito")


@login_required
def pagar_pedido(request, pk):
    try:
        exigir_socio(request.user)
    except ValidationError:
        raise PermissionDenied
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("items"),
        pk=pk, socio=request.user,
    )
    if request.method == "POST":
        try:
            metodo = request.POST.get("metodo", "")
            resultado = request.POST.get("resultado", "")
            pedido = simular_pago(pk, request.user, metodo, resultado)
            if pedido.resultado_pago_simulado == Pedido.ResultadoPagoSimulado.APROBADO:
                messages.success(
                    request,
                    "Simulación aprobada. No se realizó un cobro; recepción debe confirmar el pago real.",
                )
            else:
                messages.error(
                    request,
                    "Simulación rechazada. No se realizó un cobro y el pedido sigue pendiente.",
                )
            return redirect("pagar_pedido", pk=pk)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    return render(request, "fitlife/pago_simulado.html", {"pedido": pedido})


@login_required
def pedidos_equipo(request):
    if not es_equipo(request.user):
        raise PermissionDenied
    pedidos = Pedido.objects.select_related("socio", "confirmado_por").prefetch_related("items")
    return render(request, "fitlife/pedidos.html", {"items": Paginator(pedidos, 25).get_page(request.GET.get("page"))})


@login_required
@require_POST
def confirmar(request, pk):
    if not es_equipo(request.user):
        raise PermissionDenied
    try:
        confirmar_pedido(pk, request.user)
        messages.success(request, f"Pago del pedido #{pk} confirmado; entrega los productos en recepción.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("pedidos_equipo")


@login_required
@require_POST
def cancelar(request, pk):
    equipo = es_equipo(request.user)
    # El servicio verifica que el pedido pertenezca al socio, salvo para el equipo.
    try:
        cancelar_pedido(pk, request.user, equipo=equipo)
        messages.success(request, f"Pedido #{pk} cancelado.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("pedidos_equipo" if equipo else "carrito")
