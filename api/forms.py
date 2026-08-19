from django import forms

from .models import programmer


class ProgrammerForm(forms.ModelForm):
    class Meta:
        model = programmer
        fields = ('fullname', 'nickname', 'language', 'age', 'is_active')
        labels = {
            'fullname': 'Nombre completo',
            'nickname': 'Usuario o alias',
            'language': 'Especialidad',
            'age': 'Edad',
            'is_active': 'Usuario activo',
        }
        widgets = {
            'fullname': forms.TextInput(attrs={'placeholder': 'Ej. Ana García'}),
            'nickname': forms.TextInput(attrs={'placeholder': 'Ej. ana_garcia'}),
            'language': forms.TextInput(attrs={'placeholder': 'Ej. Python'}),
            'age': forms.NumberInput(attrs={'min': 1, 'max': 120}),
        }
