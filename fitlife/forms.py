"""Formularios y validaciones de las páginas administrativas de FitLife."""

from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.utils import timezone

from .models import Clase, Configuracion, Membresia, Pago, Plan, Producto, User


PASSWORD_HELP = (
    "Mínimo 12 caracteres; incluye minúscula, mayúscula, número y símbolo. "
    "No uses una contraseña común ni parecida a tus datos."
)


def _configure_password_fields(form):
    """Muestra requisitos y aplica pistas nativas a las dos entradas de clave."""
    form.fields["password1"].help_text = PASSWORD_HELP
    for name in ("password1", "password2"):
        form.fields[name].widget.attrs.update({
            "minlength": 12,
            "required": True,
            "autocomplete": "new-password",
        })


class RegistroForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_password_fields(self)


class ClaseForm(forms.ModelForm):
    # Usa el formato que envia el selector de fecha y hora del navegador.
    inicio = forms.DateTimeField(
        label="Inicio",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = Clase
        fields = ("nombre", "descripcion", "inicio", "cupo_maximo", "instructor", "activa")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["instructor"].queryset = User.objects.filter(role=User.Role.INSTRUCTOR, is_active=True)
        original = self.instance.inicio if self.instance.pk else None
        minimo = timezone.localtime(original) if original and original < timezone.now() else timezone.localtime()
        self.fields["inicio"].widget.attrs["min"] = minimo.strftime("%Y-%m-%dT%H:%M")

    def clean_inicio(self):
        inicio = self.cleaned_data["inicio"]
        if inicio < timezone.now():
            original = self.instance.inicio if self.instance.pk else None
            if not original or inicio != timezone.localtime(original).replace(second=0, microsecond=0):
                raise forms.ValidationError("La fecha y hora de la clase deben ser futuras.")
        return inicio


class UsuarioCrearForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "role")
        labels = {"role": "Rol"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_password_fields(self)


class UsuarioEditarForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "role", "is_active")
        labels = {"is_active": "Cuenta activa", "role": "Rol"}

    def __init__(self, *args, actor, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        if self.instance.is_superuser:
            self.fields["role"].disabled = True
            self.fields["is_active"].disabled = True

    def clean(self):
        data = super().clean()
        # Evita perder el acceso propio o alterar relaciones historicas de un socio.
        if self.instance.pk == self.actor.pk and (not data.get("is_active") or data.get("role") != self.instance.role):
            raise forms.ValidationError("No puedes desactivar tu cuenta ni cambiar tu propio rol.")
        if self.instance.dentro and not data.get("is_active"):
            self.add_error("is_active", "Registra primero la salida del usuario.")
        if self.instance.role == User.Role.SOCIO and data.get("role") != User.Role.SOCIO:
            if self.instance.dentro or self.instance.membresias.exists() or self.instance.reservas.exists() or self.instance.esperas.exists() or self.instance.pedidos.exists():
                self.add_error("role", "No se puede cambiar el rol de un socio con membresías o inscripciones.")
        if self.instance.role == User.Role.INSTRUCTOR and data.get("role") != User.Role.INSTRUCTOR and self.instance.clases_asignadas.exists():
            self.add_error("role", "Reasigna las clases antes de cambiar el rol del instructor.")
        return data


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ("nombre", "descripcion", "precio", "duracion_dias", "activo")
        labels = {"duracion_dias": "Duración en días"}


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ("nombre", "descripcion", "precio", "stock", "activo")


class MembresiaForm(forms.ModelForm):
    class Meta:
        model = Membresia
        fields = ("socio", "plan", "inicio", "fin", "estado")
        widgets = {
            "inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["socio"].queryset = User.objects.filter(role=User.Role.SOCIO, is_active=True).order_by("username")
        hoy = timezone.localdate()
        inicio_original = self.instance.inicio if self.instance.pk else None
        fin_original = self.instance.fin if self.instance.pk else None
        self.fields["inicio"].widget.attrs["min"] = min(hoy, inicio_original or hoy).isoformat()
        self.fields["fin"].widget.attrs["min"] = min(hoy, fin_original or hoy).isoformat()

    def clean_inicio(self):
        inicio = self.cleaned_data["inicio"]
        if inicio < timezone.localdate():
            original = self.instance.inicio if self.instance.pk else None
            if inicio != original:
                raise forms.ValidationError("La membresía no puede comenzar antes de hoy.")
        return inicio

    def clean_fin(self):
        fin = self.cleaned_data["fin"]
        if fin < timezone.localdate():
            original = self.instance.fin if self.instance.pk else None
            if fin != original:
                raise forms.ValidationError("La membresía no puede terminar antes de hoy.")
        return fin


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ("membresia", "monto", "fecha", "referencia")
        widgets = {"fecha": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoy = timezone.localdate()
        original = self.instance.fecha if self.instance.pk else None
        if original and timezone.localtime(original).date() < hoy:
            minimo = timezone.localtime(original).strftime("%Y-%m-%dT%H:%M")
        else:
            minimo = f"{hoy.isoformat()}T00:00"
        self.fields["fecha"].widget.attrs["min"] = minimo

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if timezone.localtime(fecha).date() < timezone.localdate():
            original = self.instance.fecha if self.instance.pk else None
            if not original or fecha != timezone.localtime(original).replace(second=0, microsecond=0):
                raise forms.ValidationError("La fecha del pago no puede ser anterior a hoy.")
        return fecha


class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = ("capacidad",)
        labels = {"capacidad": "Capacidad máxima de personas"}
