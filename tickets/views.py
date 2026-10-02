"""Endpoints del catálogo público y flujos autenticados de compra."""

from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError as APIValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import EventFilter, SectorFilter
from .models import CartItem, Event, Order, Sector, Ticket, Venue
from .permissions import IsOrganizer, PublicReadOrganizerWrite, is_master, is_organizer
from .serializers import (
    CartItemSerializer, EventSerializer, OrderSerializer, OrderStatusSerializer,
    RoleTokenObtainPairSerializer, SectorSerializer, SpectatorRegistrationSerializer,
    TicketSerializer, TokenPairResponseSerializer, VenueSerializer,
)
from .services import change_order_status, pay_cart


def page_not_found(request, exception=None):
    """Devuelve a la portada cualquier dirección que no exista."""
    return redirect('home')


class SpectatorRegistrationView(APIView):
    """Registra espectadores y devuelve sus JWT sin permitir autoasignar roles."""

    permission_classes = [AllowAny]
    serializer_class = SpectatorRegistrationSerializer

    @extend_schema(request=SpectatorRegistrationSerializer, responses={201: TokenPairResponseSerializer})
    def post(self, request):
        serializer = SpectatorRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = RoleTokenObtainPairSerializer.get_token(user)
        return Response({
            'refresh': str(token),
            'access': str(token.access_token),
            'role': 'espectador',
            'username': user.username,
        }, status=status.HTTP_201_CREATED)


class EventViewSet(viewsets.ModelViewSet):
    """Catálogo público y mantenimiento de eventos del organizador."""

    serializer_class = EventSerializer
    permission_classes = [PublicReadOrganizerWrite]
    filterset_class = EventFilter
    search_fields = ['name', 'artist', 'venue__name']
    ordering_fields = ['starts_at', 'name']
    queryset = Event.objects.select_related('venue', 'organizer').prefetch_related('sectors')

    def get_queryset(self):
        """Deja la lectura pública y limita las escrituras a eventos propios."""
        queryset = super().get_queryset()
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return queryset.filter(is_published=True)
        if is_master(self.request.user):
            return queryset
        if is_organizer(self.request.user):
            return queryset.filter(organizer=self.request.user)
        return queryset

    def perform_create(self, serializer):
        """Asigna el organizador desde el token, nunca desde el payload."""
        serializer.save(organizer=self.request.user)

    @action(detail=False, methods=['get'], url_path='gestion', permission_classes=[IsOrganizer])
    def management(self, request):
        """Lista solo los eventos administrables por el organizador autenticado."""
        events = Event.objects.all() if is_master(request.user) else Event.objects.filter(organizer=request.user)
        events = events.select_related('venue', 'organizer').prefetch_related('sectors')
        return Response(self.get_serializer(events, many=True).data)

    def destroy(self, request, *args, **kwargs):
        """Protege órdenes históricas y carros persistentes ante borrados."""
        event = self.get_object()
        if any(sector.cart_items.exists() or sector.order_items.exists() for sector in event.sectors.all()):
            return Response(
                {'detail': 'No se puede eliminar: el evento tiene entradas en carros u órdenes.'},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='sectores')
    def sectors(self, request, pk=None):
        """Lista las localidades del evento seleccionado."""
        event = self.get_object()
        sectors = event.sectors.all()
        page = self.paginate_queryset(sectors)
        data = SectorSerializer(page if page is not None else sectors, many=True).data
        return self.get_paginated_response(data) if page is not None else Response(data)


class VenueViewSet(viewsets.ModelViewSet):
    """Administración de recintos del organizador autenticado."""

    serializer_class = VenueSerializer
    permission_classes = [IsOrganizer]
    queryset = Venue.objects.all()

    def get_queryset(self):
        """Limita la administración a recintos del usuario autenticado."""
        if is_master(self.request.user):
            return Venue.objects.order_by('name')
        return Venue.objects.filter(organizer=self.request.user).order_by('name')

    def perform_create(self, serializer):
        """Asigna al usuario actual como propietario del recinto."""
        serializer.save(organizer=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Evita borrar recintos que aún contienen eventos."""
        venue = self.get_object()
        if venue.events.exists():
            return Response(
                {'detail': 'No se puede eliminar: el recinto todavía tiene eventos.'},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)


class SectorViewSet(viewsets.ModelViewSet):
    """Catálogo público y gestión de localidades por su organizador."""

    serializer_class = SectorSerializer
    permission_classes = [PublicReadOrganizerWrite]
    filterset_class = SectorFilter
    ordering_fields = ['price', 'available_tickets']

    def get_queryset(self):
        """Filtra las escrituras por propietario y deja el catálogo legible."""
        queryset = Sector.objects.select_related('event').all()
        if is_master(self.request.user):
            return queryset
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS') and is_organizer(self.request.user):
            return queryset.filter(event__organizer=self.request.user)
        return queryset

    def perform_create(self, serializer):
        """Valida propiedad y sincroniza el stock inicial con el total."""
        event = serializer.validated_data['event']
        if event.organizer_id != self.request.user.id and not is_master(self.request.user):
            raise PermissionDenied('El evento debe pertenecer al organizador.')
        serializer.save(available_tickets=serializer.validated_data['total_tickets'])

    def destroy(self, request, *args, **kwargs):
        """Protege las localidades asociadas a carros u órdenes."""
        sector = self.get_object()
        if sector.cart_items.exists() or sector.order_items.exists():
            return Response(
                {'detail': 'No se puede eliminar: la localidad tiene entradas en carros u órdenes.'},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)


class CartItemViewSet(viewsets.ModelViewSet):
    """CRUD de ítems limitado al carro persistente del usuario."""

    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]
    queryset = CartItem.objects.all()
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        """Devuelve únicamente los ítems del carro del usuario actual."""
        return CartItem.objects.filter(cart__user=self.request.user).select_related('sector', 'sector__event')


class PurchaseViewSet(viewsets.ReadOnlyModelViewSet):
    """Pago del carro y consulta de compras propias o de eventos organizados."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.all()

    def get_queryset(self):
        """Muestra compras propias a espectadores y ventas propias a organizadores."""
        queryset = Order.objects.prefetch_related('items__tickets', 'items__sector__event')
        if is_master(self.request.user):
            return queryset
        if is_organizer(self.request.user):
            return queryset.annotate(
                organizer_count=Count('items__sector__event__organizer', distinct=True),
            ).filter(
                organizer_count=1,
                items__sector__event__organizer=self.request.user,
            ).distinct()
        return queryset.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='pagar')
    def pay(self, request):
        """Liquida el carro; el servicio valida stock y emite los UUID."""
        try:
            order = pay_cart(request.user)
        except ValidationError as error:
            raise APIValidationError(error.messages) from error
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='estado', permission_classes=[IsOrganizer])
    def change_status(self, request, pk=None):
        """Autoriza cambios finales y repone inventario al cancelar."""
        order = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = change_order_status(order, serializer.validated_data['status'])
        except ValidationError as error:
            raise APIValidationError(error.messages) from error
        return Response(self.get_serializer(order).data)


class MyTicketViewSet(viewsets.ReadOnlyModelViewSet):
    """Entradas del espectador autenticado."""

    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    queryset = Ticket.objects.all()

    def get_queryset(self):
        """Restringe la lista de entradas al comprador autenticado."""
        return Ticket.objects.filter(order_item__order__user=self.request.user).select_related(
            'order_item__sector__event'
        ).order_by('-issued_at')