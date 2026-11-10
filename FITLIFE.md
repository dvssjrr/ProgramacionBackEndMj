# FitLife

Aplicación para membresías, clases, control de acceso y aforo. Usa Django,
DRF, PostgreSQL, sesiones y CSRF.

## Configuración

### Mapa del código

`fitlife/models.py` define las entidades y restricciones de la base de datos.
`forms.py` valida los formularios HTML, `serializers.py` valida la API y
`permissions.py` centraliza los roles. `pages.py` y `page_urls.py` sirven las
páginas propias; `views.py` y `urls.py` exponen la API REST.
`services.py` reúne las reglas de reservas y acceso; `shop.py` implementa
las transacciones de compra y `shop_views.py` sus páginas. `admin.py` configura
el administrador de evaluación de solo lectura. Las plantillas están en
`fitlife_templates/fitlife` y `static/fitlife/js/panel.js` consulta la API.

Las operaciones que cambian reservas, presencia o pedidos usan transacciones
y bloqueos de filas en PostgreSQL. Mantén estas operaciones en los servicios:
modificar directamente las tablas puede saltarse las reglas de negocio.

La conexión predeterminada usa el motor PostgreSQL, base `fitlife_db`, usuario
`fitlife_user`, host `localhost` y puerto `5432`. Define
`FITLIFE_DB_PASSWORD` con la contraseña suministrada para esa base. **No se
guarda la contraseña en el repositorio**. Si ya fue divulgada, cámbiala en
PostgreSQL y actualiza la variable. Se necesita Python 3.12 o superior.

Variables de entorno:

| Variable | Descripción |
|---|---|
| `DJANGO_SETTINGS_MODULE` | Opcional; `manage.py` usa `fitlife_project.settings` por defecto. |
| `FITLIFE_SECRET_KEY` | Clave aleatoria privada, obligatoria salvo con `FITLIFE_DEBUG=true`. |
| `FITLIFE_DB_PASSWORD` | Contraseña de PostgreSQL, obligatoria si el servidor la requiere. |
| `FITLIFE_DB_NAME`, `FITLIFE_DB_USER`, `FITLIFE_DB_HOST`, `FITLIFE_DB_PORT` | Opcionales; predeterminados indicados arriba. |
| `FITLIFE_DEBUG` | `true` solo en desarrollo; por defecto `false`. |
| `FITLIFE_ALLOWED_HOSTS` | Nombres separados por comas; por defecto `localhost,127.0.0.1`. |
| `FITLIFE_HTTPS` | `true` cuando se habilita HTTPS en el proxy. Activa cookies seguras y confianza en el encabezado HTTPS del proxy. |
| `FITLIFE_CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS completos separados por comas, por ejemplo `https://gimnasio.example`. |
| `FITLIFE_TIME_ZONE` | Zona horaria IANA; por defecto `America/Santiago`. |

Ejemplo local en PowerShell, con PostgreSQL ya creado:

```powershell
.\env\Scripts\python.exe -m pip install -r requirements.txt
$env:FITLIFE_DEBUG = "true"
$env:FITLIFE_DB_PASSWORD = Read-Host "Contraseña de PostgreSQL"
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py createsuperuser
.\env\Scripts\python.exe manage.py runserver
```

La clave de desarrollo generada por defecto **no sirve para producción**.
Entra con el superusuario y abre **Mi panel**. Desde **Usuarios** se pueden
crear cuentas y asignar `socio`, `staff`, `instructor` o `admin`; solo los
administradores acceden a esta función y a la configuración. Las cuentas
administradoras no conceden permisos de superusuario. Los administradores y
recepción pueden gestionar planes, membresías, pagos, clases y reportes.
La migración inicial configura una capacidad de 100; ajústala desde
**Configuración** al aforo real. Las clases se gestionan desde
`/panel/clases/` o mediante la API JSON `/api/clases/`, por ejemplo:

```json
{"nombre":"Yoga","descripcion":"Nivel inicial","inicio":"2030-01-01T10:00:00-03:00","cupo_maximo":12,"activa":true}
```

En **Usuarios**, crea una cuenta de socio
separada, luego crea un plan y una membresía vigente para ella. El escáner
requiere el código QR de esa cuenta de socio; el administrador no necesita
una membresía para gestionar el gimnasio. Los superusuarios nuevos reciben el
rol de administrador por defecto.

La página pública está en `/`, el registro en `/registro/`, el acceso en
`/login/` y los paneles en `/panel/`. El registro público crea exclusivamente
una cuenta de socio sin membresía y no verifica correo electrónico; recepción
debe asignarle un plan vigente. El cierre se realiza mediante POST en `/logout/`.
El panel de instructor muestra solo sus clases asignadas de hoy y las reservas
confirmadas; estas no implican asistencia verificada. Las sedes son informativas,
sin ubicaciones ni aforos separados configurados. La interfaz consume la API
usando la cookie de sesión y el token CSRF. Los estilos y la fotografía de
referencia son locales; las fuentes de Google tienen fuentes de respaldo si no hay conexión.
El simulador recibe el texto del QR: no captura imágenes desde
la cámara ni interpreta imágenes; un lector físico tendría que decodificar el
QR y enviar su texto a la API.

La fotografía de portada es referencial y no representa necesariamente una
sede de FitLife; fue proporcionada por el usuario, que indicó tener autorización
para usarla.

### Administrador para evaluación

La ruta `/evaluacion/` ofrece el administrador de Django con identidad FitLife
para inspeccionar todos los modelos del caso. Solo permite entrar a
superusuarios activos. Es de **solo lectura**: crear, editar y eliminar se hace
en las páginas propias o la API, para conservar sus reglas y bloqueos
transaccionales. Las reservas, la lista de espera y los accesos se gestionan
mediante sus operaciones específicas, no editando directamente sus registros.
La ruta no se incluye en la navegación habitual.

## Reglas y API

- Los roles `staff` y `admin` gestionan planes, membresías, pagos y clases;
  los socios solo consultan sus membresías, pagos e inscripciones. Los usuarios
  se administran desde las páginas propias de FitLife. Los instructores tienen un rol distinto
  sin acceso de recepción y ven en su panel solo sus clases asignadas y reservas.
- `/api/planes/`, `/api/membresias/`, `/api/pagos/` y `/api/clases/` ofrecen
  CRUD según los permisos. Las reservas, la lista de espera y los registros de
  acceso se modifican únicamente mediante las operaciones correspondientes.
- `POST /api/clases/{id}/reservar/` confirma una plaza o agrega a espera.
  `POST /api/clases/{id}/cancelar/` cancela y ofrece la plaza al primero de la
  lista con membresía vigente; los candidatos que ya no están habilitados se
  retiran de la cola. Aumentar el cupo también promociona la cola; no se puede
  reducir por debajo de las reservas confirmadas. `/api/reservas/` y
  `/api/esperas/` muestran las inscripciones según el rol. Reservas y cambios de
  cupo bloquean la fila de la clase en PostgreSQL.
- Una membresía permite entrada y reserva solo si está activa y la fecha local
  está dentro de su período, inclusive. Si el socio tiene varias, basta una
  vigente. `estado` es el valor administrado; `estado_efectivo` muestra
  `vencida` automáticamente después de la fecha de término, sin modificar la
  fila. Una membresía congelada nunca habilita el acceso.
- `/api/perfil/` entrega un token firmado; `/api/perfil/qr/` devuelve un PNG.
  Vencen tras 120 segundos; la pantalla los renueva cada minuto. El equipo envía
  `{"token":"...","accion":"entrada"}` o `salida` a
  `/api/accesos/escanear/`. La salida se permite aunque la membresía haya
  vencido. El QR identifica al socio, no sustituye la identificación visual:
  puede compartirse durante su vigencia. Solo se registran intentos cuando el
  token permite identificar un usuario.
- `/api/aforo/` es exclusivo del equipo y calcula personas dentro y porcentaje
  respecto de la capacidad configurada. La interfaz consulta cada 10 segundos:
  no utiliza WebSocket. La capacidad es una métrica y **no bloquea entradas**
  al superarse.
- Los pagos son registros administrativos, no una integración con pasarela.
  No se crean ni renuevan membresías automáticamente al registrar un pago.

## Tienda y carrito

En **Tienda**, los socios pueden añadir productos y un plan al carrito. El
equipo crea productos, define sus precios y su inventario en **Productos**.
No se han creado productos de ejemplo: pueden ser, por ejemplo, botellas,
toallas o accesorios que el gimnasio venda efectivamente.

El socio envía el carrito como un pedido **pendiente de pago**. Los precios,
nombres y duración del plan quedan fijados en el pedido; el stock no se reserva.
El pago y el retiro se realizan en recepción, no por Internet. Una vez recibido
el dinero, recepción confirma el pedido desde **Pedidos**: se valida y descuenta
el stock en una transacción, y se activa el plan desde ese día. Si el socio ya
tiene una membresía activa, futura o congelada, o si falta stock, el pedido
permanece pendiente y no se modifica el inventario ni se activa el plan.
Los pedidos pendientes pueden cancelarse; los confirmados no pueden cancelarse
desde la interfaz y deben tratarse manualmente con administración.
La venta completa queda registrada en el pedido; el registro de pago de
membresía contiene solo el precio del plan, no el importe de los productos.

Para usar dos cuentas al mismo tiempo, abre FitLife en dos navegadores o
perfiles distintos, o usa una ventana normal y otra privada. Las pestañas del
mismo perfil comparten sesión; abrir dos pestañas normales no crea dos cuentas
independientes.

La portada usa la imagen `Chiswick-EG-7_1.webp` suministrada por el usuario,
quien indicó que cuenta con autorización para utilizarla; la imagen se muestra
como referencia y no como fotografía verificada de una sede de FitLife.

## Pruebas

```powershell
.\env\Scripts\python.exe manage.py test fitlife --settings=fitlife_project.test_settings
.\env\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=fitlife_project.test_settings
```

Estas pruebas usan SQLite temporal para funcionalidad; la prueba de concurrencia
se omite allí porque SQLite no implementa `SELECT FOR UPDATE`. Para validar
también el bloqueo real, configura las variables PostgreSQL anteriores y ejecuta:

```powershell
.\env\Scripts\python.exe manage.py test fitlife --settings=fitlife_project.settings
```

Django crea una **base de pruebas separada**; el usuario debe tener permiso
`CREATEDB`. No se deben dirigir pruebas a una base de producción.

## Acceso público HTTPS y mantenimiento

La instancia configurada atiende FitLife en `https://184.198.202.51/`.
El puerto 80 redirige a HTTPS y permite el desafío de renovación del
certificado. La ruta de evaluación es `https://184.198.202.51/evaluacion/`;
requiere una cuenta de superusuario. Gunicorn y PostgreSQL permanecen privados.

El certificado de Let's Encrypt para IP tiene una vida aproximada de seis días;
Certbot dispone de un temporizador de renovación y un hook recarga Nginx.
Consulta su estado en la instancia:

```bash
sudo systemctl list-timers --all | grep certbot
sudo /snap/bin/certbot certificates
sudo /snap/bin/certbot renew --dry-run --run-deploy-hooks
sudo systemctl status fitlife nginx postgresql
```

Si EC2 cambia de IP pública, el certificado anterior no será válido para la
nueva dirección. Será necesario actualizar el certificado, Nginx y las variables
de host y CSRF; una Elastic IP o un dominio estable facilita la operación.
Mantén la instancia encendida para servir la aplicación y renovar el certificado.
No publiques credenciales ni los archivos de configuración privados.

## Acceso privado alternativo mediante SSH

En una instalación configurada **sin** `FITLIFE_HTTPS=true`, se puede mantener
FitLife accesible solo mediante túnel SSH. En la instancia, Gunicorn escucha en
`127.0.0.1:8001`, y Nginx sirve la aplicación y sus archivos estáticos en
`127.0.0.1:8081`. Estos puertos no necesitan abrirse en el grupo de seguridad.
Con `FITLIFE_HTTPS=true`, las cookies son seguras y este túnel HTTP no sirve
para iniciar sesión; usa la dirección pública HTTPS configurada.

En PowerShell, sustituye la ruta, usuario y dirección por los de tu instancia:

```powershell
ssh -i C:\ruta\clave.pem -N -L 127.0.0.1:8081:127.0.0.1:8081 ubuntu@IP_PUBLICA
```

Mantén la terminal abierta y visita `http://127.0.0.1:8081/` en el navegador de
tu máquina. Cerrar la terminal finaliza el túnel. Si el puerto local 8081 ya
está ocupado, cambia el primer `8081` por otro disponible y usa ese puerto
en el navegador.

El servicio se inicia automáticamente. Para revisar su estado y registros:

```bash
sudo systemctl status fitlife
sudo journalctl -u fitlife -n 50 --no-pager
```

La configuración Nginx del túnel debe conservar el host y puerto originales
con `proxy_set_header Host $http_host;`. De lo contrario, Django puede rechazar
los formularios por una discrepancia de origen CSRF. No desactives CSRF para
solucionar este problema.

Las variables sensibles están en `/etc/fitlife.env`, propiedad de root y con
permisos `600`. No compartas ese archivo. Si modificas su contenido, ejecuta
`sudo systemctl restart fitlife` para aplicar los cambios. Para crear más
administradores, ejecuta en la instancia:

```bash
sudo bash -c 'set -a; . /etc/fitlife.env; set +a; cd /srv/fitlife; exec runuser -u fitlife -- .venv/bin/python manage.py createsuperuser'
```

No habilites el acceso público a la aplicación sin HTTPS válido y las variables
de seguridad descritas a continuación.

## Despliegue Ubuntu 24.04, Gunicorn y Nginx

Requiere PostgreSQL y la base y usuario ya creados, DNS apuntando a EC2 y reglas
de seguridad que permitan 80/443. No expongas PostgreSQL ni Gunicorn a Internet.
Usa un certificado TLS válido. Adapta dominio y rutas al servidor.

1. Instala `python3`, `python3-venv`, `nginx`, `certbot` y
   `python3-certbot-nginx`. Copia el código a `/srv/fitlife` con permisos de
   lectura para el usuario del servicio y sin secretos. Crea ese usuario:

   ```bash
   sudo useradd --system --user-group --home /srv/fitlife --shell /usr/sbin/nologin fitlife
   cd /srv/fitlife
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. Crea `/etc/fitlife.env` como root con `chmod 600`. Es un archivo de
   variables `CLAVE=valor`, no lo añadas a Git. Configura como mínimo:

   ```text
   DJANGO_SETTINGS_MODULE=fitlife_project.settings
   FITLIFE_SECRET_KEY=<clave-aleatoria-privada>
   FITLIFE_DB_PASSWORD=<contraseña-de-postgresql>
   FITLIFE_ALLOWED_HOSTS=gimnasio.example
   FITLIFE_HTTPS=true
   FITLIFE_CSRF_TRUSTED_ORIGINS=https://gimnasio.example
   ```

   Genera una clave privada, por ejemplo con `python3 -c 'import secrets;
   print(secrets.token_urlsafe(64))'`, e insértala en el archivo. No compartas
   este archivo ni su contenido. `FITLIFE_HTTPS=true` requiere HTTPS para que
   las sesiones funcionen; termina primero la configuración TLS antes de usar
   la aplicación. Mantén `FITLIFE_DEBUG` desactivado.

3. Ejecuta las migraciones, crea el superusuario y recopila estáticos:

   ```bash
   sudo bash -c 'set -a; . /etc/fitlife.env; set +a; cd /srv/fitlife; exec runuser -u fitlife -- .venv/bin/python manage.py migrate'
   sudo bash -c 'set -a; . /etc/fitlife.env; set +a; cd /srv/fitlife; exec runuser -u fitlife -- .venv/bin/python manage.py createsuperuser'
   sudo bash -c 'set -a; . /etc/fitlife.env; set +a; cd /srv/fitlife; .venv/bin/python manage.py collectstatic --noinput'
   ```

4. Crea `/etc/systemd/system/fitlife.service`:

   ```ini
   [Unit]
   Description=FitLife Gunicorn
   After=network.target postgresql.service

   [Service]
   User=fitlife
   Group=fitlife
   WorkingDirectory=/srv/fitlife
   EnvironmentFile=/etc/fitlife.env
   ExecStart=/srv/fitlife/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8001 fitlife_project.wsgi:application
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```

   Ejecuta `sudo systemctl daemon-reload` y
   `sudo systemctl enable --now fitlife`.

5. Configura un sitio Nginx con el dominio real. Este ejemplo inicial escucha
   HTTP para permitir la emisión del certificado:

   ```nginx
   server {
       listen 80;
       server_name gimnasio.example;
       location /static/ { alias /srv/fitlife/fitlife_static/; }
       location / {
           proxy_set_header Host $http_host;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_pass http://127.0.0.1:8001;
       }
   }
   ```

   Habilita el sitio, comprueba `sudo nginx -t`, recarga Nginx y ejecuta
   `sudo certbot --nginx -d gimnasio.example` para instalar TLS y redirigir
   HTTP. El puerto Gunicorn debe quedar accesible solo localmente para que
   nadie suplante el encabezado HTTPS del proxy. Verifica renovación de
   certificados, respaldos de PostgreSQL, permisos y `systemctl status fitlife`.
   Añade límites de intentos de autenticación y registro en Nginx o una solución
   equivalente antes de exponer el servicio públicamente. En la instalación
   privada por túnel, Nginx limita ambos endpoints a 5 solicitudes por minuto
   con una ráfaga de 5; como el túnel llega desde localhost, todos sus usuarios
   comparten ese límite. La limitación por IP no reemplaza protección adicional
   frente a registros automatizados ni la verificación del correo electrónico.
