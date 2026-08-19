from django.urls import path

from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('quienes-somos/', views.about, name='about'),
    path('servicios/', views.services, name='services'),
    path('contacto/', views.contact, name='contact'),
]