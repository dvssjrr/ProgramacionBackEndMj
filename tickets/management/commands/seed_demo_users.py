from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crea o actualiza usuarios demo para maestro, organizador y cliente.'

    def handle(self, *args, **options):
        user_model = get_user_model()

        master, master_created = user_model.objects.get_or_create(
            username='damian',
            defaults={'is_staff': True, 'is_superuser': True},
        )
        master.set_password('damian123')
        master.is_staff = True
        master.is_superuser = True
        master.is_active = True
        master.save()

        organizer_group, _ = Group.objects.get_or_create(name='Organizador')
        organizer, organizer_created = user_model.objects.get_or_create(username='organizador')
        organizer.set_password('organizador123')
        organizer.is_staff = False
        organizer.is_superuser = False
        organizer.is_active = True
        organizer.save()
        organizer.groups.add(organizer_group)

        customer, customer_created = user_model.objects.get_or_create(username='usuario')
        customer.set_password('usuario123')
        customer.is_staff = False
        customer.is_superuser = False
        customer.is_active = True
        customer.save()

        self.stdout.write(self.style.SUCCESS(
            'Usuarios demo listos: damian / damian123, organizador / organizador123, usuario / usuario123'
        ))
