import django_filters
from django_filters import FilterSet, DateTimeFilter, NumberFilter, CharFilter 
from .models import TbCatalogActiv, TbLabor, RelClienteHasContacto,RelAsignar
from rest_framework.filters import SearchFilter
from django_filters import rest_framework as djf

class TbCatalogActivFilter(django_filters.FilterSet):
    categorias_ids = django_filters.CharFilter(method='filter_by_categorias_ids')

    class Meta:
        model = TbCatalogActiv
        fields = []

    def filter_by_categorias_ids(self, queryset, name, value):
        categorias_ids = value.split(',')
        return queryset.filter(categorias__id_categoria__in=categorias_ids).distinct()


class SearchNameProy(SearchFilter):
    search_param = 'searchNames'  # Cambia el parámetro de búsqueda a 'searchNames'


class TbLaborFilterSet(FilterSet):
    dt_dia_inicio = DateTimeFilter(field_name='dt_dia', lookup_expr='gte')
    dt_dia_final = DateTimeFilter(field_name='dt_dia', lookup_expr='lte')
    id_colaborador = NumberFilter(field_name='id_colaborador')
    id_codigoAct = NumberFilter(field_name='id_codigoAct')
    en_tipoLabor = CharFilter(field_name='en_tipoLabor')
    id_proyecto = NumberFilter(field_name='id_proyecto')

    class Meta:
        model = TbLabor
        fields = ['dt_dia', 'id_colaborador', 'id_codigoAct', 'en_tipoLabor', 'id_proyecto']


class RelClienteHasContactoFilterSet(FilterSet):
    id_cliente = NumberFilter(field_name='id_cliente__id_cliente')
    id_RecursoResp = NumberFilter(field_name='id_RecursoResp__id_colaborador')
    vc_contacto_nombre = CharFilter(field_name='id_contacto__vc_contacto_nombre', lookup_expr='icontains')

    class Meta:
        model = RelClienteHasContacto
        fields = ['id_cliente', 'id_RecursoResp', 'vc_contacto_nombre']


class RelAsignarFilter(djf.FilterSet):
    # Aliases legibles en la URL:
    proyecto    = djf.NumberFilter(field_name='id_proyecto_id')                 
    user_id     = djf.NumberFilter(field_name='id_colaborador__user_id')        
    colaborador = djf.NumberFilter(field_name='id_colaborador_id')             

    class Meta:
        model = RelAsignar
        fields = ['proyecto', 'user_id', 'colaborador']