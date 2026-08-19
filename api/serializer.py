from rest_framework import serializers
from .models import programmer
class ProgrammerSerializer(serializers.ModelSerializer):
	class Meta:
		model = programmer
		fields = '__all__'
 # con la opción de '__all__' nos traemos todo para ver y tener acceso a todo el registro de cada programador