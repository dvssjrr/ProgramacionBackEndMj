from django.apps import apps
from django.test import TestCase
from django.urls import reverse

from .admin import fitlife_admin
from .models import Plan, User


class AdminEvaluacionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("evaluador", password="ClaveSegura123!")
        self.socio = User.objects.create_user("socio", password="ClaveSegura123!")
        self.plan = Plan.objects.create(nombre="Mensual", precio=100, duracion_dias=30)

    def test_todos_los_modelos_del_caso_estan_registrados(self):
        self.assertEqual(set(apps.get_app_config("fitlife").get_models()), set(fitlife_admin._registry))

    def test_solo_superusuario_accede_y_se_muestra_marca(self):
        url = reverse("fitlife_admin:index")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.socio)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertContains(response, "FitLife")
        self.assertContains(response, "admin-fitlife.css")

    def test_admin_es_solo_lectura_y_no_omite_reglas_de_negocio(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("fitlife_admin:fitlife_plan_changelist")).status_code, 200)
        url = reverse("fitlife_admin:fitlife_plan_change", args=[self.plan.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {"nombre": "Alterado"}).status_code, 403)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.nombre, "Mensual")

    def test_listados_y_busquedas_de_todos_los_modelos(self):
        self.client.force_login(self.admin)
        for model in fitlife_admin._registry:
            with self.subTest(model=model.__name__):
                url = reverse(f"fitlife_admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(self.client.get(url, {"q": "1"}).status_code, 200)
