from django.urls import path, include
from rest_framework import routers
from api import views
router = routers.DefaultRouter() # este elemento enrutador permite manejar múltiples rutas.
# esta es la base del conjunto de rutas o la raíz de las rutas
# acá se manejan las rutas o ENDsPOINTS que pueda tener tu API
router.register(r'programmers', views.ProgrammerViewSet)
# la r permite que no se interprete como un salto de línea o como un escape de carácter
# usamos la r para indicar que no tome los caracteres como \n o \t que es un salto de línea o una tabulación, es un formato tipo RAW de python.
# 'programmers' es un ENDPOINT
urlpatterns = [
 path('', include(router.urls))
# la ruta base va a incluir todos los elementos que tenga elrouter que hemos creado en URLS
# esta es la lista de URLS que maneja ROUTER en sus elementos URLS
]
