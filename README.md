# FitLife

Sistema de gestión de gimnasio desarrollado con Django, Django REST Framework
y PostgreSQL. Incluye gestión de socios y membresías, clases y lista de espera,
control de acceso mediante QR, aforo, tienda y pedidos.

## Sitio en AWS EC2

**IP pública:** `54.87.168.154`

**Abrir FitLife:** [https://54.87.168.154/](https://54.87.168.154/)

La instancia debe estar encendida y el laboratorio de AWS Academy activo. Si la
IP pública cambia al detener e iniciar la instancia, consulta la dirección
actual en **AWS Console → EC2 → Instancias**. Usa HTTPS.

## Ejecutar localmente

Requisitos: Python 3.12 o superior y PostgreSQL. Crea la base de datos `fitlife_db`
y el usuario `fitlife_user` en PostgreSQL. Configura su contraseña mediante
`FITLIFE_DB_PASSWORD`; no la guardes en el repositorio.

En Windows PowerShell, desde la raíz del proyecto:

```powershell
py -3.12 -m venv env
.\env\Scripts\python.exe -m pip install -r requirements.txt
$env:FITLIFE_DEBUG = "true"
$env:FITLIFE_DB_PASSWORD = Read-Host "Contraseña de PostgreSQL"
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py createsuperuser
.\env\Scripts\python.exe manage.py runserver
```

Abre `http://127.0.0.1:8000/`. Para probar el proyecto:

```powershell
.\env\Scripts\python.exe manage.py test --settings=fitlife_project.test_settings
```

## Rutas principales

- `/login/` — iniciar sesión.
- `/registro/` — registrar un socio.
- `/panel/` — panel según el rol.
- `/panel/ingreso/` — escáner QR para recepción y administración.
- `/tienda/` — planes y productos.
- `/api/` — API REST.
- `/evaluacion/` — administrador Django de solo lectura para superusuarios.

Roles: `admin`, `staff`, `instructor` y `socio`. Para detalles de base de datos,
demostración, pruebas y despliegue, consulta [FITLIFE.md](./FITLIFE.md).
La evidencia de uso de IA está en [prompts_ia.md](./prompts_ia.md).
