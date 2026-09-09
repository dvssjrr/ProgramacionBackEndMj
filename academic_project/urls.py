from django.contrib import admin
from django.urls import include, path

# Vista que se muestra cuando una URL no existe.
handler404 = 'academic.views.page_not_found'

urlpatterns = [
    # Panel administrativo de Django.
    path('admin/', admin.site.urls),
    # API REST del sistema académico.
    path('api/', include('academic.urls')),
    # Login opcional para navegar la API DRF.
    path('api-auth/', include('rest_framework.urls')),
    # Interfaz web del sistema académico.
    path('', include('academic.web_urls')),
]
