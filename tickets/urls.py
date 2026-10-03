"""Rutas REST para cartelera, organización, carros y entradas."""

from rest_framework.routers import DefaultRouter

from .views import CartItemViewSet, EventViewSet, MyTicketViewSet, PurchaseViewSet, SectorViewSet, VenueViewSet

router = DefaultRouter()
router.register('eventos', EventViewSet, basename='event')
router.register('recintos', VenueViewSet, basename='venue')
router.register('sectores', SectorViewSet, basename='sector')
router.register('carro-tickets', CartItemViewSet, basename='cart-ticket')
router.register('compras', PurchaseViewSet, basename='purchase')
router.register('mis-entradas', MyTicketViewSet, basename='my-ticket')

urlpatterns = router.urls