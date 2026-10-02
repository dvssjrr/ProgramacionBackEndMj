from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .models import Cart, CartItem, Event, Order, Sector, Ticket, Venue
from .services import change_order_status, pay_cart


class TicketPurchaseTests(TestCase):
    """Prueba pago, emisión, rechazo por falta de stock y cancelación."""

    def setUp(self):
        user_model = get_user_model()
        self.organizer = user_model.objects.create_user(username='organizer', password='secret')
        self.customer = user_model.objects.create_user(username='customer', password='secret')
        venue = Venue.objects.create(name='Teatro Central', address='Av. Principal 100', capacity=100, organizer=self.organizer)
        event = Event.objects.create(
            name='Noche en Vivo', artist='Banda Ejemplo', starts_at=timezone.now(),
            venue=venue, organizer=self.organizer,
        )
        self.sector = Sector.objects.create(
            event=event, name='Cancha General', price='25000.00', total_tickets=3, available_tickets=3,
        )

    def test_payment_and_cancellation_restore_stock_once(self):
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, sector=self.sector, quantity=2)
        order = pay_cart(self.customer)

        self.sector.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.total, 50000)
        self.assertEqual(self.sector.available_tickets, 1)
        self.assertEqual(Ticket.objects.filter(order_item__order=order).count(), 2)
        cart.refresh_from_db()
        self.assertEqual(cart.status, Cart.Status.ACTIVE)
        self.assertFalse(cart.items.exists())

        change_order_status(order, Order.Status.CANCELLED)
        self.sector.refresh_from_db()
        self.assertEqual(self.sector.available_tickets, 3)
        with self.assertRaises(ValidationError):
            change_order_status(order, Order.Status.CANCELLED)
        self.sector.refresh_from_db()
        self.assertEqual(self.sector.available_tickets, 3)

    def test_insufficient_stock_does_not_create_order_or_change_cart(self):
        cart = Cart.objects.create(user=self.customer)
        self.assertEqual(cart.status, Cart.Status.ACTIVE)
        CartItem.objects.create(cart=cart, sector=self.sector, quantity=4)
        with self.assertRaises(ValidationError):
            pay_cart(self.customer)
        self.sector.refresh_from_db()
        self.assertEqual(self.sector.available_tickets, 3)
        self.assertEqual(Order.objects.count(), 0)
        self.assertTrue(cart.items.exists())


class TicketsAPITests(TestCase):
    """Verifica permisos públicos/protegidos y rol presente en JWT."""

    def setUp(self):
        user_model = get_user_model()
        self.organizer = user_model.objects.create_user(username='organizer', password='secret123')
        self.viewer = user_model.objects.create_user(username='viewer', password='secret123')
        organizer_group, _ = Group.objects.get_or_create(name='Organizador')
        self.organizer.groups.add(organizer_group)
        self.client = APIClient()

    def test_home_page_is_the_ticket_catalog_not_the_academic_crud(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TICKETS')
        self.assertContains(response, 'Iniciar sesión')
        self.assertNotContains(response, 'Crear cuenta de espectador')
        self.assertContains(response, 'Abrir carrito')
        self.assertContains(response, 'Pagar entradas')
        self.assertNotContains(response, 'href="/organizadores/"')
        self.assertNotContains(response, 'Gestión Académica')

    def test_master_and_organizer_roles_are_distinct_from_customer(self):
        user_model = get_user_model()
        master = user_model.objects.create_user(username='damian', password='damian123', is_staff=True, is_superuser=True)
        organizer_group, _ = Group.objects.get_or_create(name='Organizador')
        organizer = user_model.objects.create_user(username='organizador', password='organizador123')
        organizer.groups.add(organizer_group)

        self.assertEqual(master.is_staff, True)
        self.assertEqual(organizer.groups.filter(name='Organizador').exists(), True)
        self.assertEqual(self.viewer.groups.filter(name='Organizador').exists(), False)

    def test_organizer_panel_has_login_and_unknown_admin_route_returns_home(self):
        panel = self.client.get('/organizadores/')

        self.assertEqual(panel.status_code, 200)
        self.assertContains(panel, 'Administra tus eventos')
        self.assertContains(panel, 'organizer-login-form')
        self.assertEqual(self.client.get('/api/eventos/gestion/').status_code, 401)
        self.assertRedirects(self.client.get('/admin/'), '/', fetch_redirect_response=False)

    def test_not_found_page_redirects_to_home(self):
        response = self.client.get('/ruta-inexistente/')

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_catalog_is_public_but_cart_requires_authentication(self):
        self.assertEqual(self.client.get('/api/eventos/').status_code, 200)
        self.assertEqual(self.client.get('/api/carro-tickets/').status_code, 401)

    def test_unpublished_events_are_hidden_from_catalog_but_kept_in_organizer_management(self):
        venue = Venue.objects.create(
            name='Recinto oculto', address='Calle 1', capacity=50, organizer=self.organizer,
        )
        hidden_event = Event.objects.create(
            name='Evento archivado', artist='Artista', starts_at=timezone.now(),
            venue=venue, organizer=self.organizer, is_published=False,
        )
        self.assertNotContains(self.client.get('/api/eventos/'), 'Evento archivado')

        self.client.force_authenticate(self.organizer)
        managed_events = self.client.get('/api/eventos/gestion/')
        self.assertEqual(managed_events.status_code, 200)
        self.assertEqual(managed_events.data[0]['id'], hidden_event.id)

    def test_demo_account_command_activates_accounts_and_sets_login_passwords(self):
        call_command('seed_demo_users')
        user_model = get_user_model()
        for username, password in (
            ('damian', 'damian123'),
            ('organizador', 'organizador123'),
            ('usuario', 'usuario123'),
        ):
            account = user_model.objects.get(username=username)
            self.assertTrue(account.is_active)
            self.assertTrue(account.check_password(password))

    def test_master_can_manage_other_organizers_events_venues_and_sales(self):
        venue = Venue.objects.create(
            name='Recinto de organizador', address='Calle 2', capacity=80, organizer=self.organizer,
        )
        event = Event.objects.create(
            name='Evento de organizador', artist='Artista', starts_at=timezone.now(),
            venue=venue, organizer=self.organizer,
        )
        order = Order.objects.create(user=self.viewer, total='25000.00')
        master = get_user_model().objects.create_superuser(username='master', password='secret123')
        self.client.force_authenticate(master)

        managed_events = self.client.get('/api/eventos/gestion/')
        self.assertEqual([entry['id'] for entry in managed_events.data], [event.id])
        self.assertEqual(self.client.get('/api/recintos/').data[0]['id'], venue.id)
        sales = self.client.get('/api/compras/')
        self.assertEqual([entry['id'] for entry in sales.data], [order.id])
        published = self.client.patch(
            f'/api/eventos/{event.id}/', {'is_published': True}, format='json',
        )
        self.assertEqual(published.status_code, 200)
        self.assertTrue(published.data['is_published'])

    def test_jwt_contains_the_user_role(self):
        response = self.client.post(
            '/api/token/',
            {'username': 'organizer', 'password': 'secret123'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'organizador')
        self.assertEqual(AccessToken(response.data['access'])['role'], 'organizador')
        self.assertEqual(RefreshToken(response.data['refresh'])['role'], 'organizador')
        refresh_response = self.client.post(
            '/api/token/refresh/',
            {'refresh': response.data['refresh']},
            format='json',
        )
        self.assertEqual(refresh_response.status_code, 200)
        self.assertEqual(AccessToken(refresh_response.data['access'])['role'], 'organizador')

    def test_public_registration_creates_only_a_spectator_and_returns_jwts(self):
        response = self.client.post(
            '/api/registro/',
            {
                'username': 'new-spectator',
                'email': 'viewer@example.com',
                'password': 'S3cure-Ticket-Pass-2026!',
                'role': 'organizador',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['role'], 'espectador')
        self.assertEqual(AccessToken(response.data['access'])['role'], 'espectador')
        self.assertEqual(RefreshToken(response.data['refresh'])['role'], 'espectador')
        registered = get_user_model().objects.get(username='new-spectator')
        self.assertFalse(registered.is_staff)
        self.assertTrue(registered.check_password('S3cure-Ticket-Pass-2026!'))

    def test_readding_sector_increases_cart_quantity_without_decreasing_stock(self):
        venue = Venue.objects.create(
            name='Sala Norte', address='Calle 1', capacity=50, organizer=self.organizer,
        )
        event = Event.objects.create(
            name='Concierto', artist='Artista', starts_at=timezone.now(),
            venue=venue, organizer=self.organizer,
        )
        sector = Sector.objects.create(
            event=event, name='General', price='10000.00', total_tickets=5, available_tickets=5,
        )
        self.client.force_authenticate(self.viewer)

        self.client.post('/api/carro-tickets/', {'sector_id': sector.pk, 'quantity': 1}, format='json')
        response = self.client.post(
            '/api/carro-tickets/', {'sector_id': sector.pk, 'quantity': 2}, format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['quantity'], 3)
        update_response = self.client.patch(
            f"/api/carro-tickets/{response.data['id']}/",
            {'quantity': 2},
            format='json',
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data['quantity'], 2)
        sector.refresh_from_db()
        self.assertEqual(sector.available_tickets, 5)

        self.client.logout()
        another_device = APIClient()
        another_device.force_authenticate(self.viewer)
        cart_response = another_device.get('/api/carro-tickets/')
        self.assertEqual(cart_response.status_code, 200)
        self.assertEqual(cart_response.data[0]['quantity'], 2)

    def test_only_organizer_manages_sectors_and_changes_order_state(self):
        venue = Venue.objects.create(
            name='Foro Rojo', address='Calle Sur 25', capacity=60, organizer=self.organizer,
        )
        event = Event.objects.create(
            name='Noche Roja', artist='Artista', starts_at=timezone.now(),
            venue=venue, organizer=self.organizer,
        )
        sector = Sector.objects.create(
            event=event, name='General', price='9000.00', total_tickets=3, available_tickets=3,
        )
        self.client.force_authenticate(self.viewer)
        denied_sector = self.client.post(
            '/api/sectores/',
            {'event': event.pk, 'name': 'VIP', 'price': '18000.00', 'total_tickets': 2},
            format='json',
        )
        self.assertEqual(denied_sector.status_code, 403)

        self.client.post('/api/carro-tickets/', {'sector_id': sector.pk, 'quantity': 1}, format='json')
        order_response = self.client.post('/api/compras/pagar/', format='json')
        self.assertEqual(order_response.status_code, 201)
        order_id = order_response.data['id']
        denied_state = self.client.patch(
            f'/api/compras/{order_id}/estado/', {'status': Order.Status.CANCELLED}, format='json',
        )
        self.assertEqual(denied_state.status_code, 403)

        self.client.force_authenticate(self.organizer)
        created_sector = self.client.post(
            '/api/sectores/',
            {'event': event.pk, 'name': 'VIP', 'price': '18000.00', 'total_tickets': 2},
            format='json',
        )
        self.assertEqual(created_sector.status_code, 201)
        self.assertEqual(created_sector.data['available_tickets'], 2)
        foreign_organizer = get_user_model().objects.create_user(
            username='foreign-organizer', password='secret123',
        )
        foreign_venue = Venue.objects.create(
            name='Recinto Ajeno', address='Calle Norte', capacity=30, organizer=foreign_organizer,
        )
        foreign_event = Event.objects.create(
            name='Evento Ajeno', artist='Otro', starts_at=timezone.now(),
            venue=foreign_venue, organizer=foreign_organizer,
        )
        reassigned_sector = self.client.patch(
            f"/api/sectores/{created_sector.data['id']}/",
            {'event': foreign_event.pk},
            format='json',
        )
        self.assertEqual(reassigned_sector.status_code, 400)
        cancelled = self.client.patch(
            f'/api/compras/{order_id}/estado/', {'status': Order.Status.CANCELLED}, format='json',
        )
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.data['status'], Order.Status.CANCELLED)
        sector.refresh_from_db()
        self.assertEqual(sector.available_tickets, 3)

    def test_organizer_management_endpoint_returns_only_owned_events(self):
        own_venue = Venue.objects.create(
            name='Recinto Propio', address='Calle 1', capacity=20, organizer=self.organizer,
        )
        Event.objects.create(
            name='Evento Propio', artist='Banda', starts_at=timezone.now(),
            venue=own_venue, organizer=self.organizer,
        )
        Event.objects.create(
            name='Evento Ajeno', artist='Otra banda', starts_at=timezone.now(),
            venue=Venue.objects.create(
                name='Recinto Ajeno', address='Calle 2', capacity=20, organizer=self.viewer,
            ),
            organizer=self.viewer,
        )

        self.assertEqual(self.client.get('/api/eventos/gestion/').status_code, 401)
        self.client.force_authenticate(self.organizer)
        response = self.client.get('/api/eventos/gestion/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([event['name'] for event in response.data], ['Evento Propio'])

    def test_organizer_can_create_edit_and_delete_own_event(self):
        own_venue = Venue.objects.create(
            name='Sala CRUD', address='Calle CRUD 1', capacity=100, organizer=self.organizer,
        )
        foreign_organizer = get_user_model().objects.create_user(
            username='foreign-crud-organizer', password='secret123',
        )
        foreign_venue = Venue.objects.create(
            name='Sala Ajena', address='Calle CRUD 2', capacity=100, organizer=foreign_organizer,
        )
        self.client.force_authenticate(self.organizer)
        create_response = self.client.post(
            '/api/eventos/',
            {
                'name': 'Evento CRUD',
                'artist': 'Banda CRUD',
                'starts_at': timezone.now() + timezone.timedelta(days=20),
                'description': 'Evento de prueba',
                'venue': own_venue.pk,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.data['id']

        update_response = self.client.patch(
            f'/api/eventos/{event_id}/', {'name': 'Evento Actualizado'}, format='json',
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data['name'], 'Evento Actualizado')

        foreign_venue_response = self.client.patch(
            f'/api/eventos/{event_id}/', {'venue': foreign_venue.pk}, format='json',
        )
        self.assertEqual(foreign_venue_response.status_code, 400)
        sector = Sector.objects.create(
            event_id=event_id, name='General', price='10000.00', total_tickets=5, available_tickets=5,
        )
        cart = Cart.objects.create(user=self.viewer)
        CartItem.objects.create(cart=cart, sector=sector, quantity=1)
        self.assertEqual(self.client.delete(f'/api/eventos/{event_id}/').status_code, 409)
        cart.items.all().delete()
        self.assertEqual(self.client.delete(f'/api/eventos/{event_id}/').status_code, 204)

    def test_sector_total_edit_preserves_sold_inventory_and_blocks_unsafe_delete(self):
        venue = Venue.objects.create(
            name='Arena Edición', address='Calle Stock', capacity=50, organizer=self.organizer,
        )
        event = Event.objects.create(
            name='Evento Stock', artist='Banda', starts_at=timezone.now(),
            venue=venue, organizer=self.organizer,
        )
        sector = Sector.objects.create(
            event=event, name='General', price='10000.00', total_tickets=10, available_tickets=7,
        )
        self.client.force_authenticate(self.organizer)

        update = self.client.patch(
            f'/api/sectores/{sector.pk}/', {'total_tickets': 15}, format='json',
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.data['available_tickets'], 12)
        rejected = self.client.patch(
            f'/api/sectores/{sector.pk}/', {'total_tickets': 2}, format='json',
        )
        self.assertEqual(rejected.status_code, 400)

        Cart.objects.create(user=self.viewer)
        sector.cart_items.create(cart=self.viewer.ticket_cart, quantity=1)
        deletion = self.client.delete(f'/api/sectores/{sector.pk}/')
        self.assertEqual(deletion.status_code, 409)

    def test_sector_filters_apply_event_and_price_range(self):
        venue = Venue.objects.create(
            name='Teatro Filtro', address='Calle Filtro 1', capacity=100, organizer=self.organizer,
        )
        event = Event.objects.create(
            name='Evento Filtrable', artist='Artista', starts_at=timezone.now(),
            venue=venue, organizer=self.organizer,
        )
        match = Sector.objects.create(
            event=event, name='Platea', price='12000.00', total_tickets=5, available_tickets=5,
        )
        Sector.objects.create(
            event=event, name='VIP', price='30000.00', total_tickets=5, available_tickets=5,
        )

        response = self.client.get(
            f'/api/sectores/?event={event.pk}&min_price=10000&max_price=15000',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [match.pk])

    def test_demo_event_command_is_repeatable_without_resetting_stock(self):
        call_command('seed_demo_events', verbosity=0)
        initial_event_count = Event.objects.count()
        initial_sector_count = Sector.objects.count()
        sector = Sector.objects.order_by('id').first()
        sector.available_tickets -= 1
        sector.save(update_fields=['available_tickets'])

        call_command('seed_demo_events', verbosity=0)

        self.assertEqual(Event.objects.count(), initial_event_count)
        self.assertEqual(Sector.objects.count(), initial_sector_count)
        sector.refresh_from_db()
        self.assertEqual(sector.available_tickets, sector.total_tickets - 1)

    def test_checkout_pays_cart_and_issues_tickets(self):
        venue = Venue.objects.create(
            name='Arena Central', address='Avenida 10', capacity=80, organizer=self.organizer,
        )
        event = Event.objects.create(
            name='Show de prueba', artist='Banda', starts_at=timezone.now(),
            venue=venue, organizer=self.organizer,
        )
        sector = Sector.objects.create(
            event=event, name='Cancha', price='12000.00', total_tickets=4, available_tickets=4,
        )
        self.client.force_authenticate(self.viewer)
        self.client.post('/api/carro-tickets/', {'sector_id': sector.pk, 'quantity': 2}, format='json')

        response = self.client.post('/api/compras/pagar/', format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], Order.Status.PAID)
        self.assertEqual(len(response.data['items'][0]['tickets']), 2)
        sector.refresh_from_db()
        self.assertEqual(sector.available_tickets, 2)