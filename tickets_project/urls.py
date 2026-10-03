"""Rutas de páginas HTML, autenticación y documentación de la API."""

from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from tickets.views import SpectatorRegistrationView

handler404 = 'tickets.views.page_not_found'

urlpatterns = [
    path('organizadores/', TemplateView.as_view(template_name='tickets/organizer.html'), name='organizer-dashboard'),
    # API pública y autenticada de Tickets.
    path('api/', include('tickets.urls')),
    # Emisión y renovación de tokens JWT.
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/registro/', SpectatorRegistrationView.as_view(), name='spectator-registration'),
    # Esquema OpenAPI y documentación interactiva.
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Catálogo inicial para descubrir eventos y localidades.
    path('', TemplateView.as_view(template_name='tickets/home.html'), name='home'),
]
