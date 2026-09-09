# Sistema de Gestión Académica

Evaluacion 1
Backend desarrollado con Django y Django REST Framework.

## Ejecución

```powershell
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py loaddata fixtures/academic_data.json
.\env\Scripts\python.exe manage.py runserver
```

La interfaz está disponible en `/`, `/teachers/`, `/courses/`, `/students/` y `/enrollments/`.
El panel administrativo de Django está disponible en `/admin/`. Crea un usuario con `createsuperuser` para iniciar sesión.
