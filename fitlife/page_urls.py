from django.urls import path
from . import pages

urlpatterns = [
    path("", pages.inicio, name="home"),
    path("registro/", pages.registro, name="registro"),
    path("panel/", pages.panel, name="panel"),
    path("panel/clases/", pages.gestionar_clases, name="gestionar_clases"),
    path("panel/clases/<int:clase_id>/", pages.gestionar_clases, name="editar_clase"),
    path("panel/clases/<int:clase_id>/eliminar/", pages.eliminar_clase, name="eliminar_clase"),
    path("panel/usuarios/", pages.usuarios, name="usuarios"),
    path("panel/usuarios/<int:usuario_id>/", pages.usuarios, name="editar_usuario"),
    path("panel/usuarios/<int:usuario_id>/clave/", pages.cambiar_clave, name="cambiar_clave"),
    path("panel/configuracion/", pages.configuracion, name="configuracion"),
    path("panel/reportes/", pages.reportes, name="reportes"),
    path("panel/gestion/<str:tipo>/", pages.gestionar, name="gestionar"),
    path("panel/gestion/<str:tipo>/<int:objeto_id>/", pages.gestionar, name="editar_gestion"),
    path("panel/gestion/<str:tipo>/<int:objeto_id>/eliminar/", pages.eliminar, name="eliminar_gestion"),
]
