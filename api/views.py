from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets
from .forms import ProgrammerForm
from .serializer import ProgrammerSerializer
from .models import programmer


def home(request):
	return render(request, 'home.html')


def about(request):
	return render(request, 'about.html')


def services(request):
	return render(request, 'services.html')


def users(request):
	user_list = programmer.objects.order_by('fullname')
	return render(request, 'users/list.html', {'users': user_list})


def user_create(request):
	form = ProgrammerForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Usuario creado correctamente.')
		return redirect('users')
	return render(request, 'users/form.html', {'form': form, 'page_title': 'Nuevo usuario'})


def user_edit(request, user_id):
	user = get_object_or_404(programmer, pk=user_id)
	form = ProgrammerForm(request.POST or None, instance=user)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Usuario actualizado correctamente.')
		return redirect('users')
	return render(request, 'users/form.html', {'form': form, 'page_title': 'Editar usuario', 'user': user})


def user_delete(request, user_id):
	user = get_object_or_404(programmer, pk=user_id)
	if request.method == 'POST':
		user.delete()
		messages.success(request, 'Usuario eliminado correctamente.')
	return redirect('users')


def contact(request):
	if request.method == 'POST':
		messages.success(request, 'Gracias por contactarnos. Revisaremos tu mensaje pronto.')
		return redirect('contact')
	return render(request, 'contact.html')


# Create your views here.
class ProgrammerViewSet(viewsets.ModelViewSet):
 # acá creamos una consulta o QUERY a nuestra tabla, trayendo todos los campos como un objeto.
 queryset = programmer.objects.all()
 # Agregamos la clase ProgrammerSerializer que ya tiene el modelo serializado para mostrar
 serializer_class = ProgrammerSerializer
