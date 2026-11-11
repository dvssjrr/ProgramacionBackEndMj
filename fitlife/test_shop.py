from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from .models import CarritoItem, Membresia, Pago, Pedido, Plan, Producto, User
from .shop import agregar, confirmar_pedido, crear_pedido, simular_pago


class TiendaTests(TestCase):
    def setUp(self):
        self.socio = User.objects.create_user(username="socio", password="Fuerte987!")
        self.otro = User.objects.create_user(username="otro", password="Fuerte987!")
        self.staff = User.objects.create_user(username="staff", role=User.Role.STAFF, password="Fuerte987!")
        self.plan = Plan.objects.create(nombre="Mensual", precio="100.00", duracion_dias=30)
        self.producto = Producto.objects.create(nombre="Botella", precio="15.00", stock=2)

    def test_pedido_y_confirmacion_no_son_cobro_online(self):
        self.client.force_login(self.socio)
        self.assertEqual(self.client.post(f"/carrito/agregar/plan/{self.plan.pk}/").status_code, 302)
        self.client.post(f"/carrito/agregar/producto/{self.producto.pk}/")
        self.client.post(f"/carrito/agregar/producto/{self.producto.pk}/")
        self.assertContains(self.client.get("/carrito/"), "130,00")
        self.client.post("/carrito/solicitar/")
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.total, 130)
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)
        self.assertFalse(Membresia.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 2)
        self.client.force_login(self.staff)
        self.client.post(f"/panel/pedidos/{pedido.pk}/confirmar/")
        pedido.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.CONFIRMADO)
        self.assertEqual(self.producto.stock, 0)
        self.assertEqual(pedido.membresia.fin - pedido.membresia.inicio, timedelta(days=29))
        self.assertEqual(Pago.objects.get(membresia=pedido.membresia).monto, 100)
        self.client.post(f"/panel/pedidos/{pedido.pk}/confirmar/")
        self.assertEqual(Pago.objects.count(), 1)

    def test_simulador_tarjeta_no_cobra_confirma_ni_guarda_datos_de_tarjeta(self):
        self.client.force_login(self.socio)
        agregar(self.socio, "plan", self.plan.pk)
        agregar(self.socio, "producto", self.producto.pk)
        response = self.client.post("/carrito/solicitar/")
        pedido = Pedido.objects.get()
        self.assertRedirects(response, f"/pedidos/{pedido.pk}/pago-simulado/")
        self.assertContains(self.client.get(f"/pedidos/{pedido.pk}/pago-simulado/"), "Tarjeta de crédito")
        self.assertContains(self.client.get(f"/pedidos/{pedido.pk}/pago-simulado/"), "No ingreses número real")
        self.assertContains(self.client.get(f"/pedidos/{pedido.pk}/pago-simulado/"), "Simular aprobación")

        rejected = self.client.post(
            f"/pedidos/{pedido.pk}/pago-simulado/",
            {"metodo": "debito", "resultado": "rechazado", "numero_tarjeta": "4242424242424242", "cvv": "123"},
        )
        self.assertRedirects(rejected, f"/pedidos/{pedido.pk}/pago-simulado/")
        pedido.refresh_from_db()
        self.assertEqual(pedido.metodo_pago_simulado, Pedido.MetodoPagoSimulado.DEBITO)
        self.assertEqual(pedido.resultado_pago_simulado, Pedido.ResultadoPagoSimulado.RECHAZADO)
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)
        self.assertFalse(hasattr(pedido, "numero_tarjeta"))
        self.assertFalse(hasattr(pedido, "cvv"))
        self.assertFalse(Pago.objects.exists())
        self.assertFalse(Membresia.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 2)

        approved = self.client.post(
            f"/pedidos/{pedido.pk}/pago-simulado/",
            {"metodo": "credito", "resultado": "aprobado"},
        )
        self.assertRedirects(approved, f"/pedidos/{pedido.pk}/pago-simulado/")
        pedido.refresh_from_db()
        self.assertEqual(pedido.resultado_pago_simulado, Pedido.ResultadoPagoSimulado.APROBADO)
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)
        self.assertContains(self.client.get(f"/pedidos/{pedido.pk}/pago-simulado/"), "El pedido sigue pendiente")
        self.assertContains(self.client.get(f"/pedidos/{pedido.pk}/pago-simulado/"), "no se mueve dinero")
        self.assertFalse(Pago.objects.exists())
        self.assertFalse(Membresia.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 2)

        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(f"/pedidos/{pedido.pk}/pago-simulado/").status_code, 403)
        self.client.post(f"/panel/pedidos/{pedido.pk}/confirmar/")
        pedido.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.CONFIRMADO)
        self.assertEqual(self.producto.stock, 1)
        self.assertEqual(Pago.objects.count(), 1)

    def test_simulador_protege_propiedad_metodo_y_estado_del_pedido(self):
        agregar(self.socio, "producto", self.producto.pk)
        pedido = crear_pedido(self.socio)
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(f"/pedidos/{pedido.pk}/pago-simulado/").status_code, 404)
        self.assertEqual(
            self.client.post(f"/pedidos/{pedido.pk}/pago-simulado/", {
                "metodo": "bitcoin", "resultado": "aprobado",
            }).status_code, 404,
        )
        self.client.force_login(self.socio)
        invalid = self.client.post(f"/pedidos/{pedido.pk}/pago-simulado/", {
            "metodo": "bitcoin", "resultado": "aprobado",
        })
        self.assertEqual(invalid.status_code, 200)
        self.assertContains(invalid, "Selecciona tarjeta de crédito o débito.")
        pedido.refresh_from_db()
        self.assertEqual(pedido.metodo_pago_simulado, "")
        self.assertEqual(pedido.resultado_pago_simulado, "")
        pedido.estado = Pedido.Estado.CANCELADO
        pedido.save(update_fields=["estado"])
        self.assertEqual(self.client.get(f"/pedidos/{pedido.pk}/pago-simulado/").status_code, 200)
        canceled_attempt = self.client.post(f"/pedidos/{pedido.pk}/pago-simulado/", {
            "metodo": "credito", "resultado": "aprobado",
        })
        self.assertEqual(canceled_attempt.status_code, 200)
        self.assertContains(canceled_attempt, "Solo se pueden simular pagos de pedidos pendientes.")

    def test_stock_insuficiente_no_confirma_ni_activa(self):
        agregar(self.socio, "plan", self.plan.pk)
        agregar(self.socio, "producto", self.producto.pk)
        pedido = crear_pedido(self.socio)
        Producto.objects.filter(pk=self.producto.pk).update(stock=0)
        with self.assertRaises(ValidationError):
            confirmar_pedido(pedido.pk, self.staff)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)
        self.assertFalse(Membresia.objects.exists())
        self.assertFalse(Pago.objects.exists())

    def test_membresia_existente_o_congelada_bloquea_pedido(self):
        agregar(self.socio, "plan", self.plan.pk)
        pedido = crear_pedido(self.socio)
        hoy = timezone.localdate()
        Membresia.objects.create(socio=self.socio, plan=self.plan, inicio=hoy, fin=hoy + timedelta(days=10), estado="congelada")
        with self.assertRaises(ValidationError):
            confirmar_pedido(pedido.pk, self.staff)
        self.assertEqual(Pedido.objects.get(pk=pedido.pk).estado, "pendiente")

    def test_precios_fijados_y_plan_reemplazado(self):
        otro = Plan.objects.create(nombre="Anual", precio=500, duracion_dias=365)
        agregar(self.socio, "plan", self.plan.pk)
        agregar(self.socio, "plan", otro.pk)
        self.assertEqual(CarritoItem.objects.filter(socio=self.socio).count(), 1)
        pedido = crear_pedido(self.socio)
        otro.precio = 999
        otro.duracion_dias = 40
        otro.save()
        confirmar_pedido(pedido.pk, self.staff)
        pedido.refresh_from_db()
        self.assertEqual(pedido.total, 500)
        self.assertEqual(pedido.membresia.fin - pedido.membresia.inicio, timedelta(days=364))

    def test_roles_aislamiento_cancelacion_y_csrf(self):
        self.client.force_login(self.socio)
        self.assertEqual(self.client.get("/panel/pedidos/").status_code, 403)
        self.client.post(f"/carrito/agregar/producto/{self.producto.pk}/")
        self.client.post("/carrito/solicitar/")
        pedido = Pedido.objects.get()
        self.client.get("/carrito/")
        self.client.force_login(self.otro)
        self.assertNotContains(self.client.get("/carrito/"), f"Pedido #{pedido.pk}")
        self.client.post(f"/pedidos/{pedido.pk}/cancelar/")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "pendiente")
        self.client.force_login(self.socio)
        self.client.post(f"/pedidos/{pedido.pk}/cancelar/")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "cancelado")
        self.assertEqual(self.client.get(f"/panel/pedidos/{pedido.pk}/confirmar/").status_code, 405)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/carrito/").status_code, 403)
        self.assertEqual(self.client.post("/panel/gestion/productos/", {"nombre": "Agua", "precio": "5", "stock": 10, "activo": "on"}).status_code, 302)
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.socio)
        self.assertEqual(client.post(f"/carrito/agregar/producto/{self.producto.pk}/").status_code, 403)

    def test_sesiones_separadas_no_comparten_usuarios(self):
        from django.test import Client
        a, b = Client(), Client()
        a.force_login(self.socio)
        b.force_login(self.otro)
        a.post(f"/carrito/agregar/producto/{self.producto.pk}/")
        self.assertContains(a.get("/carrito/"), "Botella")
        self.assertNotContains(b.get("/carrito/"), "Botella")
        self.assertEqual(a.get("/api/perfil/").json()["username"], "socio")
        self.assertEqual(b.get("/api/perfil/").json()["username"], "otro")


class StockConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_dos_pedidos_no_venden_mas_stock(self):
        staff = User.objects.create_user(username="staff", role=User.Role.STAFF)
        users = [User.objects.create_user(username=f"s{i}") for i in range(2)]
        producto = Producto.objects.create(nombre="Última botella", precio=10, stock=1)
        for user in users:
            agregar(user, "producto", producto.pk)
        pedidos = [crear_pedido(user) for user in users]
        barrier = Barrier(2, timeout=15)

        def confirmar(pk):
            close_old_connections()
            try:
                operador = User.objects.get(pk=staff.pk)
                barrier.wait()
                try:
                    confirmar_pedido(pk, operador)
                    return "confirmado"
                except ValidationError:
                    return "pendiente"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(confirmar, [pedido.pk for pedido in pedidos]))
        self.assertCountEqual(results, ["confirmado", "pendiente"])
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 0)
