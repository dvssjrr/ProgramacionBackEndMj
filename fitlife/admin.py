"""Administrador de evaluación de solo lectura para los modelos de FitLife."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    CarritoItem, Clase, Configuracion, ListaEspera, Membresia, Pago, Pedido,
    PedidoItem, Plan, Producto, RegistroAcceso, Reserva, User,
)


class FitlifeAdminSite(admin.AdminSite):
    # Este sitio separado se usa para evaluar, no sustituye al panel de gestion.
    site_header = "FitLife | Administración"
    site_title = "FitLife | Administración"
    index_title = "Panel de evaluación"
    site_url = "/panel/"

    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser


fitlife_admin = FitlifeAdminSite(name="fitlife_admin")


class SoloLectura:
    # Los cambios se hacen en el panel o API para respetar las reglas de negocio.
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(User, site=fitlife_admin)
class FitlifeUserAdmin(SoloLectura, UserAdmin):
    # Columnas visibles, filtros y campos que se consultan desde el buscador.
    list_display = ("username", "email", "role", "is_active", "dentro")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
    fieldsets = UserAdmin.fieldsets + (("FitLife", {"fields": ("role", "dentro")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("FitLife", {"fields": ("role",)}),)
    readonly_fields = ("dentro",)


@admin.register(Plan, site=fitlife_admin)
class PlanAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("nombre", "precio", "duracion_dias", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(Membresia, site=fitlife_admin)
class MembresiaAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("socio", "plan", "inicio", "fin", "estado")
    list_filter = ("estado", "plan")
    search_fields = ("socio__username", "socio__email", "plan__nombre")
    # Carga las relaciones junto a la membresia para evitar consultas adicionales.
    list_select_related = ("socio", "plan")
    autocomplete_fields = ("socio", "plan")


@admin.register(Pago, site=fitlife_admin)
class PagoAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("membresia", "monto", "fecha", "referencia")
    list_filter = ("fecha",)
    search_fields = ("membresia__socio__username", "referencia")
    list_select_related = ("membresia", "membresia__socio", "membresia__plan")
    autocomplete_fields = ("membresia",)


@admin.register(Clase, site=fitlife_admin)
class ClaseAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("nombre", "inicio", "cupo_maximo", "activa")
    list_filter = ("activa", "inicio")
    search_fields = ("nombre",)


@admin.register(Reserva, site=fitlife_admin)
class ReservaAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("socio", "clase", "creada")
    list_filter = ("clase",)
    search_fields = ("socio__username", "clase__nombre")
    list_select_related = ("socio", "clase")


@admin.register(ListaEspera, site=fitlife_admin)
class ListaEsperaAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("socio", "clase", "creada")
    list_filter = ("clase",)
    search_fields = ("socio__username", "clase__nombre")
    list_select_related = ("socio", "clase")


@admin.register(RegistroAcceso, site=fitlife_admin)
class RegistroAccesoAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("socio", "operador", "accion", "permitido", "fecha", "motivo")
    list_filter = ("accion", "permitido", "fecha")
    search_fields = ("socio__username", "operador__username", "motivo")
    list_select_related = ("socio", "operador")


@admin.register(Configuracion, site=fitlife_admin)
class ConfiguracionAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("id", "capacidad")
    search_fields = ("id",)


@admin.register(Producto, site=fitlife_admin)
class ProductoAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "stock", "activo")
    list_filter = ("activo", "categoria")
    search_fields = ("nombre",)


@admin.register(CarritoItem, site=fitlife_admin)
class CarritoItemAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("socio", "plan", "producto", "cantidad")
    list_filter = ("plan", "producto")
    search_fields = ("socio__username", "plan__nombre", "producto__nombre")
    list_select_related = ("socio", "plan", "producto")


@admin.register(Pedido, site=fitlife_admin)
class PedidoAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("id", "socio", "estado", "total", "creado", "confirmado_por")
    list_filter = ("estado", "creado")
    search_fields = ("socio__username",)
    list_select_related = ("socio", "confirmado_por")


@admin.register(PedidoItem, site=fitlife_admin)
class PedidoItemAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("pedido", "nombre", "cantidad", "precio")
    list_filter = ("plan", "producto")
    search_fields = ("nombre", "pedido__socio__username")
    list_select_related = ("pedido", "pedido__socio")
