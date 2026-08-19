from django.urls import path

from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('quienes-somos/', views.about, name='about'),
    path('servicios/', views.services, name='services'),
    path('contacto/', views.contact, name='contact'),
    path('usuarios/', views.users, name='users'),
    path('usuarios/nuevo/', views.user_create, name='user_create'),
    path('usuarios/<int:user_id>/editar/', views.user_edit, name='user_edit'),
    path('usuarios/<int:user_id>/borrar/', views.user_delete, name='user_delete'),
]