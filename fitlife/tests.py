from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.core import signing
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Clase, Configuracion, ListaEspera, Membresia, Pago, Plan, RegistroAcceso, Reserva, User
from .views import QR_SALT
from .services import reservar


class FitLifeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.socio = User.objects.create_user(username="socio", password="segura123!")
        self.otro = User.objects.create_user(username="otro", password="segura123!")
        self.staff = User.objects.create_user(username="staff", password="segura123!", role=User.Role.STAFF)
        self.plan = Plan.objects.create(nombre="Mensual", precio=100, duracion_dias=30)
        hoy = timezone.localdate()
        self.membresia = Membresia.objects.create(socio=self.socio, plan=self.plan, inicio=hoy, fin=hoy + timedelta(days=30))
        Membresia.objects.create(socio=self.otro, plan=self.plan, inicio=hoy, fin=hoy + timedelta(days=30))
        self.clase = Clase.objects.create(nombre="Yoga", inicio=timezone.now() + timedelta(days=1), cupo_maximo=1)

    def token(self, user=None):
        return signing.dumps((user or self.socio).pk, salt=QR_SALT)

    def scan(self, accion, token=None):
        self.client.force_authenticate(self.staff)
        return self.client.post("/api/accesos/escanear/", {"token": token or self.token(), "accion": accion}, format="json")

    def test_acceso_entrada_salida_y_denegaciones(self):
        self.assertEqual(self.scan("entrada").status_code, 200)
        self.assertEqual(self.scan("entrada").status_code, 403)
        self.assertEqual(self.client.get("/api/aforo/").data["dentro"], 1)
        self.membresia.estado = Membresia.Estado.CONGELADA
        self.membresia.save()
        self.assertEqual(self.scan("salida").status_code, 200)
        self.assertEqual(self.scan("entrada").status_code, 403)
        self.assertEqual(self.client.get("/api/aforo/").data["porcentaje"], 0)
        self.assertEqual(RegistroAcceso.objects.count(), 4)

    def test_expirada_o_futura_no_permite_entrada(self):
        self.membresia.inicio = timezone.localdate() - timedelta(days=2)
        self.membresia.fin = timezone.localdate() - timedelta(days=1)
        self.membresia.save()
        self.assertEqual(self.scan("entrada").status_code, 403)
        self.client.force_authenticate(self.socio)
        self.assertEqual(self.client.get("/api/membresias/").data[0]["estado_efectivo"], "vencida")
        self.membresia.inicio = timezone.localdate() + timedelta(days=1)
        self.membresia.fin = timezone.localdate() + timedelta(days=2)
        self.membresia.save()
        self.assertEqual(self.scan("entrada").status_code, 403)

    def test_qr_invalido_no_modifica_presencia(self):
        self.assertEqual(self.scan("entrada", "invalido").status_code, 400)
        self.assertFalse(User.objects.get(pk=self.socio.pk).dentro)
        self.assertFalse(RegistroAcceso.objects.exists())

    def test_qr_caducado_y_png(self):
        from unittest.mock import patch
        from django.core.signing import TimestampSigner
        with patch.object(TimestampSigner, "timestamp", return_value="1"):
            token = self.token()
        self.assertEqual(self.scan("entrada", token).status_code, 400)
        self.client.force_authenticate(self.socio)
        response = self.client.get("/api/perfil/qr/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertIn("no-store", response["Cache-Control"])

    def test_lista_espera_promueve_al_cancelar(self):
        self.client.force_authenticate(self.socio)
        url = f"/api/clases/{self.clase.pk}/"
        self.assertEqual(self.client.post(url + "reservar/").data["estado"], "reservada")
        self.assertEqual(self.client.post(url + "reservar/").status_code, 400)
        self.client.force_authenticate(self.otro)
        self.assertEqual(self.client.post(url + "reservar/").data["estado"], "espera")
        self.client.force_authenticate(self.socio)
        self.assertEqual(self.client.post(url + "cancelar/").status_code, 200)
        self.assertTrue(Reserva.objects.filter(socio=self.otro, clase=self.clase).exists())
        self.assertFalse(ListaEspera.objects.exists())

    def test_promocion_omite_membresia_congelada(self):
        Reserva.objects.create(socio=self.socio, clase=self.clase)
        ListaEspera.objects.create(socio=self.otro, clase=self.clase)
        Membresia.objects.filter(socio=self.otro).update(estado=Membresia.Estado.CONGELADA)
        self.client.force_authenticate(self.socio)
        self.client.post(f"/api/clases/{self.clase.pk}/cancelar/")
        self.assertFalse(Reserva.objects.exists())
        self.assertFalse(ListaEspera.objects.exists())

    def test_ampliacion_promueve_y_reduccion_invalida(self):
        Reserva.objects.create(socio=self.socio, clase=self.clase)
        ListaEspera.objects.create(socio=self.otro, clase=self.clase)
        self.client.force_authenticate(self.staff)
        url = f"/api/clases/{self.clase.pk}/"
        self.assertEqual(self.client.patch(url, {"cupo_maximo": 2}, format="json").status_code, 200)
        self.assertEqual(Reserva.objects.count(), 2)
        self.assertEqual(self.client.patch(url, {"cupo_maximo": 1}, format="json").status_code, 400)

    def test_permisos_y_aislamiento(self):
        pago = Pago.objects.create(membresia=self.membresia, monto=100)
        self.assertEqual(self.client.get("/api/planes/").status_code, 403)
        self.client.force_authenticate(self.otro)
        self.assertEqual(self.client.get(f"/api/pagos/{pago.pk}/").status_code, 404)
        self.assertEqual(self.client.get("/api/aforo/").status_code, 403)
        self.assertEqual(self.client.post("/api/planes/", {"nombre": "X"}, format="json").status_code, 403)
        self.assertEqual(self.client.post("/api/accesos/escanear/", {"token": self.token(), "accion": "entrada"}, format="json").status_code, 403)

    def test_equipo_gestiona_plan_membresia_pago_y_clase(self):
        self.client.force_authenticate(self.staff)
        plan = self.client.post("/api/planes/", {"nombre": "Anual", "precio": "1200.00", "duracion_dias": 365}, format="json")
        self.assertEqual(plan.status_code, 201)
        membresia = self.client.post("/api/membresias/", {
            "socio": self.socio.pk, "plan": plan.data["id"],
            "inicio": str(timezone.localdate()), "fin": str(timezone.localdate() + timedelta(days=365)),
            "estado": "activa",
        }, format="json")
        self.assertEqual(membresia.status_code, 201)
        pago = self.client.post("/api/pagos/", {"membresia": membresia.data["id"], "monto": "1200.00"}, format="json")
        self.assertEqual(pago.status_code, 201)
        self.assertEqual(self.client.patch(f"/api/membresias/{membresia.data['id']}/", {"estado": "congelada"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/pagos/{pago.data['id']}/").status_code, 204)
        clase = self.client.post("/api/clases/", {
            "nombre": "Spinning", "inicio": (timezone.now() + timedelta(days=1)).isoformat(), "cupo_maximo": 4,
        }, format="json")
        self.assertEqual(clase.status_code, 201)
        self.assertEqual(self.client.delete(f"/api/clases/{clase.data['id']}/").status_code, 204)

    def test_no_reservar_sin_vigencia_o_clase_iniciada(self):
        self.membresia.estado = Membresia.Estado.CONGELADA
        self.membresia.save()
        self.client.force_authenticate(self.socio)
        url = f"/api/clases/{self.clase.pk}/reservar/"
        self.assertEqual(self.client.post(url).status_code, 400)
        self.membresia.estado = Membresia.Estado.ACTIVA
        self.membresia.save()
        self.clase.inicio = timezone.now() - timedelta(minutes=1)
        self.clase.save()
        self.assertEqual(self.client.post(url).status_code, 400)

    def test_capacidad_y_registros_protegidos(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/aforo/").data["capacidad"], 100)
        Configuracion.objects.filter(pk=1).update(capacidad=0)
        self.assertEqual(self.client.get("/api/aforo/").status_code, 503)
        self.assertEqual(self.client.delete(f"/api/planes/{self.plan.pk}/").status_code, 400)
        Reserva.objects.create(socio=self.socio, clase=self.clase)
        self.assertEqual(self.client.delete(f"/api/clases/{self.clase.pk}/").status_code, 400)

    def test_sesion_csrf_para_reservas(self):
        cliente = APIClient(enforce_csrf_checks=True)
        self.assertTrue(cliente.login(username="socio", password="segura123!"))
        url = f"/api/clases/{self.clase.pk}/reservar/"
        self.assertEqual(cliente.post(url).status_code, 403)
        cliente.get("/")
        token = cliente.cookies["csrftoken"].value
        self.assertEqual(cliente.post(url, HTTP_X_CSRFTOKEN=token).status_code, 201)

    def test_admin_y_frontend_disponibles(self):
        self.client.force_authenticate(user=None)
        self.assertTrue(self.client.login(username="socio", password="segura123!"))
        self.assertEqual(self.client.get("/").status_code, 200)
        self.client.logout()
        User.objects.create_superuser(username="admin", password="segura123!")
        self.assertTrue(self.client.login(username="admin", password="segura123!"))
        self.assertEqual(self.client.get("/admin/").status_code, 404)
        self.assertEqual(self.client.get("/panel/usuarios/").status_code, 200)

    def test_superusuario_administra_y_crea_socio(self):
        admin = User.objects.create_superuser(username="admin", password="segura123!")
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.client.force_authenticate(admin)
        perfil = self.client.get("/api/perfil/").data
        self.assertTrue(perfil["es_equipo"])
        self.assertTrue(perfil["puede_usar_admin"])
        self.assertFalse(perfil["es_socio"])
        self.assertEqual(perfil["rol_visible"], "Administrador")
        self.client.force_authenticate(user=None)
        self.assertTrue(self.client.login(username="admin", password="segura123!"))
        formulario = self.client.get("/panel/usuarios/")
        self.assertEqual(formulario.status_code, 200)
        self.assertContains(formulario, 'name="role"')
        response = self.client.post("/panel/usuarios/", {
            "username": "socio_nuevo", "password1": "UnaClaveSegura321!",
            "password2": "UnaClaveSegura321!", "role": User.Role.SOCIO,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.get(username="socio_nuevo").role, User.Role.SOCIO)

    def test_paginas_administrativas_y_permisos(self):
        admin = User.objects.create_superuser(username="admin", password="segura123!")
        self.client.force_login(admin)
        for path in ("/panel/usuarios/", "/panel/gestion/planes/", "/panel/gestion/membresias/",
                     "/panel/gestion/pagos/", "/panel/configuracion/", "/panel/reportes/"):
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.assertNotContains(self.client.get("/panel/"), "/admin/")
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/panel/usuarios/").status_code, 403)
        self.assertEqual(self.client.get("/panel/configuracion/").status_code, 403)
        self.assertEqual(self.client.get("/panel/gestion/planes/").status_code, 200)
        self.client.force_login(self.socio)
        for path in ("/panel/usuarios/", "/panel/configuracion/", "/panel/gestion/planes/", "/panel/reportes/"):
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_operaciones_planes_membresias_pagos(self):
        self.client.force_login(self.staff)
        response = self.client.post("/panel/gestion/planes/", {
            "nombre": "Anual", "precio": "1200.00", "duracion_dias": 365, "activo": "on",
        })
        self.assertEqual(response.status_code, 302)
        plan = Plan.objects.get(nombre="Anual")
        response = self.client.post("/panel/gestion/membresias/", {
            "socio": self.socio.pk, "plan": plan.pk, "inicio": "2030-01-01", "fin": "2030-12-31", "estado": "activa",
        })
        self.assertEqual(response.status_code, 302)
        membresia = Membresia.objects.get(plan=plan)
        response = self.client.post("/panel/gestion/pagos/", {
            "membresia": membresia.pk, "monto": "1200.00", "fecha": "2030-01-01T10:00", "referencia": "test",
        })
        self.assertEqual(response.status_code, 302)
        pago = Pago.objects.get(membresia=membresia)
        self.assertEqual(self.client.get(f"/panel/gestion/planes/{plan.pk}/eliminar/").status_code, 405)
        self.client.post(f"/panel/gestion/planes/{plan.pk}/eliminar/")
        self.assertTrue(Plan.objects.filter(pk=plan.pk).exists())
        self.client.post(f"/panel/gestion/pagos/{pago.pk}/eliminar/")
        self.assertFalse(Pago.objects.filter(pk=pago.pk).exists())

    def test_edicion_usuario_no_permite_escalar_superusuario(self):
        admin = User.objects.create_user(username="gestor", role=User.Role.ADMIN)
        principal = User.objects.create_superuser(username="principal")
        self.client.force_login(admin)
        self.assertEqual(self.client.get(f"/panel/usuarios/{principal.pk}/").status_code, 403)
        response = self.client.post(f"/panel/usuarios/{self.otro.pk}/", {
            "first_name": "Socio", "role": "socio", "is_active": "on",
            "is_superuser": "on", "is_staff": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.otro.refresh_from_db()
        self.assertFalse(self.otro.is_superuser)
        self.assertFalse(self.otro.is_staff)
        response = self.client.post(f"/panel/usuarios/{self.otro.pk}/", {"role": "admin", "is_active": "on"})
        self.assertContains(response, "No se puede cambiar el rol")
        self.otro.refresh_from_db()
        self.assertEqual(self.otro.role, User.Role.SOCIO)

    def test_configuracion_clase_y_validaciones_administrativas(self):
        admin = User.objects.create_superuser(username="admin", password="segura123!")
        self.client.force_login(admin)
        self.assertEqual(self.client.post("/panel/configuracion/", {"capacidad": 75}).status_code, 302)
        self.assertEqual(Configuracion.objects.get(pk=1).capacidad, 75)
        response = self.client.post("/panel/gestion/planes/", {})
        self.assertTrue(response.context["form"].errors)
        Reserva.objects.create(clase=self.clase, socio=self.socio)
        self.assertEqual(self.client.get(f"/panel/clases/{self.clase.pk}/eliminar/").status_code, 405)
        self.client.post(f"/panel/clases/{self.clase.pk}/eliminar/")
        self.assertTrue(Clase.objects.filter(pk=self.clase.pk).exists())
        self.assertContains(self.client.get("/panel/clases/"), "No se puede eliminar la clase")

    def test_paginas_personalizadas_de_errores_y_csrf(self):
        from django.test import override_settings
        with override_settings(DEBUG=False):
            self.assertContains(self.client.get("/admin/"), "FITLIFE", status_code=404)
            self.client.force_login(self.socio)
            self.assertContains(self.client.get("/panel/usuarios/"), "FITLIFE", status_code=403)
        cliente = APIClient(enforce_csrf_checks=True)
        response = cliente.post("/login/", {"username": "x", "password": "x"})
        self.assertContains(response, "Tu sesión de seguridad ha caducado", status_code=403)

    def test_perfil_socio_y_superusuario_existente(self):
        self.client.force_authenticate(self.socio)
        perfil = self.client.get("/api/perfil/").data
        self.assertTrue(perfil["es_socio"])
        self.assertFalse(perfil["es_equipo"])
        self.assertFalse(perfil["puede_usar_admin"])
        admin = User.objects.create_superuser(username="admin", password="segura123!", role=User.Role.SOCIO)
        self.client.force_authenticate(admin)
        perfil = self.client.get("/api/perfil/").data
        self.assertTrue(perfil["es_equipo"])
        self.assertFalse(perfil["es_socio"])
        self.assertEqual(perfil["rol_visible"], "Administrador")

    def test_inicio_publico_y_registro_crea_solo_socio(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registrarse")
        self.assertContains(response, self.plan.nombre)
        self.assertEqual(self.client.get("/panel/").status_code, 302)
        response = self.client.post("/registro/", {
            "username": "nueva", "email": "nueva@example.com",
            "password1": "UnaClaveSegura321!", "password2": "UnaClaveSegura321!",
            "role": "admin", "is_superuser": "on", "is_staff": "on",
        })
        self.assertRedirects(response, "/panel/")
        usuario = User.objects.get(username="nueva")
        self.assertEqual(usuario.role, User.Role.SOCIO)
        self.assertFalse(usuario.is_superuser)
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.membresias.exists())
        self.assertContains(self.client.get("/panel/"), "Aún no tienes un plan activo")

    def test_instructor_solo_ve_sus_clases_y_sus_alumnos(self):
        instructor = User.objects.create_user(username="instructor", role=User.Role.INSTRUCTOR)
        otro_instructor = User.objects.create_user(username="otro_instructor", role=User.Role.INSTRUCTOR)
        self.clase.inicio = timezone.now()
        self.clase.instructor = instructor
        self.clase.save()
        Reserva.objects.create(clase=self.clase, socio=self.socio)
        otra_clase = Clase.objects.create(nombre="Privada", inicio=timezone.now(), cupo_maximo=1, instructor=otro_instructor)
        Reserva.objects.create(clase=otra_clase, socio=self.otro)
        self.client.force_login(instructor)
        response = self.client.get("/panel/")
        self.assertContains(response, "Yoga")
        self.assertContains(response, "socio")
        self.assertNotContains(response, "Privada")
        self.assertNotContains(response, "otro</li>")
        self.assertEqual(self.client.get("/panel/clases/").status_code, 403)
        self.assertEqual(self.client.get("/api/accesos/").status_code, 403)

    def test_gestion_clases_y_proteccion_de_cupos(self):
        instructor = User.objects.create_user(username="instructor", role=User.Role.INSTRUCTOR)
        self.client.force_login(self.staff)
        response = self.client.post("/panel/clases/", {
            "nombre": "Pilates", "descripcion": "Movilidad", "inicio": "2030-01-01T10:00",
            "cupo_maximo": 2, "instructor": instructor.pk, "activa": "on",
        })
        self.assertRedirects(response, "/panel/clases/")
        clase = Clase.objects.get(nombre="Pilates")
        self.assertEqual(clase.instructor, instructor)
        Reserva.objects.create(clase=clase, socio=self.socio)
        Reserva.objects.create(clase=clase, socio=self.otro)
        response = self.client.post(f"/panel/clases/{clase.pk}/", {
            "nombre": "Pilates", "descripcion": "Movilidad", "inicio": "2030-01-01T10:00",
            "cupo_maximo": 1, "instructor": instructor.pk, "activa": "on",
        })
        self.assertContains(response, "El cupo no puede ser inferior")
        clase.refresh_from_db()
        self.assertEqual(clase.cupo_maximo, 2)

    def test_login_redirige_al_panel_y_logout_a_inicio(self):
        response = self.client.post("/login/", {"username": "socio", "password": "segura123!"})
        self.assertRedirects(response, "/panel/")
        response = self.client.post("/logout/")
        self.assertRedirects(response, "/")


class ReservaConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_solicitudes_simultaneas_no_exceden_cupo(self):
        plan = Plan.objects.create(nombre="Plan", precio=100, duracion_dias=30)
        clase = Clase.objects.create(nombre="Yoga", inicio=timezone.now() + timedelta(days=1), cupo_maximo=1)
        usuarios = [User.objects.create_user(username=f"socio{i}") for i in range(2)]
        for usuario in usuarios:
            Membresia.objects.create(socio=usuario, plan=plan, inicio=timezone.localdate(), fin=timezone.localdate() + timedelta(days=1))
        barrera = Barrier(2, timeout=10)

        def solicitud(usuario_id):
            close_old_connections()
            try:
                socio = User.objects.get(pk=usuario_id)
                barrera.wait()
                return reservar(clase.pk, socio)[0]
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(solicitud, [usuario.pk for usuario in usuarios]))
        self.assertCountEqual(resultados, ["reservada", "espera"])
        self.assertEqual(Reserva.objects.filter(clase=clase).count(), 1)
        self.assertEqual(ListaEspera.objects.filter(clase=clase).count(), 1)
