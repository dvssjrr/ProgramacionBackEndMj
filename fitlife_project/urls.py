"""Rutas principales, autenticación, API y administrador de evaluación."""

from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from fitlife.admin import fitlife_admin

handler403 = "fitlife.pages.error_403"
handler404 = "fitlife.pages.error_404"

# El administrador de evaluacion se mantiene separado del panel de FitLife.
urlpatterns = [
    path("evaluacion/", fitlife_admin.urls),
    path("login/", auth_views.LoginView.as_view(template_name="fitlife/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/", include("fitlife.urls")),
    path("", include("fitlife.page_urls")),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico")),
]
