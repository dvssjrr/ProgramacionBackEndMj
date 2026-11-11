"""Páginas públicas y paneles por rol, incluida la gestión administrativa."""

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (ClaseForm, ConfiguracionForm, MembresiaForm, PagoForm, PlanForm, ProductoForm,
                    RegistroForm, UsuarioCrearForm, UsuarioEditarForm)
from .models import Clase, Configuracion, Membresia, Pago, Plan, Producto, RegistroAcceso, User
from .permissions import es_administrador, es_equipo
from .services import promover_espera


def inicio(request):
    clases = Clase.objects.filter(activa=True, inicio__gt=timezone.now()).select_related("instructor")[:6]
    return render(request, "fitlife/landing.html", {
        "planes": Plan.objects.filter(activo=True).order_by("precio"),
        "clases": clases,
    })


def registro(request):
    if request.user.is_authenticated:
        return redirect("panel")
    form = RegistroForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        # El registro publico nunca permite elegir un rol administrativo.
        user.role = User.Role.SOCIO
        user.save()
        login(request, user)
        return redirect("panel")
    return render(request, "fitlife/registro.html", {"form": form})


@login_required
def panel(request):
    user = request.user
    # Cada rol recibe solamente la informacion necesaria para su panel.
    context = {"es_equipo": es_equipo(user), "es_admin": es_administrador(user), "es_instructor": user.role == User.Role.INSTRUCTOR and not user.is_superuser}
    if context["es_equipo"]:
        context.update({
            "dentro": User.objects.filter(dentro=True).count(),
            "capacidad": Configuracion.objects.filter(pk=1).first(),
            "socios_count": User.objects.filter(role=User.Role.SOCIO, is_active=True).count(),
            "clases_count": Clase.objects.filter(activa=True, inicio__gte=timezone.now()).count(),
        })
    elif context["es_instructor"]:
        context["clases_instructor"] = (
            Clase.objects.filter(instructor=user, activa=True, inicio__date=timezone.localdate())
            .prefetch_related("reservas__socio")
        )
    else:
        hoy = timezone.localdate()
        context["membresia"] = (
            user.membresias.filter(estado=Membresia.Estado.ACTIVA, inicio__lte=hoy, fin__gte=hoy)
            .select_related("plan").order_by("-fin").first()
        )
        context["reservas"] = user.reservas.select_related("clase").filter(clase__inicio__gte=timezone.now()).order_by("clase__inicio")
        context["esperas"] = user.esperas.select_related("clase").filter(clase__inicio__gte=timezone.now()).order_by("clase__inicio")
        context["accesos"] = user.accesos.filter(permitido=True).order_by("-fecha")[:20]
    return render(request, "fitlife/panel.html", context)


@login_required
def acceso_gimnasio(request):
    """Muestra el lector de QR solo al personal de recepción y administración."""
    if not es_equipo(request.user):
        raise PermissionDenied
    return render(request, "fitlife/acceso.html", {
        "dentro": User.objects.filter(dentro=True).count(),
        "capacidad": Configuracion.objects.filter(pk=1).first(),
    })


@login_required
def gestionar_clases(request, clase_id=None):
    if not es_equipo(request.user):
        raise PermissionDenied
    with transaction.atomic():
        # Las reservas y cambios de cupo comparten el bloqueo de esta clase.
        clase = get_object_or_404(Clase.objects.select_for_update(), pk=clase_id) if clase_id else None
        form = ClaseForm(request.POST if request.method == "POST" else None, instance=clase)
        if request.method == "POST" and form.is_valid():
            if clase and form.cleaned_data["cupo_maximo"] < clase.reservas.count():
                form.add_error("cupo_maximo", "El cupo no puede ser inferior a las reservas existentes.")
            else:
                clase = form.save()
                promover_espera(clase)
                return redirect("gestionar_clases")
    clases = Clase.objects.select_related("instructor").annotate(ocupados=Count("reservas"))
    return render(request, "fitlife/gestionar_clases.html", {"form": form, "clases": clases, "editando": clase_id is not None})


@login_required
@require_POST
def eliminar_clase(request, clase_id):
    if not es_equipo(request.user):
        raise PermissionDenied
    with transaction.atomic():
        clase = get_object_or_404(Clase.objects.select_for_update(), pk=clase_id)
        try:
            clase.delete()
        except ProtectedError:
            messages.error(request, "No se puede eliminar la clase porque tiene reservas o lista de espera.")
        else:
            messages.success(request, "Clase eliminada correctamente.")
    return redirect("gestionar_clases")


def error_403(request, exception=None):
    return render(request, "fitlife/error.html", {"codigo": 403, "mensaje": "No tienes permiso para acceder a esta página."}, status=403)


def error_404(request, exception=None):
    return render(request, "fitlife/error.html", {"codigo": 404, "mensaje": "No encontramos la página que buscas."}, status=404)


def csrf_failure(request, reason=""):
    return render(request, "fitlife/error.html", {
        "codigo": 403, "mensaje": "Tu sesión de seguridad ha caducado. Recarga la página e inténtalo nuevamente.",
    }, status=403)


# Mapa de recursos permitidos para la vista administrativa compartida.
MANAGEMENT = {
    "planes": (Plan, PlanForm, "Planes", "plan"),
    "membresias": (Membresia, MembresiaForm, "Membresías", "membresía"),
    "pagos": (Pago, PagoForm, "Pagos", "pago"),
    "productos": (Producto, ProductoForm, "Productos", "producto"),
}


@login_required
def gestionar(request, tipo, objeto_id=None):
    if not es_equipo(request.user):
        raise PermissionDenied
    if tipo not in MANAGEMENT:
        raise PermissionDenied
    model, form_class, titulo, singular = MANAGEMENT[tipo]
    with transaction.atomic():
        # El catalogo se bloquea para no cambiar precios durante la compra.
        qs = model.objects.select_for_update() if tipo in {"productos", "planes"} else model.objects
        obj = get_object_or_404(qs, pk=objeto_id) if objeto_id else None
        form = form_class(request.POST if request.method == "POST" else None, instance=obj)
        if request.method == "POST" and form.is_valid():
            if tipo == "membresias":
                User.objects.select_for_update().get(pk=form.cleaned_data["socio"].pk)
            form.save()
            messages.success(request, f"{singular.capitalize()} guardado correctamente.")
            return redirect("gestionar", tipo=tipo)
    queryset = model.objects.all().order_by("-pk")
    if tipo == "membresias":
        queryset = queryset.select_related("socio", "plan")
    elif tipo == "pagos":
        queryset = queryset.select_related("membresia__socio", "membresia__plan")
    return render(request, "fitlife/gestionar.html", {
        "tipo": tipo, "titulo": titulo, "singular": singular, "form": form,
        "editando": obj is not None, "items": Paginator(queryset, 25).get_page(request.GET.get("page")),
    })


@login_required
@require_POST
def eliminar(request, tipo, objeto_id):
    if not es_equipo(request.user):
        raise PermissionDenied
    if tipo not in MANAGEMENT:
        raise PermissionDenied
    model, _, _, singular = MANAGEMENT[tipo]
    obj = get_object_or_404(model, pk=objeto_id)
    try:
        obj.delete()
    except ProtectedError:
        messages.error(request, f"No se puede eliminar: el {singular} tiene registros asociados.")
    else:
        messages.success(request, f"{singular.capitalize()} eliminado correctamente.")
    return redirect("gestionar", tipo=tipo)


@login_required
def usuarios(request, usuario_id=None):
    if not es_administrador(request.user):
        raise PermissionDenied
    usuario = get_object_or_404(User, pk=usuario_id) if usuario_id else None
    if usuario and usuario.is_superuser and usuario.pk != request.user.pk:
        raise PermissionDenied
    if usuario:
        form = UsuarioEditarForm(request.POST if request.method == "POST" else None, instance=usuario, actor=request.user)
    else:
        form = UsuarioCrearForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Usuario guardado correctamente.")
        return redirect("usuarios")
    lista = User.objects.order_by("username")
    return render(request, "fitlife/usuarios.html", {
        "form": form, "usuario_editado": usuario, "items": Paginator(lista, 25).get_page(request.GET.get("page")),
    })


@login_required
def cambiar_clave(request, usuario_id):
    if not es_administrador(request.user):
        raise PermissionDenied
    usuario = get_object_or_404(User, pk=usuario_id)
    if usuario.is_superuser and usuario.pk != request.user.pk:
        raise PermissionDenied
    form = SetPasswordForm(usuario, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        if usuario.pk == request.user.pk:
            update_session_auth_hash(request, usuario)
        messages.success(request, "Contraseña actualizada.")
        return redirect("usuarios")
    return render(request, "fitlife/clave.html", {"form": form, "usuario_editado": usuario})


@login_required
def configuracion(request):
    if not es_administrador(request.user):
        raise PermissionDenied
    config = get_object_or_404(Configuracion, pk=1)
    form = ConfiguracionForm(request.POST if request.method == "POST" else None, instance=config)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Capacidad actualizada.")
        return redirect("configuracion")
    return render(request, "fitlife/configuracion.html", {"form": form})


@login_required
def reportes(request):
    if not es_equipo(request.user):
        raise PermissionDenied
    accesos = RegistroAcceso.objects.select_related("socio", "operador")
    return render(request, "fitlife/reportes.html", {"items": Paginator(accesos, 25).get_page(request.GET.get("page"))})
