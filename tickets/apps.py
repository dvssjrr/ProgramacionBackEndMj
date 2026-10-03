from django.apps import AppConfig


class TicketsConfig(AppConfig):
    """Registra Tickets con el label histórico que usan sus migraciones."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tickets'
    label = 'ticketing'
    verbose_name = 'Tickets'