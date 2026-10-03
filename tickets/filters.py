"""Filtros de consulta para eventos, localidades y precios."""

import django_filters

from .models import Event, Sector


class EventFilter(django_filters.FilterSet):
    """Filtra por recinto y fechas límite de inicio del evento."""

    starts_after = django_filters.IsoDateTimeFilter(field_name='starts_at', lookup_expr='gte')
    starts_before = django_filters.IsoDateTimeFilter(field_name='starts_at', lookup_expr='lte')

    class Meta:
        """Define el modelo y el filtro directo disponible para eventos."""

        model = Event
        fields = ['venue']


class SectorFilter(django_filters.FilterSet):
    """Filtra localidades por evento y tramo de precios."""

    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    class Meta:
        """Define el modelo y el filtro directo disponible para localidades."""

        model = Sector
        fields = ['event']