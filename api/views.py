from django.contrib import messages
from django.shortcuts import redirect, render
from rest_framework import viewsets
from .serializer import ProgrammerSerializer
from .models import programmer


def home(request):
	return render(request, 'home.html')


def about(request):
	return render(request, 'about.html')


def services(request):
	return render(request, 'services.html')


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
