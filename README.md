# Sistema de Gestión Académica

Evaluacion 1
Backend desarrollado con Django y Django REST Framework.

## Ejecución

El proyecto incluye el entorno virtual `env`. En Windows, ejecútalo desde la
carpeta raíz con:

```powershell
.\env\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver
```

Si PowerShell bloquea la activación, puede ejecutarse directamente sin activar
el entorno:

```powershell
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py runserver
```

La aplicación queda disponible en `http://127.0.0.1:8000/` y la API en
`http://127.0.0.1:8000/api/`.
