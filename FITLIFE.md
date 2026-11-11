# FitLife — guía rápida para la exposición

FitLife administra socios, membresías, clases, acceso al gimnasio, aforo y
pedidos. Está desarrollado con Django, Django REST Framework y PostgreSQL.

## Demostración sugerida

1. **Ingresar:** inicia sesión con una cuenta de recepción o administración.
   El socio tiene su propio panel y QR.
2. **Control de acceso:** como socio, muestra el QR. En recepción abre
   **Mi panel → Ingreso al gimnasio** (`/panel/ingreso/`). Una membresía vigente
   permite la entrada; una vencida o congelada la deniega.
3. **Clases:** desde el panel del socio, reserva una clase. Si no quedan cupos,
   se agrega a la lista de espera; una plaza liberada puede asignarse al primero
   que cumpla los requisitos.
4. **Aforo:** recepción consulta personas dentro y porcentaje de ocupación.
   Se actualiza periódicamente; no usa WebSocket ni bloquea entradas al superar
   la capacidad.
5. **Tienda y simulación:** agrega un plan o producto al carrito y crea un
   pedido. En el simulador elige crédito o débito y aprueba o rechaza. Es una
   demostración: no cobra, no pide datos reales de tarjeta y no confirma la
   venta. Recepción debe verificar el pago real antes de confirmar el pedido.

## Acceso y funciones principales

| Función | Dónde demostrarla |
|---|---|
| Inicio de sesión y registro | `/login/` y `/registro/` |
| Panel de socio y QR | `/panel/` |
| Escáner de recepción | `/panel/ingreso/` |
| Gestión de clases | `/panel/clases/` |
| Tienda, carrito y pedidos | `/tienda/`, `/carrito/` |
| API REST | `/api/` |
| Administrador Django de evaluación | `/evaluacion/` — solo superusuarios, solo lectura |

Roles: `admin`, `staff`, `instructor` y `socio`. Los permisos se verifican en
el servidor; los formularios usan sesiones y protección CSRF. Las contraseñas
nuevas exigen 12 caracteres, minúscula, mayúscula, número y símbolo. Con
`FITLIFE_TAB_SESSIONS=true`, **Nueva sesión** permite usar cuentas distintas
en pestañas separadas.

## Base de datos y desarrollo local

La configuración predeterminada apunta a PostgreSQL (`fitlife_db`,
`fitlife_user`, `localhost:5432`). La contraseña y la clave privada se
configuran mediante variables de entorno; no se guardan en el repositorio.
En PowerShell, con PostgreSQL disponible:

```powershell
.\env\Scripts\python.exe -m pip install -r requirements.txt
$env:FITLIFE_DEBUG = "true"
$env:FITLIFE_DB_PASSWORD = Read-Host "Contraseña de PostgreSQL"
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py createsuperuser
.\env\Scripts\python.exe manage.py runserver
```

Para validar el proyecto:

```powershell
.\env\Scripts\python.exe manage.py test --settings=fitlife_project.test_settings
.\env\Scripts\python.exe manage.py check --settings=fitlife_project.test_settings
.\env\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=fitlife_project.test_settings
```

La suite usa SQLite temporal; omite las pruebas que requieren bloqueos
`SELECT FOR UPDATE`. Para validar concurrencia real se necesita ejecutar la
suite contra PostgreSQL con una base de pruebas separada y permiso `CREATEDB`.

## Archivos que conviene explicar

- `fitlife/models.py`: usuarios y entidades relacionales.
- `fitlife/services.py`: reservas, lista de espera y control de acceso.
- `fitlife/shop.py`: carrito, simulación y confirmación transaccional de pedidos.
- `fitlife/views.py`, `fitlife/serializers.py`, `fitlife/urls.py`: API REST.
- `fitlife/pages.py`, `fitlife/shop_views.py`: páginas y formularios.
- `fitlife/admin.py`: administrador de evaluación.
- `fitlife/migrations/`: cambios versionados de la base de datos.

La migración `0006` añade los datos de la simulación. No se aplica a producción
automáticamente: después de desplegar el código, ejecuta `python manage.py
migrate` en el servidor. El despliegue corre con Gunicorn detrás de Nginx y
HTTPS; no expongas PostgreSQL, Gunicorn ni archivos de entorno. Antes de
presentar, confirma que la IP pública asignada abre el sitio y que las cuentas
de prueba funcionan.

## Abrir FitLife 

1. Entra a AWS Academy y abre **Iniciar el Laboratorio de aprendizaje de AWS
   Academy**. Pulsa **Start Lab** y espera a que el indicador quede verde.
2. Abre AWS Console, región **us-east-1 (N. Virginia)**, y entra a
   **EC2 → Instancias**. Busca `fitlife-server`.
3. Si está **Stopped**, selecciónala y pulsa **Instance state → Start
   instance**. No crees otra instancia. Espera a que aparezca **Running** y
   pasen las comprobaciones de estado.
4. Abre `https://54.87.168.154/`. Si la dirección no carga, revisa el campo
   **Public IPv4 address** de la instancia y prueba la dirección actual con
   `https://`; no uses HTTP.
5. Inicia sesión con tu cuenta de presentación y comprueba el panel antes de
   exponer. Si aparece un aviso de certificado o la aplicación no responde,
   no ignores el aviso: usa el enlace HTTPS configurado y solicita ayuda para
   revisar el servidor.
