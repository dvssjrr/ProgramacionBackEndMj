"""Modelos relacionales y restricciones de socios, clases, accesos y tienda."""

from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class FitlifeUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        STAFF = "staff", "Recepción"
        INSTRUCTOR = "instructor", "Instructor"
        SOCIO = "socio", "Socio"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.SOCIO)
    # La presencia cambia al registrar una entrada o salida, no desde formularios.
    dentro = models.BooleanField(default=False, editable=False)
    objects = FitlifeUserManager()


class Plan(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    duracion_dias = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Membresia(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        VENCIDA = "vencida", "Vencida"
        CONGELADA = "congelada", "Congelada"

    # PROTECT conserva el historial si el socio o el plan tienen registros asociados.
    socio = models.ForeignKey(User, on_delete=models.PROTECT, related_name="membresias")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="membresias")
    inicio = models.DateField()
    fin = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVA)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(fin__gte=F("inicio")), name="fitlife_membresia_fechas")]

    def clean(self):
        if self.inicio and self.fin and self.fin < self.inicio:
            raise ValidationError("La fecha final no puede ser anterior a la inicial.")
        if self.socio_id and (self.socio.role != User.Role.SOCIO or not self.socio.is_active):
            raise ValidationError({"socio": "Selecciona un socio activo."})

    @property
    def habilitada(self):
        hoy = timezone.localdate()
        return self.estado == self.Estado.ACTIVA and self.inicio <= hoy <= self.fin

    @property
    def estado_efectivo(self):
        # La fecha vencida se refleja al consultar, sin modificar el estado guardado.
        if self.estado == self.Estado.ACTIVA and self.fin < timezone.localdate():
            return self.Estado.VENCIDA
        return self.estado

    def __str__(self):
        return f"{self.socio} - {self.plan}"


class Pago(models.Model):
    membresia = models.ForeignKey(Membresia, on_delete=models.PROTECT, related_name="pagos")
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    fecha = models.DateTimeField(default=timezone.now)
    referencia = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"{self.membresia}: {self.monto}"


class Producto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class CarritoItem(models.Model):
    socio = models.ForeignKey(User, on_delete=models.CASCADE, related_name="carrito")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, null=True, blank=True)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        # Cada linea representa un plan o producto; solo puede haber un plan por socio.
        constraints = [
            models.CheckConstraint(condition=(Q(plan__isnull=False, producto__isnull=True, cantidad=1) | Q(plan__isnull=True, producto__isnull=False, cantidad__gte=1)), name="fitlife_carrito_item_valido"),
            models.UniqueConstraint(fields=["socio"], condition=Q(plan__isnull=False), name="fitlife_carrito_un_plan"),
            models.UniqueConstraint(fields=["socio", "producto"], condition=Q(producto__isnull=False), name="fitlife_carrito_producto_unico"),
        ]

    @property
    def articulo(self):
        return self.plan or self.producto

    @property
    def subtotal(self):
        return self.articulo.precio * self.cantidad


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de pago"
        CONFIRMADO = "confirmado", "Pago confirmado"
        CANCELADO = "cancelado", "Cancelado"

    socio = models.ForeignKey(User, on_delete=models.PROTECT, related_name="pedidos")
    creado = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    confirmado_por = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="pedidos_confirmados")
    confirmado_en = models.DateTimeField(null=True, blank=True)
    membresia = models.OneToOneField(Membresia, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ["-creado", "-pk"]


class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="items")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, null=True, blank=True)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    # Estos datos conservan los valores del articulo al momento de crear el pedido.
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    duracion_dias = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(Q(plan__isnull=False, producto__isnull=True, cantidad=1, duracion_dias__gte=1) | Q(plan__isnull=True, producto__isnull=False, cantidad__gte=1, duracion_dias__isnull=True)), name="fitlife_pedido_item_valido"),
        ]

    @property
    def subtotal(self):
        return self.precio * self.cantidad


class Clase(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    inicio = models.DateTimeField()
    cupo_maximo = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    activa = models.BooleanField(default=True)
    instructor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="clases_asignadas", limit_choices_to={"role": User.Role.INSTRUCTOR},
    )

    class Meta:
        ordering = ["inicio", "pk"]

    def __str__(self):
        return f"{self.nombre} - {self.inicio}"


class Reserva(models.Model):
    socio = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reservas")
    clase = models.ForeignKey(Clase, on_delete=models.PROTECT, related_name="reservas")
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["socio", "clase"], name="fitlife_reserva_unica")]

    def __str__(self):
        return f"{self.socio} - {self.clase}"


class ListaEspera(models.Model):
    socio = models.ForeignKey(User, on_delete=models.PROTECT, related_name="esperas")
    clase = models.ForeignKey(Clase, on_delete=models.PROTECT, related_name="esperas")
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        # El orden de creacion determina quien recibe la siguiente plaza disponible.
        ordering = ["creada", "pk"]
        constraints = [models.UniqueConstraint(fields=["socio", "clase"], name="fitlife_espera_unica")]

    def __str__(self):
        return f"{self.socio} - {self.clase}"


class RegistroAcceso(models.Model):
    class Accion(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SALIDA = "salida", "Salida"

    socio = models.ForeignKey(User, on_delete=models.PROTECT, related_name="accesos")
    operador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="accesos_operados")
    accion = models.CharField(max_length=7, choices=Accion.choices)
    permitido = models.BooleanField()
    motivo = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-pk"]

    def __str__(self):
        return f"{self.socio} - {self.accion} - {self.fecha}"


class Configuracion(models.Model):
    capacidad = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])

    def clean(self):
        if self.pk != 1:
            raise ValidationError("Solo se permite la configuración principal (id 1).")

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "Configuración del gimnasio"
