from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Clase, Configuracion, ListaEspera, Membresia, Pago, Plan, RegistroAcceso, Reserva, User


@admin.register(User)
class FitlifeUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "dentro")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
    fieldsets = UserAdmin.fieldsets + (("FitLife", {"fields": ("role", "dentro")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("FitLife", {"fields": ("role",)}),)
    readonly_fields = ("dentro",)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio", "duracion_dias", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ("socio", "plan", "inicio", "fin", "estado")
    list_filter = ("estado", "plan")
    search_fields = ("socio__username", "socio__email", "plan__nombre")
    list_select_related = ("socio", "plan")
    autocomplete_fields = ("socio", "plan")


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("membresia", "monto", "fecha", "referencia")
    list_filter = ("fecha",)
    search_fields = ("membresia__socio__username", "referencia")
    list_select_related = ("membresia", "membresia__socio", "membresia__plan")
    autocomplete_fields = ("membresia",)


class SoloLectura(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Clase)
class ClaseAdmin(SoloLectura):
    list_display = ("nombre", "inicio", "cupo_maximo", "activa")
    list_filter = ("activa", "inicio")
    search_fields = ("nombre",)


@admin.register(Reserva)
class ReservaAdmin(SoloLectura):
    list_display = ("socio", "clase", "creada")
    list_filter = ("clase",)
    search_fields = ("socio__username", "clase__nombre")
    list_select_related = ("socio", "clase")


@admin.register(ListaEspera)
class ListaEsperaAdmin(SoloLectura):
    list_display = ("socio", "clase", "creada")
    list_filter = ("clase",)
    search_fields = ("socio__username", "clase__nombre")
    list_select_related = ("socio", "clase")


@admin.register(RegistroAcceso)
class RegistroAccesoAdmin(SoloLectura):
    list_display = ("socio", "operador", "accion", "permitido", "fecha", "motivo")
    list_filter = ("accion", "permitido", "fecha")
    search_fields = ("socio__username", "operador__username", "motivo")
    list_select_related = ("socio", "operador")


@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ("id", "capacidad")
    search_fields = ("id",)

    def has_add_permission(self, request):
        return not Configuracion.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
