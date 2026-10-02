# Tickets

Backend de venta de entradas para eventos, construido con Django REST Framework
y PostgreSQL. La aplicación incluye catálogo público, gestión de organizadores,
carro persistente, compras atómicas, inventario y emisión de entradas UUID.

## Iniciar

Usa PostgreSQL local y configura `.env` a partir de `.env.example`. Completa
`POSTGRES_PASSWORD` con la contraseña local del usuario de base de datos. El
archivo `.env` no se sube al repositorio.

```powershell
.\env\Scripts\python.exe -m pip install -r requirements.txt
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py createsuperuser
.\env\Scripts\python.exe manage.py seed_demo_events
.\env\Scripts\python.exe manage.py runserver
```

`seed_demo_events` crea una cartelera ficticia con stock inicial; puede
ejecutarse de nuevo sin duplicar eventos ni restablecer entradas vendidas.

La página de eventos está en `http://127.0.0.1:8000/`, el panel organizador en
`http://127.0.0.1:8000/organizadores/` y Swagger en `http://127.0.0.1:8000/api/docs/`.
Configura `STUDENT_FULL_NAME`, `STUDENT_SECTION` y `STUDENT_YEAR` en `.env`
para mostrar los datos reales del alumno en el pie de página.
En la portada se puede registrar un espectador, iniciar/cerrar sesión, agregar
o cambiar cantidades del carrito persistente, pagar y revisar las entradas UUID.

## API
- `GET /api/eventos/gestion/`: lista los eventos del organizador autenticado.

- `GET /api/eventos/` y `GET /api/eventos/{id}/sectores/`: catálogo público.
- `GET /api/sectores/?event={id}&min_price={monto}&max_price={monto}`: filtros.
- `/api/recintos/`, `/api/eventos/` y `/api/sectores/`: gestión de organizador.
- `/api/carro-tickets/`: carro persistente del usuario autenticado.
- `POST /api/compras/pagar/`: valida y descuenta stock dentro de una transacción.
- `PATCH /api/compras/{id}/estado/`: cancelar o marcar como entregada.
- `GET /api/mis-entradas/`: entradas del espectador.
- `POST /api/token/` y `/api/token/refresh/`: JWT con claim `role`.
- `POST /api/registro/`: crea una cuenta de espectador y entrega access/refresh.
- `/api/schema/`: esquema OpenAPI.

La cuenta creada con `createsuperuser` puede ingresar al panel organizador.
Los usuarios normales reciben el rol `espectador`. El stock no se reserva al agregar
al carro: solo se descuenta al pagar y se repone al cancelar una compra pagada.

## Pruebas

```powershell
.\env\Scripts\python.exe manage.py test tickets
```

Django crea una base PostgreSQL temporal para las pruebas.
