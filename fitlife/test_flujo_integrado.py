"""Comprobación de los flujos principales con sesiones aisladas y datos temporales."""

from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from .models import Clase, Membresia, Plan, Reserva, User


class FlujoIntegradoTests(TestCase):
    def test_registro_acceso_aforo_reserva_espera_y_cancelacion(self):
        admin = User.objects.create_superuser("admin", password="ClaveSegura123!")
        recepcion = Client()
        recepcion.force_login(admin)
        hoy = timezone.localdate()
        plan = Plan.objects.create(nombre="Mensual", precio=100, duracion_dias=30)
        clase = Clase.objects.create(
            nombre="Yoga", inicio=timezone.now() + timedelta(days=1), cupo_maximo=1
        )
        clientes = []
        socios = []
        # Cada cliente conserva una sesion independiente y valida CSRF.
        for username in ("socio1", "socio2"):
            cliente = Client(enforce_csrf_checks=True)
            cliente.get("/registro/")
            token = cliente.cookies["csrftoken"].value
            respuesta = cliente.post("/registro/", {
                "username": username, "email": f"{username}@example.com",
                "password1": "UnaClaveSegura321!", "password2": "UnaClaveSegura321!",
                "csrfmiddlewaretoken": token,
            })
            self.assertRedirects(respuesta, "/panel/")
            socio = User.objects.get(username=username)
            respuesta = recepcion.post("/panel/gestion/membresias/", {
                "socio": socio.pk, "plan": plan.pk, "inicio": str(hoy),
                "fin": str(hoy + timedelta(days=30)), "estado": "activa",
            })
            self.assertEqual(respuesta.status_code, 302)
            clientes.append(cliente)
            socios.append(socio)

        codigo = clientes[0].get("/api/perfil/").json()["qr_token"]
        acceso = recepcion.post("/api/accesos/escanear/", {
            "token": codigo, "accion": "entrada",
        })
        self.assertEqual(acceso.status_code, 200)
        self.assertEqual(recepcion.get("/api/aforo/").json()["dentro"], 1)
        self.assertEqual(recepcion.post("/api/accesos/escanear/", {
            "token": codigo, "accion": "salida",
        }).status_code, 200)
        self.assertEqual(recepcion.get("/api/aforo/").json()["dentro"], 0)

        # El primer socio ocupa la plaza; el segundo debe pasar a espera.
        url = f"/api/clases/{clase.pk}/"
        for cliente, estado in zip(clientes, ("reservada", "espera")):
            csrf = cliente.cookies["csrftoken"].value
            respuesta = cliente.post(url + "reservar/", HTTP_X_CSRFTOKEN=csrf)
            self.assertEqual(respuesta.status_code, 201)
            self.assertEqual(respuesta.json()["estado"], estado)
        csrf = clientes[0].cookies["csrftoken"].value
        self.assertEqual(clientes[0].post(url + "cancelar/", HTTP_X_CSRFTOKEN=csrf).status_code, 200)
        self.assertTrue(Reserva.objects.filter(clase=clase, socio=socios[1]).exists())

        Membresia.objects.filter(socio=socios[0]).update(estado=Membresia.Estado.CONGELADA)
        respuesta = recepcion.post("/api/accesos/escanear/", {
            "token": codigo, "accion": "entrada",
        })
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(User.objects.get(pk=socios[0].pk).dentro)
