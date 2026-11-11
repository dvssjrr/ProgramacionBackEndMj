"""Pruebas de sesiones independientes en pestañas del mismo navegador."""

import re
from datetime import timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import Membresia, Plan, RegistroAcceso, User


@override_settings(TAB_SESSION_ISOLATION=True)
class TabSessionTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="pestana1", password="ClaveSegura321!")
        User.objects.create_user(username="pestana2", password="ClaveSegura321!")
        User.objects.create_user(
            username="recepcion", password="ClaveSegura321!", role=User.Role.STAFF
        )

    def _open_session(self, client):
        response = client.get("/")
        match = re.fullmatch(r"/sesion/([0-9a-f]{32})/", response["Location"])
        self.assertIsNotNone(match)
        return match.group(1)

    def _login(self, client, tab_id, username):
        login_url = f"/sesion/{tab_id}/login/"
        response = client.get(login_url)
        self.assertEqual(response.status_code, 200)
        csrf = client.cookies[f"csrftoken_{tab_id}"].value
        response = client.post(login_url, {
            "username": username,
            "password": "ClaveSegura321!",
            "csrfmiddlewaretoken": csrf,
        }, HTTP_X_CSRFTOKEN=csrf, HTTP_REFERER=f"https://testserver{login_url}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/sesion/{tab_id}/panel/")
        self.assertIn(f"sessionid_{tab_id}", client.cookies)

    def test_dos_pestanas_conservan_sesiones_y_cookies_independientes(self):
        navegador = Client(enforce_csrf_checks=True)
        id_primera = self._open_session(navegador)
        id_segunda = self._open_session(navegador)
        self.assertNotEqual(id_primera, id_segunda)

        self._login(navegador, id_primera, "pestana1")
        self._login(navegador, id_segunda, "pestana2")
        self.assertIn(f"sessionid_{id_primera}", navegador.cookies)
        self.assertIn(f"sessionid_{id_segunda}", navegador.cookies)
        panel_primero = navegador.get(f"/sesion/{id_primera}/panel/")
        panel_segundo = navegador.get(f"/sesion/{id_segunda}/panel/")
        perfil_primero = navegador.get(f"/sesion/{id_primera}/api/perfil/")
        perfil_segundo = navegador.get(f"/sesion/{id_segunda}/api/perfil/")
        self.assertContains(panel_primero, "HOLA, PESTANA1")
        self.assertContains(panel_segundo, "HOLA, PESTANA2")
        self.assertEqual(perfil_primero.status_code, 200)
        self.assertEqual(perfil_primero.json()["username"], "pestana1")
        self.assertEqual(perfil_segundo.status_code, 200)
        self.assertEqual(perfil_segundo.json()["username"], "pestana2")
        self.assertEqual(navegador.get(f"/sesion/{id_primera}/api/clases/").status_code, 200)
        qr = navegador.get(f"/sesion/{id_primera}/api/perfil/qr/")
        self.assertEqual(qr.status_code, 200)
        self.assertEqual(qr["Content-Type"], "image/png")
        self.assertContains(panel_primero, f"/sesion/{id_primera}/tienda/")
        self.assertContains(panel_primero, 'data-session-base="/sesion/' + id_primera + '"')
        self.assertContains(panel_primero, 'href="/" target="_blank" rel="noopener">Nueva sesión')
        self.assertContains(panel_primero, "fitlife/js/panel.js?v=20261111-2")

    def test_control_de_ingreso_solo_personal_y_registra_entrada_y_salida(self):
        navegador = Client(enforce_csrf_checks=True)
        socio_tab = self._open_session(navegador)
        staff_tab = self._open_session(navegador)
        self._login(navegador, socio_tab, "pestana1")
        self._login(navegador, staff_tab, "recepcion")

        self.assertEqual(navegador.get(f"/sesion/{staff_tab}/panel/ingreso/").status_code, 200)
        self.assertEqual(navegador.get(f"/sesion/{socio_tab}/panel/ingreso/").status_code, 403)
        self.assertEqual(
            navegador.get(f"/sesion/{staff_tab}/api/aforo/").status_code, 200
        )

        hoy = timezone.localdate()
        plan = Plan.objects.create(nombre="Mensual", precio=100, duracion_dias=30)
        Membresia.objects.create(
            socio=User.objects.get(username="pestana1"),
            plan=plan,
            inicio=hoy,
            fin=hoy + timedelta(days=30),
        )
        token = navegador.get(f"/sesion/{socio_tab}/api/perfil/").json()["qr_token"]
        csrf = navegador.cookies[f"csrftoken_{staff_tab}"].value
        scan_url = f"/sesion/{staff_tab}/api/accesos/escanear/"
        response = navegador.post(
            scan_url,
            {"token": token, "accion": "entrada"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
            HTTP_REFERER=f"https://testserver/sesion/{staff_tab}/panel/ingreso/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["permitido"])
        self.assertEqual(
            navegador.get(f"/sesion/{staff_tab}/api/aforo/").json()["dentro"], 1
        )

        response = navegador.post(
            scan_url,
            {"token": token, "accion": "salida"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
            HTTP_REFERER=f"https://testserver/sesion/{staff_tab}/panel/ingreso/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["permitido"])
        self.assertEqual(RegistroAcceso.objects.count(), 2)

    def test_post_sin_prefijo_de_sesion_se_rechaza(self):
        response = Client().post("/login/", {"username": "pestana1"})
        self.assertEqual(response.status_code, 400)
