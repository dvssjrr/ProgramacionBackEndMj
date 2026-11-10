# Evidencia de uso de IA: FitLife

Este registro resume solicitudes reales de esta conversación. Las fechas
anteriores al 10 de noviembre de 2026 no estaban disponibles en el historial
resumido. No se incluyen credenciales ni datos privados.

| Fecha | Herramienta | Solicitud, sin secretos | Resultado y verificación |
|---|---|---|---|
| No registrada | Asistente de IA mediante Copilot SDK | "construyas la solución backend completa e integrada con un frontend responsivo" para FitLife, con Django, DRF, PostgreSQL, acceso QR y reservas. | Se implementaron modelos, API, interfaz y pruebas. El estudiante debe revisar el código y demostrar los flujos. |
| No registrada | Asistente de IA mediante Copilot SDK | "todo lo administrativo tenga una pagina que tenga las opciones administrativa" sin mostrar Django a los usuarios. | Se crearon páginas de gestión propias. La rúbrica posterior requiere además el administrador de Django en una ruta separada. |
| No registrada | Asistente de IA mediante Copilot SDK | "crees un carro para poder comprar en la pagina membresia o lo que se compre en el gym" y permitir dos usuarios a la vez. | Se implementaron carrito y pedidos con confirmación manual. Se verificaron 32 pruebas en PostgreSQL; las sesiones simultáneas requieren perfiles o navegadores distintos. |
| 2026-11-10 | Asistente de IA mediante Copilot SDK | "revises para puntuar 100 en mi rubrica todos estos puntos". | La revisión detectó que el administrador de Django no estaba accesible, faltaba completar este archivo y la IP pública no mostraba FitLife. |
| 2026-11-10 | Asistente de IA mediante Copilot SDK | "realices cambios para cumplir toda la rubrica que generes el codigo y verifiques que todo funcione". | Se habilitó un administrador de evaluación separado y de solo lectura y HTTPS en la IP pública. Pasaron 35 pruebas con PostgreSQL y la simulación de renovación del certificado. El estudiante debe verificar y practicar la defensa. |

## Reflexión y responsabilidad

- La IA ayudó a generar código, revisar reglas, preparar pruebas y despliegue.
- Se detectaron limitaciones: el cobro no es en línea, el escáner es simulado
  y el aforo no bloquea entradas al alcanzar la capacidad.
- Las pruebas automatizadas no sustituyen la comprobación en el navegador ni
  la defensa. Las credenciales divulgadas previamente deben rotarse.
- **Revisión humana pendiente:** el estudiante debe comprobar cada resultado,
  agregar otras herramientas o prompts que haya usado, y describir sus propias
  correcciones y aprendizajes. No se afirma una revisión que aún no ocurrió.
