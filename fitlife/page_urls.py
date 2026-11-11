"""Rutas de las páginas y acciones HTML de FitLife."""

from django.urls import path
from . import pages, shop_views

# Las paginas visibles y los formularios usan estas rutas con nombres estables.
urlpatterns = [
    path("", pages.inicio, name="home"),
    path("registro/", pages.registro, name="registro"),
    path("panel/", pages.panel, name="panel"),
    path("panel/ingreso/", pages.acceso_gimnasio, name="acceso_gimnasio"),
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
    path("tienda/", shop_views.tienda, name="tienda"),
    path("carrito/", shop_views.carrito, name="carrito"),
    path("carrito/agregar/<str:tipo>/<int:pk>/", shop_views.agregar_articulo, name="agregar_articulo"),
    path("carrito/item/<int:pk>/", shop_views.actualizar_item, name="actualizar_item"),
    path("carrito/solicitar/", shop_views.solicitar, name="solicitar_pedido"),
    path("pedidos/<int:pk>/pago-simulado/", shop_views.pagar_pedido, name="pagar_pedido"),
    path("pedidos/<int:pk>/cancelar/", shop_views.cancelar, name="cancelar_pedido"),
    path("panel/pedidos/", shop_views.pedidos_equipo, name="pedidos_equipo"),
    path("panel/pedidos/<int:pk>/confirmar/", shop_views.confirmar, name="confirmar_pedido"),
]
