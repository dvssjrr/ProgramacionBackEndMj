const message = document.getElementById('mensaje');
const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
const csrf = tokenInput ? tokenInput.value : '';
function notify(text, error = false) {
  message.className = `alert ${error ? 'error' : 'success'}`;
  message.textContent = text;
}
async function api(url, options = {}) {
  const response = await fetch(url, {
    credentials: 'same-origin', ...options,
    headers: {'X-CSRFToken': csrf, 'Content-Type': 'application/json', ...(options.headers || {})},
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.motivo || data.detail || data.detalle || JSON.stringify(data));
  return data;
}
async function refreshAforo() {
  const data = await api('/api/aforo/');
  document.getElementById('aforo-dentro').textContent = data.dentro;
  document.getElementById('aforo-detalle').textContent = `${data.porcentaje}% de ${data.capacidad} plazas`;
}
const scanner = document.getElementById('escanear');
if (scanner) {
  scanner.addEventListener('submit', async event => {
    event.preventDefault();
    try {
      await api('/api/accesos/escanear/', {method: 'POST', body: JSON.stringify({
        token: document.getElementById('codigo').value, accion: document.getElementById('accion').value,
      })});
      notify('Acceso registrado correctamente.');
      await refreshAforo();
    } catch (error) { notify(error.message, true); }
  });
  refreshAforo().catch(error => notify(error.message, true));
  setInterval(() => refreshAforo().catch(error => notify(error.message, true)), 10000);
}
async function refreshQR() {
  const perfil = await api('/api/perfil/');
  document.getElementById('token').value = perfil.qr_token;
  document.getElementById('qr').src = `/api/perfil/qr/?t=${Date.now()}`;
}
async function loadClasses() {
  const [classes, reservations, waiting] = await Promise.all([
    api('/api/clases/'), api('/api/reservas/'), api('/api/esperas/'),
  ]);
  const subscribed = new Set([...reservations, ...waiting].map(item => item.clase));
  const container = document.getElementById('clases-lista');
  container.replaceChildren();
  const upcoming = classes.filter(item => item.activa && new Date(item.inicio) > new Date());
  if (!upcoming.length) { container.textContent = 'No hay clases disponibles por ahora.'; return; }
  for (const item of upcoming) {
    const card = document.createElement('article'); card.className = 'quick-card';
    const heading = document.createElement('h3'); heading.textContent = item.nombre;
    const details = document.createElement('p'); details.textContent = `${new Date(item.inicio).toLocaleString()} · ${item.ocupados}/${item.cupo_maximo} cupos · ${item.en_espera} en espera`;
    const button = document.createElement('button'); button.className = 'btn btn-outline light btn-small';
    const enrolled = subscribed.has(item.id);
    button.textContent = enrolled ? 'Cancelar inscripción' : 'Reservar / lista de espera';
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        const result = await api(`/api/clases/${item.id}/${enrolled ? 'cancelar' : 'reservar'}/`, {method: 'POST'});
        notify(result.estado === 'espera' ? 'Te agregamos a la lista de espera.' : result.estado === 'reservada' ? 'Reserva confirmada.' : result.detalle);
        window.location.reload();
      } catch (error) { button.disabled = false; notify(error.message, true); }
    });
    card.append(heading, details, button); container.append(card);
  }
}
if (document.getElementById('qr')) {
  refreshQR().catch(error => notify(error.message, true));
  loadClasses().catch(error => notify(error.message, true));
  setInterval(() => refreshQR().catch(error => notify(error.message, true)), 60000);
}
