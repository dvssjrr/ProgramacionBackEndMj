"""Carga eventos demostrativos y stock inicial de forma idempotente."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.models import Event, Sector, Venue


DEMO_EVENTS = [
    {
        'name': 'Noche Carmesí',
        'artist': 'Banda Horizonte',
        'venue': 'Arena Costanera',
        'address': 'Temuco, Chile',
        'capacity': 1800,
        'days_ahead': 45,
        'sectors': [('General', '18000.00', 400), ('VIP', '36000.00', 80)],
    },
    {
        'name': 'Festival del Río',
        'artist': 'Los del Sur',
        'venue': 'Parque de la Araucanía',
        'address': 'Temuco, Chile',
        'capacity': 900,
        'days_ahead': 72,
        'sectors': [('Cancha', '24000.00', 240), ('Preferencial', '42000.00', 60)],
    },
    {
        'name': 'Sesión Roja',
        'artist': 'DJ Aurora',
        'venue': 'Teatro Estación',
        'address': 'Padre Las Casas, Chile',
        'capacity': 1200,
        'days_ahead': 100,
        'sectors': [('Platea', '15000.00', 300), ('Palco', '30000.00', 50)],
    },
]


class Command(BaseCommand):
    help = 'Crea eventos de muestra y stock inicial sin modificar inventario existente.'

    def handle(self, *args, **options):
        user_model = get_user_model()
        organizer, created = user_model.objects.get_or_create(
            username='tickets-demo-organizer',
            defaults={'email': 'organizador@tickets.invalid'},
        )
        if created:
            organizer.set_unusable_password()
            organizer.save(update_fields=['password'])
        organizer_group, _ = Group.objects.get_or_create(name='Organizador')
        organizer.groups.add(organizer_group)

        events_created = 0
        sectors_created = 0
        for sample in DEMO_EVENTS:
            venue, _ = Venue.objects.get_or_create(
                organizer=organizer,
                name=sample['venue'],
                defaults={
                    'address': sample['address'],
                    'capacity': sample['capacity'],
                },
            )
            event, created = Event.objects.get_or_create(
                organizer=organizer,
                name=sample['name'],
                defaults={
                    'artist': sample['artist'],
                    'starts_at': timezone.now() + timedelta(days=sample['days_ahead']),
                    'description': 'Evento de demostración para probar la venta de entradas.',
                    'venue': venue,
                },
            )
            events_created += int(created)
            for sector_name, price, stock in sample['sectors']:
                _, created = Sector.objects.get_or_create(
                    event=event,
                    name=sector_name,
                    defaults={
                        'price': price,
                        'total_tickets': stock,
                        'available_tickets': stock,
                    },
                )
                sectors_created += int(created)

        self.stdout.write(self.style.SUCCESS(
            f'Eventos creados: {events_created}. Localidades con stock creadas: {sectors_created}. '
            'El comando puede repetirse sin restablecer ventas.'
        ))