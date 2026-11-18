# Librerías estándar
import csv
import io
from decimal import Decimal, ROUND_HALF_UP

# Importaciones de Django
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import connection, models, transaction
from django.db.models import Sum, F, Value, CharField, Prefetch, Q
from django.db.models.functions import Coalesce, Concat, TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render


from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status, viewsets
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import action, authentication_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission, DjangoModelPermissions, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import filters as drf_filters
from .serializers import GroupSerializer
# Importaciones locales
from .utils import decode_base64_image  # Importamos la función de utilidades
from .filters import SearchNameProy, TbCatalogActivFilter, TbLaborFilterSet, RelClienteHasContactoFilterSet ,RelAsignarFilter
from .authentication import CognitoJWTAuthentication
from django.contrib.auth.models import Group
from .models import (
    TbArea, TbPuesto, TbColaborador, TbCliente, TbProyecto, RelAsignar, 
    TbContacto, TbDireccion, TblIndustria, RelClienteHasContacto, 
    RelCollabHasContacto, TbProveedor, RelProvHasContact, RelTenerProv, 
    TblCategoria, TbCatalogTiempo, TbCatalogActiv, TbLabor, TbModulo,
    TbPrecioPuestoAnual,TbProyectoPuestoAnio,
    TbLineaNegocio,TbLineaServicio,TbListadoServicio

)
from .serializers import (
    UserColaboradorUpsertSerializer,
    TbColaboradorSerializer, TbPuestoSerializer, TbClienteSerializer, 
    TbAreaSerializer,TbAreaConPuestosSerializer, UserSerializer, RelAsignarSerializer, 
    TbContactoSerializer, TbDireccionSerializer, TblIndustriaSerializer, 
    TbProyectoSerializer, RelClienteHasContactoSerializer, 
    RelCollabHasContactoSerializer, RelProvHasContactSerializer, 
    TbProveedorSerializer, RelTenerProvSerializer, TbCatalogActivSerializer, 
    TblCategoriaSerializer, TbCatalogTiempoSerializer ,TbLaborSerializer, TbModuloSerializer, 
    LoginSerializer, RegisterSerializer, LaborResumenMesSerializer, LaborDetalleSerializer,
    LaborDetalleSinAreaSerializer,LaborDetallePorFechaSerializer,
    TbPrecioPuestoAnualSerializer,TbProyectoPuestoAnioSerializer,TbPuestoConTarifasSerializer,
    TbLineaNegocioSerializer,TbLineaServicioSerializer,TbListadoServicioSerializer,
    TbColaboradorUpdateSerializer
)   
from .utils import promover_colaborador 


"""
class RegisterView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            user_serializer = UserSerializer(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_serializer.data
            })
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

"""
class UserProfileCognito(APIView):
    authentication_classes = [CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # Obtener el usuario autenticado
        serializer = UserSerializer(user)  # Serializar los datos del usuario
        return Response(serializer.data)  # Retornar los datos serializados

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/users/               -> lista usuarios con colaborador anidado
    GET /api/users/{id}/          -> detalle de un usuario
    ?search=texto                 -> busca por username, email, nombre
    ?has_colaborador=1            -> solo usuarios con TbColaborador
    """
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def get_queryset(self):
        """
        Devuelve usuarios con colaborador y grupos prefetchados
        para minimizar consultas
        """
        qs = (
            User.objects
            .select_related(
                'colaborador__id_puesto__id_area',
                'colaborador__id_direccion'
            )
            .prefetch_related('groups')
        )
        if self.request.query_params.get('has_colaborador') in ('1', 'true', 'True'):
            qs = qs.filter(colaborador__isnull=False)
        return qs


class IsAdminOrReadOnly(BasePermission):
    """
    Permitir acceso de solo lectura a todos, pero solo permitir acciones de modificación a administradores.
    """

    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user and request.user.is_staff

class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/grupos/         -> Lista todos los grupos (roles)
    GET /api/grupos/{id}/    -> Detalle de un grupo
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]



class UserColaboradorUpsertViewSet(viewsets.ViewSet):
    """
    /api/colaboradores_upsert/
      GET    ?email=...            -> devuelve colaborador (busca por TbColaborador.email o User.email)
      POST                         -> crea nuevo colaborador;
                                      si el email ya existe en TbColaborador o User, devuelve 400 {"error": "el colaborador ya existe"}
      PATCH  /update/?email=...    -> actualiza colaborador existente
    """
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    # -------------------- Helpers --------------------
    def _resolve_for_email(self, email: str):
        """
        Devuelve (user, colab, conflict_ids).
        Busca por coincidencia en TbColaborador.email O user.email (case-insensitive).
        """
        from django.contrib.auth.models import User
        email = (email or "").strip()
        if not email:
            return None, None, None

        qs = (
            TbColaborador.objects
            .filter(Q(email__iexact=email) | Q(user__email__iexact=email))
            .select_related('user', 'id_puesto', 'id_direccion')
        )
        ids = list(qs.values_list('id_colaborador', flat=True).distinct())
        if len(ids) > 1:
            return None, None, ids  # conflicto: múltiples colaboradores con el mismo email

        colab = qs.first()
        user = colab.user if (colab and colab.user_id) else User.objects.filter(email__iexact=email).first()
        return user, colab, None

    def _email_en_uso_por_otro(self, new_email: str, colab_actual_id: int) -> bool:
        if not new_email:
            return False
        return TbColaborador.objects.filter(
            Q(email__iexact=new_email) | Q(user__email__iexact=new_email)
        ).exclude(pk=colab_actual_id).exists()

    # -------------------- GET --------------------
    def list(self, request):
        q_email = request.query_params.get('email')
        user, colab, conflict = self._resolve_for_email(q_email)

        if conflict:
            return Response(
                {"detail": "El email coincide con más de un colaborador.", "colaborador_ids": conflict},
                status=status.HTTP_409_CONFLICT
            )

        if not colab:
            if user:
                return Response(
                    {"detail": "El usuario existe pero no hay TbColaborador para ese email."},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(
                {"detail": "No se encontró TbColaborador para el email proporcionado."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(TbColaboradorSerializer(colab).data, status=status.HTTP_200_OK)

    # -------------------- POST --------------------
    def create(self, request):
        data = request.data.copy()

        # Aceptar 'email' o 'user_email'
        if not data.get('user_email') and data.get('email'):
            data['user_email'] = data['email']

        if 'username' in data and (data['username'] is None or str(data['username']).strip() == ''):
            data.pop('username')

        probe_email = (data.get('user_email') or data.get('email') or '').strip()

        with transaction.atomic():
            if probe_email:
                user, colab, conflict = self._resolve_for_email(probe_email)
                if conflict:
                    return Response(
                        {
                            "detail": "El email coincide con más de un colaborador. Corrige los datos antes de continuar.",
                            "colaborador_ids": conflict
                        },
                        status=status.HTTP_409_CONFLICT
                    )
                if colab or user:
                    # Ya existe un colaborador o un usuario con ese email -> ERROR
                    return Response({"error": "el colaborador ya existe"}, status=status.HTTP_400_BAD_REQUEST)

            # Si no existe: crear normalmente
            ser = UserColaboradorUpsertSerializer(data=data, context={"request": request})
            ser.is_valid(raise_exception=True)
            obj = ser.save()
            return Response(ser.to_representation(obj), status=status.HTTP_201_CREATED)

    # -------------------- PATCH --------------------
    @action(detail=False, methods=['patch'], url_path='update')
    def patch_update(self, request):
        q_email = request.query_params.get('email')
        user, colab, conflict = self._resolve_for_email(q_email)

        if conflict:
            return Response(
                {"detail": "El email coincide con más de un colaborador.", "colaborador_ids": conflict},
                status=status.HTTP_409_CONFLICT
            )

        if not colab:
            if user:
                return Response(
                    {"detail": "El usuario existe pero no tiene TbColaborador vinculado ni se encontró por email."},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(
                {"detail": "No existe TbColaborador para ese email."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.copy()

        with transaction.atomic():
            if colab.user_id:
                new_user_email = data.pop('email', None)
                grupo_ids = data.pop('grupo_ids', None)

                if new_user_email:
                    if self._email_en_uso_por_otro(new_user_email, colab.id_colaborador):
                        return Response(
                            {"email": "Este email ya está en uso por otro colaborador."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    colab.user.email = new_user_email
                    colab.user.save(update_fields=['email'])

                if grupo_ids is not None:
                    try:
                        ids = [int(x) for x in grupo_ids]
                    except Exception:
                        return Response({'grupo_ids': 'Debe ser una lista de IDs válidos.'},
                                        status=status.HTTP_400_BAD_REQUEST)
                    qs = Group.objects.filter(id__in=ids)
                    colab.user.groups.set(qs)
            else:
                new_colab_email = data.get('email')
                data.pop('grupo_ids', None)
                if new_colab_email:
                    if self._email_en_uso_por_otro(new_colab_email, colab.id_colaborador):
                        return Response(
                            {"email": "Este email ya está en uso por otro colaborador."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            ser = TbColaboradorUpdateSerializer(instance=colab, data=data, partial=True, context={"request": request})
            ser.is_valid(raise_exception=True)
            obj = ser.save()
            return Response(TbColaboradorSerializer(obj).data, status=status.HTTP_200_OK)



class PromoverColaboradorAPIView(APIView):
    def post(self, request):
        colaborador_id = request.data.get("id_colaborador")
        username = request.data.get("username")
        password = request.data.get("password")
        grupo_ids = request.data.get("grupo_ids", [])

        if not colaborador_id or not username:
            return Response(
                {"detail": "Se requieren 'id_colaborador' y 'username'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            colaborador = TbColaborador.objects.get(id_colaborador=colaborador_id)
        except TbColaborador.DoesNotExist:
            return Response(
                {"detail": "Colaborador no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            user = promover_colaborador(
                colaborador=colaborador,
                username=username,
                password=password,
                grupo_ids=grupo_ids
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "detail": "Usuario creado y vinculado al colaborador.",
            "user_id": user.id,
            "username": user.username
        }, status=status.HTTP_201_CREATED)
    

class TbAreaViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication,  CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]  # Solo requiere autenticación, no verifica permisos del modelo
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    queryset = TbArea.objects.all()
    serializer_class = TbAreaSerializer

class TbAreaConPuestosViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TbArea.objects.all()
    serializer_class = TbAreaConPuestosSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

class TbPuestoViewSet(viewsets.ModelViewSet):

    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    queryset = TbPuesto.objects.all()
    serializer_class = TbPuestoSerializer




class TbColaboradorViewSet(viewsets.ModelViewSet):
    """
    /api/colaboradores/ CRUD y acciones:
      - GET /api/colaboradores/?has_user=1    lista filtrada
      - GET/POST/PATCH /api/colaboradores/upsert/   upsert unificado por user_id/email
      - POST /api/colaboradores/{id}/baja/    desactiva colaborador
    """
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TbColaboradorSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    queryset = TbColaborador.objects.all()
    filterset_fields = {
        'id_puesto': ['exact'],
        'chr_status': ['exact'],
        'user__id': ['exact'],
    }
    search_fields = [
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'first_name', 'last_name', 'email', 'vc_numEmpleado'
    ]

    def get_queryset(self):
        qs = (
            TbColaborador.objects
            .select_related('user', 'id_puesto__id_area', 'id_direccion')
            .prefetch_related('user__groups')  # requerido para "grupos" sin N+1
        )
        if self.request.query_params.get('has_user') in ('1', 'true', 'True'):
            qs = qs.filter(user__isnull=False)
        return qs


    @action(detail=True, methods=['post'], url_path='baja')
    def dar_de_baja(self, request, pk=None):
        colab = self.get_object()
        colab.chr_status = False
        colab.save(update_fields=['chr_status'])
        return Response({"detail": f"Colaborador {colab.id_colaborador} dado de baja."},
                        status=status.HTTP_200_OK)


class ColaboradorBajaView(APIView):
    """
    POST /api/colaboradores/baja/?id_colaborador=XX
    - Marca al colaborador con chr_status = 0 (False).
    """
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        id_colab = request.query_params.get('id_colaborador')
        if not id_colab:
            return Response(
                {"detail": "Debes enviar ?id_colaborador="},
                status=status.HTTP_400_BAD_REQUEST
            )

        colab = get_object_or_404(TbColaborador, pk=id_colab)
        colab.chr_status = False  # equivalente a 0
        colab.save(update_fields=['chr_status'])

        return Response(
            {
                "detail": f"Colaborador {colab.id_colaborador} dado de baja.",
                "colaborador": TbColaboradorSerializer(colab).data
            },
            status=status.HTTP_200_OK
        )
    
class TblIndustriaViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TblIndustria.objects.all()
    serializer_class = TblIndustriaSerializer
    filter_backends = [DjangoFilterBackend]
              
class TbClienteViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'put', 'delete']
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbCliente.objects.all()
    serializer_class = TbClienteSerializer

    def get_queryset(self):
        queryset = TbCliente.objects.all()

        id_industria = self.request.query_params.get('id_industria')
        if id_industria:
            queryset = queryset.filter(id_industria=id_industria)

        return queryset

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            # Si los datos son una lista, procesarlos como una lista
            serializer = self.get_serializer(data=request.data, many=True)
        else:
            # Si no, procesarlos como un solo objeto
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save()
        
class TbProyectoViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = TbProyecto.objects.all()
    serializer_class = TbProyectoSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'vc_nomProy': ['exact', 'icontains'],
        'proy_cliente__id_cliente__vc_nomb_cliente': ['exact', 'icontains'],
        'proy_cliente__id_cliente__id_industria': ['exact'],
        'id_colab_resp__user__id': ['exact'],
        'bool_isActive': ['exact'],
    }

    def get_serializer_context(self):
        """
        Pasa ?int_anio=YYYY al serializer para construir 'puestos_anio'.
        """
        ctx = super().get_serializer_context()
        ctx['int_anio'] = self.request.query_params.get('int_anio')
        return ctx

    def get_queryset(self):
        """
        Optimiza joins y, si viene ?int_anio=YYYY, hace prefetch de los renglones
        TbProyectoPuestoAnio del año indicado (a través de id_precioPA__int_anio).
        """
        qs = super().get_queryset().select_related(
            'id_colab_resp__user',
            'id_servicio',
            'proy_cliente',
            'proy_cliente__id_cliente',
        )

        anio = self.request.query_params.get('int_anio')
        if anio and str(anio).isdigit():
            qs = qs.prefetch_related(
                Prefetch(
                    'tbproyectopuestoanio_set',
                    queryset=TbProyectoPuestoAnio.objects
                        .filter(id_precioPA__int_anio=int(anio))
                        .select_related('id_precioPA__id_puesto'),
                    to_attr='puestos_prefetch_anio'
                )
            )
        return qs




class RelAsignarViewSet(viewsets.ModelViewSet):
    """
    /api/asignar/ CRUD
      - POST   /api/asignar/                       -> crea UNA asignación (single)
      - POST   /api/asignar/bulk_upsert/           -> crea/actualiza VARIAS asignaciones al MISMO proyecto
      - PATCH  /api/asignar/bulk_patch/            -> bulk PATCH (body: id_proyecto + asignaciones[])
      - PATCH  /api/asignar/bulk_patch/<id>/       -> bulk PATCH (id_proyecto en URL)
      - GET    /api/asignar/resumen_proyecto/?id_proyecto=XX
      - DELETE /api/asignar/clear_proyecto/?id_proyecto=XX
    """
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    queryset = (
        RelAsignar.objects
        .select_related('id_colaborador__user', 'id_colaborador__id_puesto', 'id_proyecto')
    )
    serializer_class = RelAsignarSerializer

    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = RelAsignarFilter
    search_fields = [
        'id_proyecto__vc_nomProy',
        'id_colaborador__user__first_name',
        'id_colaborador__user__last_name',
        'id_colaborador__vc_numEmpleado',
    ]
    ordering_fields = ['id_proyecto', 'id_colaborador', 'dec_dias_plan', 'dec_fact', 'dec_no_fact']
    ordering = ['id_proyecto', 'id_colaborador']

    # ---------- Helpers ----------

    def _is_zero_or_null(self, v):
        """True si v es None o representa 0 (e.g., '0', '0.0', 0)."""
        if v is None:
            return True
        s = str(v).strip().replace(',', '.')
        if s in ('0', '0.0', '0.00', '0.000'):
            return True
        try:
            return float(s) == 0.0
        except Exception:
            return False

    def _bulk_patch_core(self, proy, asignaciones):
        """
        Reglas:
        - Si viene dec_dias_plan en {0, "0", "0.0", null} => DELETE.
        - Si no existe la fila y no es DELETE => CREATE.
        - Si existe y no es DELETE => PATCH parcial de campos presentes (dec_*).
        """
        updated_objs, created_objs = [], []
        deleted_info, skipped, errors = [], [], []
        editable_fields = ('dec_dias_plan', 'dec_fact', 'dec_no_fact')

        with transaction.atomic():
            for idx, row in enumerate(asignaciones):
                col_id = row.get('id_colaborador') or row.get('colaborador_id')
                if not col_id:
                    errors.append({'index': idx, 'detail': 'Falta id_colaborador.'})
                    continue

                # ¿Eliminar?
                delete_flag = ('dec_dias_plan' in row) and self._is_zero_or_null(row.get('dec_dias_plan'))
                if delete_flag:
                    qs = RelAsignar.objects.filter(id_proyecto=proy, id_colaborador_id=col_id)
                    if qs.exists():
                        deleted_count, _ = qs.delete()
                        deleted_info.append({'id_colaborador': col_id, 'count': deleted_count})
                    else:
                        skipped.append({'id_colaborador': col_id, 'reason': 'no_existe_para_borrar'})
                    continue

                # Upsert "parcial": crea si no existe; si existe, solo setea campos presentes
                obj, created = RelAsignar.objects.get_or_create(
                    id_proyecto=proy, id_colaborador_id=col_id
                )

                fields_to_set = {k: row[k] for k in editable_fields if k in row}
                if fields_to_set:
                    for k, v in fields_to_set.items():
                        setattr(obj, k, v)
                    obj.save(update_fields=list(fields_to_set.keys()))

                if created:
                    created_objs.append(obj)
                else:
                    if not fields_to_set:
                        skipped.append({'id_colaborador': col_id, 'reason': 'sin_campos_editables'})
                    else:
                        updated_objs.append(obj)

        return {
            'updated': updated_objs,
            'created': created_objs,
            'deleted': deleted_info,
            'skipped': skipped,
            'errors': errors,
        }

    # ---------- Single create ----------

    def create(self, request, *args, **kwargs):
        """
        Crea UNA asignación. Si envías una lista, rechaza y te pide usar bulk_upsert.
        """
        if isinstance(request.data, list):
            return Response(
                {"detail": ("Para varias asignaciones al MISMO proyecto usa "
                            "POST /api/asignar/bulk_upsert/ con "
                            '{"id_proyecto": <int>, "asignaciones": [{"id_colaborador": <int>, ...}]}')},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # ---------- Bulk upsert (mismo proyecto) ----------

    @action(detail=False, methods=['post'], url_path='bulk_upsert')
    def bulk_upsert(self, request):
        """
        Body (mismo proyecto):
        {
          "id_proyecto": 12,
          "asignaciones": [
            {"id_colaborador": 5, "dec_dias_plan": "10.0", "dec_fact": "8.0", "dec_no_fact": "2.0"},
            {"id_colaborador": 8, "dec_dias_plan": "15.0"}
          ]
        }
        """
        payload = request.data
        if not isinstance(payload, dict) or 'asignaciones' not in payload:
            return Response(
                {'detail': "Body debe ser {'id_proyecto': <int>, 'asignaciones': [...]}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        id_proyecto = payload.get('id_proyecto')
        asignaciones = payload.get('asignaciones', [])
        if not id_proyecto or not isinstance(asignaciones, list):
            return Response(
                {'detail': 'id_proyecto y asignaciones[] son requeridos.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        proy = get_object_or_404(TbProyecto, pk=id_proyecto)
        updated = []
        with transaction.atomic():
            for row in asignaciones:
                col_id = row.get('id_colaborador') or row.get('colaborador_id')
                if not col_id:
                    return Response(
                        {'detail': 'Cada elemento requiere id_colaborador.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                col = get_object_or_404(TbColaborador, pk=col_id)
                obj, _ = RelAsignar.objects.update_or_create(
                    id_colaborador=col, id_proyecto=proy,
                    defaults={
                        'dec_dias_plan': row.get('dec_dias_plan'),
                        'dec_fact': row.get('dec_fact'),
                        'dec_no_fact': row.get('dec_no_fact'),
                    }
                )
                updated.append(obj)
        data = self.get_serializer(updated, many=True).data
        return Response({'count': len(data), 'results': data}, status=status.HTTP_200_OK)

    # ---------- Bulk PATCH (body) ----------

    @action(detail=False, methods=['patch'], url_path='bulk_patch')
    def bulk_patch(self, request):
        """
        PATCH /api/asignar/bulk_patch/
        Body:
        {
          "id_proyecto": 12,
          "asignaciones": [
            {"id_colaborador": 5, "dec_dias_plan": "0"},      // elimina
            {"id_colaborador": 6, "dec_dias_plan": null},     // elimina
            {"id_colaborador": 7, "dec_dias_plan": "10.0"},   // crea/actualiza
            {"id_colaborador": 8, "dec_fact": "6.5"}          // crea/actualiza parcial
          ]
        }
        """
        payload = request.data
        if not isinstance(payload, dict):
            return Response({'detail': 'Body debe ser un objeto JSON.'}, status=status.HTTP_400_BAD_REQUEST)

        id_proyecto = payload.get('id_proyecto')
        asignaciones = payload.get('asignaciones')

        if not id_proyecto or not isinstance(asignaciones, list):
            return Response(
                {'detail': "Se requiere {'id_proyecto': <int>, 'asignaciones': [ ... ]}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        proy = get_object_or_404(TbProyecto, pk=id_proyecto)
        result = self._bulk_patch_core(proy, asignaciones)

        data_updated = self.get_serializer(result['updated'], many=True).data
        data_created = self.get_serializer(result['created'], many=True).data

        return Response({
            'updated_count': len(data_updated),
            'created_count': len(data_created),
            'deleted_count': len(result['deleted']),
            'updated': data_updated,
            'created': data_created,
            'deleted': result['deleted'],
            'skipped': result['skipped'],
            'errors': result['errors']
        }, status=status.HTTP_200_OK)

    # ---------- Bulk PATCH (URL con id_proyecto) ----------

    @action(detail=False, methods=['patch'], url_path=r'bulk_patch/(?P<id_proyecto>\d+)')
    def bulk_patch_by_id(self, request, id_proyecto=None):
        """
        PATCH /api/asignar/bulk_patch/<id_proyecto>/
        Body:
        {
          "asignaciones": [ { "id_colaborador": 5, "dec_dias_plan": "0" }, ... ]
        }
        """
        if not id_proyecto:
            return Response({'detail': 'Falta id_proyecto en la URL.'}, status=status.HTTP_400_BAD_REQUEST)

        asignaciones = request.data.get('asignaciones')
        if not isinstance(asignaciones, list):
            return Response({'detail': 'asignaciones debe ser una lista.'}, status=status.HTTP_400_BAD_REQUEST)

        proy = get_object_or_404(TbProyecto, pk=id_proyecto)
        result = self._bulk_patch_core(proy, asignaciones)

        data_updated = self.get_serializer(result['updated'], many=True).data
        data_created = self.get_serializer(result['created'], many=True).data

        return Response({
            'updated_count': len(data_updated),
            'created_count': len(data_created),
            'deleted_count': len(result['deleted']),
            'updated': data_updated,
            'created': data_created,
            'deleted': result['deleted'],
            'skipped': result['skipped'],
            'errors': result['errors']
        }, status=status.HTTP_200_OK)

    # ---------- Resumen y limpieza ----------

    @action(detail=False, methods=['get'], url_path='resumen_proyecto')
    def resumen_proyecto(self, request):
        """
        GET /api/asignar/resumen_proyecto/?id_proyecto=XX
        Devuelve sumas por colaborador y totales del proyecto.
        """
        id_proyecto = request.query_params.get('id_proyecto')
        if not id_proyecto:
            return Response({'detail': '?id_proyecto= requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        qs = (
            RelAsignar.objects
            .filter(id_proyecto_id=id_proyecto)
            .select_related('id_colaborador__user', 'id_colaborador__id_puesto')
            .values(
                'id_colaborador',
                nombre=Concat(
                    Coalesce(F('id_colaborador__user__first_name'), Value('')),
                    Value(' '),
                    Coalesce(F('id_colaborador__user__last_name'), Value('')),
                    output_field=CharField()
                ),
                puesto=F('id_colaborador__id_puesto__vc_puesto'),
            )
            .annotate(
                dias_plan=Coalesce(Sum('dec_dias_plan'), 0),
                fact=Coalesce(Sum('dec_fact'), 0),
                no_fact=Coalesce(Sum('dec_no_fact'), 0),
            )
            .order_by('nombre')
        )

        totales = RelAsignar.objects.filter(id_proyecto_id=id_proyecto).aggregate(
            total_plan=Coalesce(Sum('dec_dias_plan'), 0),
            total_fact=Coalesce(Sum('dec_fact'), 0),
            total_no_fact=Coalesce(Sum('dec_no_fact'), 0),
        )

        return Response({'resumen': list(qs), 'totales': totales}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='clear_proyecto')
    def clear_proyecto(self, request):
        """
        DELETE /api/asignar/clear_proyecto/?id_proyecto=XX
        Elimina todas las filas de ese proyecto.
        """
        id_proyecto = request.query_params.get('id_proyecto')
        if not id_proyecto:
            return Response({'detail': '?id_proyecto= requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = RelAsignar.objects.filter(id_proyecto_id=id_proyecto).delete()
        return Response({'deleted': deleted}, status=status.HTTP_200_OK)


class TbDireccionViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbDireccion.objects.all()
    serializer_class = TbDireccionSerializer

class TbContactoViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbContacto.objects.all()
    serializer_class = TbContactoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    lookup_field = 'id_contacto'  


class RelClienteHasContactoViewSet(viewsets.ModelViewSet):
    # --- Configuración base del ViewSet ---
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = RelClienteHasContacto.objects.all()
    serializer_class = RelClienteHasContactoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = RelClienteHasContactoFilterSet
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    # ===========================================================
    #  LIST: permite listar como JSON normal o exportar en CSV
    def list(self, request, *args, **kwargs):
        export_csv = request.query_params.get('export_csv')

        # --- Rama para exportar CSV ---
        if export_csv in ['1', 'true', 'True']:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="rel_cliente_contacto.csv"'
            writer = csv.writer(response)

            # Encabezados del CSV
            writer.writerow([
                'ID', 'Cliente', 'Industria', 'Dirección Cliente', 'Contacto',
                'Email Contacto', 'Teléfono Contacto', 'WhatsApp', 'Nacionalidad Contacto',
                'LinkedIn', 'Recurso Responsable (Email)',
                'Año Ingreso', 'Área', 'Nivel de Interlocución', 'Cargo',
                'Teléfono Oficina', 'Seguimiento Cobro', 'Aún Trabajando',
                'Antigüedad en Compañía', 'NPS', 'Competencia Digital'
            ])

            # Recorremos el queryset filtrado
            for rel in self.filter_queryset(self.get_queryset()):
                writer.writerow([
                    # --- Datos de cliente ---
                    rel.id_ClienteHasContacto,
                    rel.id_cliente.vc_nomb_cliente if rel.id_cliente else '',
                    rel.id_cliente.id_industria.vc_nombreInd if rel.id_cliente and rel.id_cliente.id_industria else '',
                    f"{rel.id_cliente.id_direccion.vc_calle}, {rel.id_cliente.id_direccion.vc_localidad}, "
                    f"{rel.id_cliente.id_direccion.vc_estado}, {rel.id_cliente.id_direccion.vc_pais}"
                    if rel.id_cliente and rel.id_cliente.id_direccion else '',

                    # --- Datos de contacto ---
                    rel.id_contacto.vc_contacto_nombre if rel.id_contacto else '',
                    rel.id_contacto.vc_email if rel.id_contacto else '',
                    rel.id_contacto.vc_celular if rel.id_contacto else '',
                    'Sí' if rel.id_contacto and rel.id_contacto.bool_contacto_whatsapp else 'No',
                    rel.id_contacto.vc_nacionalidad_contacto if rel.id_contacto else '',
                    rel.id_contacto.vc_linkedin if rel.id_contacto else '',

                    # --- Responsable (colaborador asociado) ---
                    rel.id_RecursoResp.user.email if rel.id_RecursoResp and rel.id_RecursoResp.user else '',

                    # --- Datos adicionales de la relación ---
                    rel.int_anioIngreso,
                    rel.vc_contArea,
                    rel.vc_contNivInterlocucion,
                    rel.vc_cargo,
                    rel.vc_telOficina,
                    'Sí' if rel.bool_seguimientoCobro else 'No',
                    'Sí' if rel.bool_stillWorking else 'No',
                    rel.vc_antiguedadCompania,
                    rel.vc_NPS,
                    rel.vc_CompDigital
                ])
            return response

        # --- Rama normal (JSON con DRF) ---
        return super().list(request, *args, **kwargs)

    #  IMPORT_CSV: permite cargar datos desde un archivo CSV
    @action(detail=False, methods=['post'], url_path='import_csv')
    @transaction.atomic
    def import_csv(self, request):
        # --- 1. Validación inicial ---
        f = request.FILES.get('file')
        if not f:
            return Response({"detail": "Adjunta un archivo CSV en el campo 'file'."},
                            status=status.HTTP_400_BAD_REQUEST)

        dry_run = str(request.data.get('dry_run', '0')).lower() in ('1', 'true', 'yes')
        try:
            decoded = io.TextIOWrapper(f.file, encoding='utf-8-sig', newline='')
        except AttributeError:
            decoded = io.StringIO(f.read().decode('utf-8-sig'))

        reader = csv.DictReader(decoded, skipinitialspace=True)

        # Columnas obligatorias mínimas
        required = {'id_cliente', 'vc_contacto_nombre', 'vc_email', 'int_anioIngreso'}
        if not required.issubset(set([(c or '').strip() for c in (reader.fieldnames or [])])):
            return Response({
                "detail": "Encabezados mínimos requeridos: id_cliente, vc_contacto_nombre, vc_email, int_anioIngreso",
                "columns_found": reader.fieldnames
            }, status=status.HTTP_400_BAD_REQUEST)

        # Helpers para limpieza de valores
        def none_if_blank(v):
            if v is None: return None
            s = str(v).replace('\u00A0', ' ').strip()
            return None if s == "" else s

        def sstrip(v):
            return (str(v).replace('\u00A0', ' ').strip()) if v is not None else ""

        # --- 2. Proceso de filas ---
        ok, skipped, errors = [], [], []
        seen = set()

        with transaction.atomic():
            sid = transaction.savepoint()
            line_no = 1
            for raw_row in reader:
                line_no += 1
                try:
                    # Limpieza básica de la fila
                    row = {(k or "").strip(): (v if v is None else str(v)) for k, v in (raw_row or {}).items()}
                    if all(sstrip(v) == "" for v in row.values()):
                        continue

                    # --- Validación de campos requeridos ---
                    id_cliente_raw = sstrip(row.get("id_cliente"))
                    try:
                        id_cliente = int(id_cliente_raw) if id_cliente_raw != "" else None
                    except (TypeError, ValueError):
                        id_cliente = None

                    nombre_raw = sstrip(row.get("vc_contacto_nombre"))
                    email_raw = sstrip(row.get("vc_email"))

                    if not id_cliente or nombre_raw == "" or email_raw == "":
                        missing = []
                        if not id_cliente: missing.append("id_cliente")
                        if nombre_raw == "": missing.append("vc_contacto_nombre")
                        if email_raw == "": missing.append("vc_email")
                        raise ValueError(f"Faltan/invalidos: {', '.join(missing)}")

                    # Evita duplicados en el mismo CSV
                    key_csv = (nombre_raw.lower(), email_raw.lower(), id_cliente)
                    if key_csv in seen:
                        skipped.append({"line": line_no, "reason": "duplicado_en_csv", "row": row})
                        continue
                    seen.add(key_csv)

                    # --- Payload para crear o actualizar ---
                    payload = {
                        "id_cliente": id_cliente,
                        "data_contacto": {
                            "vc_contacto_nombre": nombre_raw,
                            "vc_email": email_raw,
                            "vc_genero": none_if_blank(row.get("vc_genero")),
                            "vc_celular": none_if_blank(row.get("vc_celular")),
                            "bool_contacto_whatsapp": sstrip(row.get("bool_contacto_whatsapp")).lower() in ("1","true","sí","si","yes"),
                            "vc_nacionalidad_contacto": none_if_blank(row.get("vc_nacionalidad_contacto")),
                            "fecha_cumpleanos": none_if_blank(row.get("fecha_cumpleanos")),
                            "vc_linkedin": none_if_blank(row.get("vc_linkedin")),
                        },
                        "id_RecursoResp": int(sstrip(row.get("id_RecursoResp"))) if sstrip(row.get("id_RecursoResp")).isdigit() else None,
                        "int_anioIngreso": sstrip(row.get("int_anioIngreso")),
                        "vc_contArea": none_if_blank(row.get("vc_contArea")),
                        "vc_contNivInterlocucion": none_if_blank(row.get("vc_contNivInterlocucion")),
                        "vc_cargo": none_if_blank(row.get("vc_cargo")),
                        "vc_telOficina": none_if_blank(row.get("vc_telOficina")),
                        "bool_seguimientoCobro": sstrip(row.get("bool_seguimientoCobro")).lower() in ("1","true","sí","si","yes"),
                        "bool_stillWorking": sstrip(row.get("bool_stillWorking")).lower() in ("1","true","sí","si","yes"),
                        "vc_antiguedadCompania": none_if_blank(row.get("vc_antiguedadCompania")),
                        "vc_NPS": none_if_blank(row.get("vc_NPS")),
                        "vc_CompDigital": none_if_blank(row.get("vc_CompDigital")),
                    }

                    # --- Deduplicación contra BD ---
                    contacto_exist = TbContacto.objects.filter(
                        vc_contacto_nombre__iexact=nombre_raw,
                        vc_email__iexact=email_raw
                    ).first()

                    if contacto_exist:
                        payload["id_contacto"] = contacto_exist.id_contacto
                        payload.pop("data_contacto", None)
                        if RelClienteHasContacto.objects.filter(
                            id_cliente=id_cliente,
                            id_contacto=contacto_exist.id_contacto
                        ).exists():
                            skipped.append({"line": line_no, "reason": "duplicado_en_bd_relacion", "row": row})
                            continue

                    # --- Validación con serializer ---
                    ser = self.get_serializer(data=payload)
                    ser.is_valid(raise_exception=True)
                    if not dry_run:
                        ser.save()

                    # Registro exitoso
                    ok.append({
                        "line": line_no,
                        "id": ser.data.get("id_ClienteHasContacto"),
                        "contacto_id": payload.get("id_contacto"),
                        "dedupe_contacto": bool(contacto_exist)
                    })

                except Exception as e:
                    msg = getattr(e, "detail", str(e))
                    errors.append({"line": line_no, "error": msg, "row": raw_row})

            # --- Si es dry_run, revertimos ---
            if dry_run:
                transaction.savepoint_rollback(sid)

        # --- Resumen final ---
        code = status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS
        return Response({
            "dry_run": dry_run,
            "inserted": 0 if dry_run else len(ok),
            "validated": len(ok),
            "skipped": len(skipped),
            "skipped_samples": skipped[:20],
            "errors_count": len(errors),
            "errors": errors[:50],
        }, status=code)


class TbLineaNegocioViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbLineaNegocio.objects.all()
    serializer_class = TbLineaNegocioSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['vc_nombre']


class TbLineaServicioViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbLineaServicio.objects.select_related('vc_linea_negocio').all()
    serializer_class = TbLineaServicioSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['vc_linea_negocio']
    search_fields = ['vc_nombre']


class TbListadoServicioViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbListadoServicio.objects.select_related('id_linea_servicio', 'id_linea_servicio__vc_linea_negocio')
    serializer_class = TbListadoServicioSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['id_linea_servicio']
    search_fields = ['vc_nombre']


class RelCollabHasontactoViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = RelCollabHasContacto.objects.all()
    serializer_class = RelCollabHasContactoSerializer

class TbProveedorViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbProveedor.objects.all()
    serializer_class = TbProveedorSerializer

class RelProvHasContactViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = RelProvHasContact.objects.all()
    serializer_class = RelProvHasContactSerializer

class RelTenerProvViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = RelTenerProv.objects.all()
    serializer_class = RelTenerProvSerializer

class TblCategoriaViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TblCategoria.objects.all()
    serializer_class = TblCategoriaSerializer

class TbCatalogTiempoViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbCatalogTiempo.objects.all()
    serializer_class = TbCatalogTiempoSerializer

class TbCatalogActivViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbCatalogActiv.objects.all()
    serializer_class = TbCatalogActivSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TbCatalogActivFilter  # Apuntamos al filtro personalizado
    
class TbLaborViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbLabor.objects.all()
    serializer_class = TbLaborSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TbLaborFilterSet

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset

    def list(self, request, *args, **kwargs):
        # Obtenemos el queryset filtrado
        queryset = self.filter_queryset(self.get_queryset())

        # Calculamos la suma de las horas invertidas
        total_horas_decimal = queryset.aggregate(total_horas=Sum('dec_horasInvertidas'))['total_horas'] or 0

        # Convertimos total_horas_decimal a formato hh:mm
        total_horas = self.convert_decimal_to_hhmm(total_horas_decimal)

        # Serializamos los datos
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            # Si se usa paginación, se incluye la suma en la respuesta paginada
            response = self.get_paginated_response(data)
            response.data['total_horas'] = total_horas
            return response

        serializer = self.get_serializer(queryset, many=True)
        # Añadimos la suma de las horas invertidas a la respuesta
        return Response({
            'results': serializer.data,
            'total_horas': total_horas
        })

    def convert_decimal_to_hhmm(self, decimal_hours):
        """Convierte un valor decimal de horas a formato hh:mm"""
        hours = int(decimal_hours)
        minutes = int((decimal_hours - hours) * 60)
        return f"{hours}:{minutes:02d}"

class TbModuloViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbModulo.objects.all()
    serializer_class = TbModuloSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id_proyecto']

class ResumenLaborMesViewSet(viewsets.ViewSet):
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        anio = request.GET.get('anio')
        mes = request.GET.get('mes')
        colaborador = request.GET.get('colaborador')

        if not anio:
            return Response({
                'error': 'Debe proporcionar el parámetro "anio".'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            anio = int(anio)
        except ValueError:
            return Response({
                'error': 'El formato de "anio" debe ser numérico.'
            }, status=status.HTTP_400_BAD_REQUEST)

        queryset = TbLabor.objects.filter(dt_dia__year=anio)

        if mes:
            meses_validos = {
                'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4,
                'Mayo': 5, 'Junio': 6, 'Julio': 7, 'Agosto': 8,
                'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12
            }
            if mes not in meses_validos:
                return Response({
                    'error': 'Mes inválido. Use nombres como Enero, Febrero, etc.'
                }, status=status.HTTP_400_BAD_REQUEST)
            mes_numero = meses_validos[mes]
            queryset = queryset.filter(dt_dia__month=mes_numero)

        if colaborador:
            queryset = queryset.filter(id_colaborador__user_id=colaborador)

        queryset = queryset.annotate(
            nombre_colaborador=Concat(
                F('id_colaborador__user__first_name'),
                F('id_colaborador__user__last_name'),
                output_field=models.CharField()
            ),
            mes=models.functions.TruncMonth('dt_dia')
        ).values(
            'nombre_colaborador',
            'mes'
        ).annotate(
            total_horas=Sum('dec_horasInvertidas')
        ).order_by('mes', 'nombre_colaborador')

        # Convertir fecha a formato YYYY-MM para el campo mes
        for item in queryset:
            item['mes'] = item['mes'].strftime('%Y-%m')

        serializer = LaborResumenMesSerializer(queryset, many=True)
        return Response(serializer.data)


        
class LaborDetalleSerializerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LaborDetalleSerializer
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        anio = request.GET.get('anio', None)
        vc_tipo = request.GET.get('vc_tipo', None)
        tipo_tiempo = request.GET.get('tipo_tiempo', None)

        if not anio:
            return Response({'error': 'Debe proporcionar el parámetro "anio".'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            anio = int(anio)
        except ValueError:
            return Response({'error': 'El parámetro "anio" debe ser un número válido.'}, status=status.HTTP_400_BAD_REQUEST)

        if tipo_tiempo and tipo_tiempo.upper() not in ['TR', 'NO_TR']:
            return Response({'error': 'El parámetro "tipo_tiempo" solo puede ser "TR" o "NO_TR".'}, status=status.HTTP_400_BAD_REQUEST)

        query = """
            SELECT
                COALESCE(api_tbproyecto.vc_nomProy, 'General') AS proyecto,
                COALESCE(api_tbarea.vc_nomb_area, 'Sin Área') AS area,
                CONCAT(auth_user.first_name, ' ', auth_user.last_name) AS nombre_colaborador,
                DATE_FORMAT(api_tblabor.dt_dia, '%%Y-%%m') AS mes,
                api_tbcatalogactiv.vc_nombre AS nombre_actividad,
                api_tbcatalogactiv.vc_desc AS comentarios,
                api_tbcatalogtiempo.vc_nombre AS tipo_tiempo,
                ROUND(SUM(api_tblabor.dec_horasInvertidas), 2) AS total_horas_decimal
            FROM
                api_tblabor
            LEFT JOIN api_tbproyecto ON api_tblabor.id_proyecto_id = api_tbproyecto.id_proyecto
            LEFT JOIN api_tbcolaborador ON api_tblabor.id_colaborador_id = api_tbcolaborador.id_colaborador
            LEFT JOIN auth_user ON api_tbcolaborador.user_id = auth_user.id
            LEFT JOIN api_tbcatalogactiv ON api_tblabor.id_codigoAct_id = api_tbcatalogactiv.id_codigoAct
            LEFT JOIN api_relactcattiempo ON api_tbcatalogactiv.id_codigoAct = api_relactcattiempo.id_codigoAct_id
            LEFT JOIN api_tbcatalogtiempo ON api_relactcattiempo.id_catalogTiempo_id = api_tbcatalogtiempo.id_catalogTiempo
            LEFT JOIN api_tbpuesto ON api_tbcolaborador.id_puesto_id = api_tbpuesto.id_puesto
            LEFT JOIN api_tbarea ON api_tbpuesto.id_area_id = api_tbarea.id_area
            WHERE
                YEAR(api_tblabor.dt_dia) = %s
        """
        params = [anio]

        if tipo_tiempo:
            if tipo_tiempo.upper() == 'TR':
                query += " AND UPPER(api_tbcatalogtiempo.vc_nombre) = 'TR'"
            elif tipo_tiempo.upper() == 'NO_TR':
                query += """
                    AND api_tbcatalogactiv.id_codigoAct NOT IN (
                        SELECT id_codigoAct_id
                        FROM api_relactcattiempo
                        INNER JOIN api_tbcatalogtiempo ON api_relactcattiempo.id_catalogTiempo_id = api_tbcatalogtiempo.id_catalogTiempo
                        WHERE UPPER(api_tbcatalogtiempo.vc_nombre) = 'TR'
                    )
                """

        if vc_tipo:
            query += " AND LOWER(api_tbproyecto.vc_tipo) = %s"
            params.append(vc_tipo.lower())

        query += """
            GROUP BY
                proyecto,
                area,
                nombre_colaborador,
                mes,
                nombre_actividad,
                comentarios,
                tipo_tiempo
            ORDER BY
                proyecto,
                area,
                nombre_colaborador,
                nombre_actividad;
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0].lower() for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        serializer = LaborDetalleSerializer(results, many=True)
        return Response(serializer.data)

class LaborDetalleSinAreaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LaborDetalleSinAreaSerializer
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        anio = request.GET.get('anio', None)
        vc_tipo = request.GET.get('vc_tipo', None)
        tipo_tiempo = request.GET.get('tipo_tiempo', None)

        if not anio:
            return Response({'error': 'Debe proporcionar el parámetro "anio".'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            anio = int(anio)
        except ValueError:
            return Response({'error': 'El parámetro "anio" debe ser un número válido.'}, status=status.HTTP_400_BAD_REQUEST)

        if tipo_tiempo and tipo_tiempo.upper() not in ['TR', 'NO_TR']:
            return Response({'error': 'El parámetro "tipo_tiempo" solo puede ser "TR" o "NO_TR".'}, status=status.HTTP_400_BAD_REQUEST)

        # Consulta principal de labores, usando categorización de tipo de tiempo según en_tipoLabor
        query = """
            SELECT
                -- labor.id_labor AS id_labor,  -- ID de referencia (comentado para no mostrar)
                COALESCE(proyecto.vc_nomProy, 'General') AS proyecto,
                CONCAT(usuario.first_name, ' ', usuario.last_name) AS nombre_colaborador,
                DATE_FORMAT(labor.dt_dia, '%%Y-%%m') AS mes,
                actividad.vc_nombre AS nombre_actividad,
                labor.vc_desc AS comentarios,
                tipo.vc_nombre AS tipo_tiempo,
                ROUND(SUM(labor.dec_horasInvertidas), 2) AS total_horas_decimal
            FROM api_tblabor labor
            LEFT JOIN api_tbproyecto proyecto ON labor.id_proyecto_id = proyecto.id_proyecto
            LEFT JOIN api_tbcolaborador colaborador ON labor.id_colaborador_id = colaborador.id_colaborador
            LEFT JOIN auth_user usuario ON colaborador.user_id = usuario.id
            LEFT JOIN api_tbcatalogactiv actividad ON labor.id_codigoAct_id = actividad.id_codigoAct
            LEFT JOIN api_relactcattiempo relacion ON relacion.id_codigoAct_id = actividad.id_codigoAct AND (
                ((labor.en_tipoLabor = 'Proyecto Cliente' OR labor.en_tipoLabor = 'Proyecto') AND relacion.id_categoria_id = 1) OR
                (labor.en_tipoLabor = 'General' AND relacion.id_categoria_id = 2) OR
                (labor.en_tipoLabor = 'Proyecto Interno' AND relacion.id_categoria_id = 3)
            )
            LEFT JOIN api_tbcatalogtiempo tipo ON relacion.id_catalogTiempo_id = tipo.id_catalogTiempo
            WHERE YEAR(labor.dt_dia) = %s
        """

        params = [anio]

        # Si se especifica tipo_tiempo, aplicar filtrado adicional
        if tipo_tiempo:
            if tipo_tiempo.upper() == 'TR':
                query += " AND UPPER(tipo.vc_nombre) = 'TR'"
            elif tipo_tiempo.upper() == 'NO_TR':
                query += " AND (tipo.vc_nombre IS NULL OR UPPER(tipo.vc_nombre) <> 'TR')"

        query += """
            GROUP BY labor.id_labor, proyecto, nombre_colaborador, mes, nombre_actividad, comentarios, tipo_tiempo
            ORDER BY proyecto, nombre_colaborador, nombre_actividad;
        """

        # Ejecuta la consulta usando el cursor de bajo nivel
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0].lower() for col in cursor.description]  # convierte a lowercase para consistencia
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Serializa los resultados planos
        serializer = LaborDetalleSinAreaSerializer(results, many=True)
        return Response(serializer.data)
        
#Serializers con filtros 
class LaborDetalleMapaTablaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LaborDetalleSinAreaSerializer
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        anio = request.GET.get('anio')
        tipo_tiempo = request.GET.get('tipo_tiempo')
        vc_tipo = request.GET.get('vc_tipo')
        id_colaborador = request.GET.get('id_colaborador')
        id_proyecto = request.GET.get('id_proyecto')
        id_actividad = request.GET.get('id_actividad')
        id_cliente = request.GET.get('id_cliente')
        mes_inicial = request.GET.get('mes_inicial')
        mes_final = request.GET.get('mes_final')

        if not anio:
            return Response({'error': 'Debe proporcionar el parámetro "anio".'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            anio = int(anio)
        except ValueError:
            return Response({'error': 'El parámetro "anio" debe ser un número válido.'}, status=status.HTTP_400_BAD_REQUEST)

        meses_ordenados = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                           'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        meses_map = {nombre: i+1 for i, nombre in enumerate(meses_ordenados)}

        mes_ini_val = meses_map.get(mes_inicial) if mes_inicial else None
        mes_fin_val = meses_map.get(mes_final) if mes_final else None
        if mes_ini_val and mes_fin_val and mes_ini_val > mes_fin_val:
            mes_ini_val, mes_fin_val = mes_fin_val, mes_ini_val

        query = """
            SELECT
                COALESCE(proyecto.vc_nomProy, 'General') AS proyecto,
                COALESCE(cliente.vc_nomb_cliente, '—') AS cliente, -- 👈 cliente
                CONCAT(usuario.first_name, ' ', usuario.last_name) AS nombre_colaborador,
                DATE_FORMAT(labor.dt_dia, '%%Y-%%m') AS mes,
                actividad.vc_nombre AS nombre_actividad,
                labor.vc_desc AS comentarios,
                tipo.vc_nombre AS tipo_tiempo,
                ROUND(SUM(labor.dec_horasInvertidas), 2) AS total_horas_decimal
            FROM api_tblabor labor
            LEFT JOIN api_tbproyecto proyecto 
                ON labor.id_proyecto_id = proyecto.id_proyecto
            LEFT JOIN api_tbcolaborador colaborador 
                ON labor.id_colaborador_id = colaborador.id_colaborador
            LEFT JOIN auth_user usuario 
                ON colaborador.user_id = usuario.id
            LEFT JOIN api_tbcatalogactiv actividad 
                ON labor.id_codigoAct_id = actividad.id_codigoAct
            LEFT JOIN api_relactcattiempo relacion 
                ON relacion.id_codigoAct_id = actividad.id_codigoAct AND (
                    ((labor.en_tipoLabor = 'Proyecto Cliente' OR labor.en_tipoLabor = 'Proyecto') AND relacion.id_categoria_id = 1) OR
                    (labor.en_tipoLabor = 'General' AND relacion.id_categoria_id = 2) OR
                    (labor.en_tipoLabor = 'Proyecto Interno' AND relacion.id_categoria_id = 3)
                )
            LEFT JOIN api_tbcatalogtiempo tipo 
                ON relacion.id_catalogTiempo_id = tipo.id_catalogTiempo
            LEFT JOIN api_tbproycliente proycli 
                ON proycli.id_proyecto_id = proyecto.id_proyecto
            LEFT JOIN api_tbcliente cliente 
                ON proycli.id_cliente_id = cliente.id_cliente
            WHERE YEAR(labor.dt_dia) = %s
        """
        params = [anio]

        if tipo_tiempo == "TR":
            query += " AND UPPER(tipo.vc_nombre) = 'TR'"
        elif tipo_tiempo == "NO_TR":
            query += " AND (tipo.vc_nombre IS NULL OR UPPER(tipo.vc_nombre) <> 'TR')"

        if vc_tipo:
            query += " AND LOWER(proyecto.vc_tipo) = %s"
            params.append(vc_tipo.lower())

        if id_colaborador:
            query += " AND colaborador.id_colaborador = %s"
            params.append(id_colaborador)

        if id_proyecto:
            query += " AND proyecto.id_proyecto = %s"
            params.append(id_proyecto)

        if id_actividad:
            query += " AND actividad.id_codigoAct = %s"
            params.append(id_actividad)

        if id_cliente:  
            query += " AND cliente.id_cliente = %s"
            params.append(id_cliente)

        if mes_ini_val:
            query += " AND MONTH(labor.dt_dia) >= %s"
            params.append(mes_ini_val)

        if mes_fin_val:
            query += " AND MONTH(labor.dt_dia) <= %s"
            params.append(mes_fin_val)

        query += """
            GROUP BY
                proyecto,
                cliente,
                nombre_colaborador,
                mes,
                nombre_actividad,
                comentarios,
                tipo_tiempo
            ORDER BY
                proyecto,
                nombre_colaborador,
                nombre_actividad;
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0].lower() for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        serializer = LaborDetalleSinAreaSerializer(results, many=True)
        return Response(serializer.data)


#Salida para reporte con días
class LaborDetalleMapaFechasViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LaborDetallePorFechaSerializer
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        anio = request.GET.get('anio')
        tipo_tiempo = request.GET.get('tipo_tiempo')
        vc_tipo = request.GET.get('vc_tipo')
        id_colaborador = request.GET.get('id_colaborador')
        id_proyecto = request.GET.get('id_proyecto')
        id_actividad = request.GET.get('id_actividad')
        fecha_inicial = request.GET.get('fecha_inicial')
        fecha_final = request.GET.get('fecha_final')

        if not anio:
            return Response({'error': 'Debe proporcionar el parámetro "anio".'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            anio = int(anio)
        except ValueError:
            return Response({'error': 'El parámetro "anio" debe ser un número válido.'}, status=status.HTTP_400_BAD_REQUEST)

        query = """
            SELECT
                COALESCE(proyecto.vc_nomProy, 'General') AS proyecto,
                CONCAT(usuario.first_name, ' ', usuario.last_name) AS nombre_colaborador,
                DATE_FORMAT(labor.dt_dia, '%%Y-%%m-%%d') AS fecha,
                actividad.vc_nombre AS nombre_actividad,
                labor.vc_desc AS comentarios,
                tipo.vc_nombre AS tipo_tiempo,
                ROUND(SUM(labor.dec_horasInvertidas), 2) AS total_horas_decimal
            FROM api_tblabor labor
            LEFT JOIN api_tbproyecto proyecto ON labor.id_proyecto_id = proyecto.id_proyecto
            LEFT JOIN api_tbcolaborador colaborador ON labor.id_colaborador_id = colaborador.id_colaborador
            LEFT JOIN auth_user usuario ON colaborador.user_id = usuario.id
            LEFT JOIN api_tbcatalogactiv actividad ON labor.id_codigoAct_id = actividad.id_codigoAct
            LEFT JOIN api_relactcattiempo relacion ON relacion.id_codigoAct_id = actividad.id_codigoAct AND (
                ((labor.en_tipoLabor = 'Proyecto Cliente' OR labor.en_tipoLabor = 'Proyecto') AND relacion.id_categoria_id = 1) OR
                (labor.en_tipoLabor = 'General' AND relacion.id_categoria_id = 2) OR
                (labor.en_tipoLabor = 'Proyecto Interno' AND relacion.id_categoria_id = 3)
            )
            LEFT JOIN api_tbcatalogtiempo tipo ON relacion.id_catalogTiempo_id = tipo.id_catalogTiempo
            WHERE YEAR(labor.dt_dia) = %s
        """
        params = [anio]

        if tipo_tiempo == "TR":
            query += " AND UPPER(tipo.vc_nombre) = 'TR'"
        elif tipo_tiempo == "NO_TR":
            query += " AND (tipo.vc_nombre IS NULL OR UPPER(tipo.vc_nombre) <> 'TR')"

        if vc_tipo:
            query += " AND LOWER(proyecto.vc_tipo) = %s"
            params.append(vc_tipo.lower())

        if id_colaborador:
            query += " AND colaborador.id_colaborador = %s"
            params.append(id_colaborador)

        if id_proyecto:
            query += " AND proyecto.id_proyecto = %s"
            params.append(id_proyecto)

        if id_actividad:
            query += " AND actividad.id_codigoAct = %s"
            params.append(id_actividad)

        if fecha_inicial:
            query += " AND labor.dt_dia >= %s"
            params.append(fecha_inicial)

        if fecha_final:
            query += " AND labor.dt_dia <= %s"
            params.append(fecha_final)

        query += """
            GROUP BY
                proyecto,
                nombre_colaborador,
                fecha,
                nombre_actividad,
                comentarios,
                tipo_tiempo
            ORDER BY
                proyecto,
                nombre_colaborador,
                fecha,
                nombre_actividad;
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0].lower() for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        serializer = LaborDetallePorFechaSerializer(results, many=True)
        return Response(serializer.data)


#--------- TIEMPOS PRecios proyecots
class TbPrecioPuestoAnualViewSet(viewsets.ModelViewSet):
    """
    POST /api/precio_puesto_anual/
    - Acepta:
      A) {"id_puesto": 3, "int_anio": 2025, "dec_precio_unitario": "180.00"}
      B) {"puesto_in": {...}, "int_anio": 2025, "dec_precio_unitario": "180.00"}
         - Si el puesto existe por (vc_puesto + id_area), lo reutiliza.
         - Si ya existe precio (puesto + año), devuelve 400 con mensaje.
    """
    authentication_classes = [BasicAuthentication, CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = TbPrecioPuestoAnual.objects.all()
    serializer_class = TbPrecioPuestoAnualSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id_puesto', 'int_anio']


class TbPuestoConTarifasViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TbPuesto.objects.all().prefetch_related('precios_anuales', 'id_area')
    serializer_class = TbPuestoConTarifasSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'id_area': ['exact'],                             
        'precios_anuales__int_anio': ['exact','gte','lte']  
    }

class TbProyectoPuestoAnioViewSet(viewsets.ModelViewSet):
    authentication_classes = [BasicAuthentication,CognitoJWTAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = (
        TbProyectoPuestoAnio.objects
        .select_related('id_proyecto', 'id_precioPA', 'id_precioPA__id_puesto')
        .all()
    )
    serializer_class = TbProyectoPuestoAnioSerializer
    filter_backends = [DjangoFilterBackend]
    # Ya NO existe int_anio en TbProyectoPuestoAnio; filtramos por el año del tabulador:
    filterset_fields = ['id_proyecto', 'id_precioPA', 'id_precioPA__int_anio']

    def get_serializer_context(self):
        """
        Pasamos ?int_anio=YYYY al serializer para validar coherencia con el tabulador
        y para exponerlo en respuestas (campo 'anio').
        """
        ctx = super().get_serializer_context()
        ctx['int_anio'] = self.request.query_params.get('int_anio')
        return ctx

    @action(detail=False, methods=['post'], url_path='bulk_upsert_calcular')
    def bulk_upsert_calcular(self, request):
        """
        POST /api/proyectoPuestoAnio/bulk_upsert_calcular/

        Body:
        {
          "id_proyecto": 14,
          "int_anio": 2025,
          "puestos": [
            // Opción A: con ID directo
            { "id_precioPA": 7, "horas_estimadas": 10, "int_numPuestos": 2, "dec_tarifa_hora_override": null },

            // Opción B: anidado (crea/actualiza TbPrecioPuestoAnual si hace falta)
            {
              "precio_puesto_data": {
                "id_puesto": 3,                   // o "puesto_in": {...} para crearlo
                "int_anio": 2025,                 // opcional; si no viene, usa el int_anio del body
                "dec_precio_unitario": "180.00"   // opcional; si existe, puede actualizar
              },
              "horas_estimadas": 12.5,
              "int_numPuestos": 3
            }
          ]
        }

        Reglas:
        - Upsert por (id_proyecto, id_precioPA).
        - tarifa_resuelta = override si viene; si no, dec_precio_unitario del tabulador.
        - subtotal de cada renglón = tarifa_resuelta × horas_estimadas × int_numPuestos.
        - total_calculado = sum(subtotal de cada renglón).
        - Validación: el año del tabulador debe coincidir con int_anio del payload.
        """
        id_proyecto = request.data.get('id_proyecto')
        int_anio = request.data.get('int_anio')
        puestos = request.data.get('puestos', [])

        if not id_proyecto or not int_anio or not isinstance(puestos, list):
            return Response(
                {"detail": "Faltan campos requeridos: id_proyecto, int_anio, puestos[]"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            int_anio = int(int_anio)
        except (TypeError, ValueError):
            return Response({"detail": "int_anio debe ser numérico."}, status=status.HTTP_400_BAD_REQUEST)

        objs_actualizados = []
        total_calculado = Decimal('0')

        with transaction.atomic():
            for item in puestos:
                horas = item.get('horas_estimadas')
                override = item.get('dec_tarifa_hora_override', None)
                num_puestos = item.get('int_numPuestos', 1)

                if horas is None:
                    return Response(
                        {"detail": "Cada elemento de 'puestos' requiere horas_estimadas."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # validar num_puestos
                try:
                    num_puestos = int(num_puestos)
                    if num_puestos < 1:
                        return Response({"detail": "int_numPuestos debe ser >= 1."}, status=status.HTTP_400_BAD_REQUEST)
                except (TypeError, ValueError):
                    return Response({"detail": "int_numPuestos debe ser un entero >= 1."}, status=status.HTTP_400_BAD_REQUEST)

                # Resolver precio (A: id_precioPA) o (B: precio_puesto_data)
                precio_row = None
                id_precioPA = item.get('id_precioPA')
                precio_in = item.get('precio_puesto_data')

                if id_precioPA is not None:
                    try:
                        precio_row = TbPrecioPuestoAnual.objects.select_related('id_puesto').get(pk=id_precioPA)
                    except TbPrecioPuestoAnual.DoesNotExist:
                        return Response(
                            {"detail": f"id_precioPA={id_precioPA} no existe."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                elif isinstance(precio_in, dict):
                    # Crear/obtener puesto si viene puesto_in
                    puesto_in = precio_in.get('puesto_in')
                    id_puesto = precio_in.get('id_puesto')
                    if puesto_in:
                        puesto_obj = TbPuesto.objects.create(**puesto_in)
                        id_puesto = puesto_obj.id_puesto
                    if not id_puesto:
                        return Response(
                            {"detail": "precio_puesto_data requiere id_puesto o puesto_in."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    anio_tab = precio_in.get('int_anio', int_anio)
                    try:
                        anio_tab = int(anio_tab)
                    except (TypeError, ValueError):
                        return Response(
                            {"detail": "precio_puesto_data.int_anio debe ser numérico si se envía."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    dec_precio_unitario = precio_in.get('dec_precio_unitario')
                    precio_row, created = TbPrecioPuestoAnual.objects.get_or_create(
                        id_puesto_id=id_puesto,
                        int_anio=anio_tab,
                        defaults={'dec_precio_unitario': dec_precio_unitario} if dec_precio_unitario is not None else {}
                    )
                    # Política: si ya existía y mandan unitario, actualizarlo
                    if not created and dec_precio_unitario is not None:
                        precio_row.dec_precio_unitario = dec_precio_unitario
                        precio_row.save(update_fields=['dec_precio_unitario'])

                else:
                    return Response(
                        {"detail": "Cada elemento en 'puestos' requiere id_precioPA o precio_puesto_data."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Validar año del tabulador vs payload
                if precio_row.int_anio != int_anio:
                    return Response(
                        {"detail": f"El int_anio ({int_anio}) no coincide con TbPrecioPuestoAnual(id={precio_row.id}, anio={precio_row.int_anio})."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Upsert por (proyecto, FK al tabulador)
                obj, _created = TbProyectoPuestoAnio.objects.update_or_create(
                    id_proyecto_id=id_proyecto,
                    id_precioPA_id=precio_row.id,
                    defaults={
                        'dec_horas_estimadas': horas,
                        'dec_tarifa_hora_override': override,
                        'int_numPuestos': num_puestos,
                    }
                )

                # total = tarifa × horas × numPuestos
                tarifa = obj.tarifa_resuelta
                horas_dec = Decimal(str(horas))
                subtotal = (Decimal(str(tarifa)) * horas_dec * Decimal(str(num_puestos))) if tarifa is not None else Decimal('0')
                total_calculado += subtotal
                objs_actualizados.append(obj)

        # Serializar detalles (pasamos el año en context para coherencia)
        detalles = TbProyectoPuestoAnioSerializer(
            objs_actualizados, many=True, context={'int_anio': int_anio}
        ).data

        return Response({
            "id_proyecto": int(id_proyecto),
            "int_anio": int_anio,
            "total_calculado": float(total_calculado),
            "detalles": detalles
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        """
        GET /api/proyectoPuestoAnio/resumen/?id_proyecto=<ID>&int_anio=<ANIO>

        Devuelve todas las filas del proyecto/año + sumatoria:
        {
          "id_proyecto": <ID>,
          "int_anio": <ANIO>,
          "detalles": [ ... ],
          "total_estimado": 12345.67
        }
        """
        id_proyecto = request.query_params.get('id_proyecto')
        int_anio = request.query_params.get('int_anio')

        if not id_proyecto or not int_anio:
            return Response(
                {"detail": "Debe enviar id_proyecto e int_anio como query params."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            int_anio = int(int_anio)
        except (TypeError, ValueError):
            return Response(
                {"detail": "int_anio debe ser numérico."},
                status=status.HTTP_400_BAD_REQUEST
            )

        qs = (
            self.get_queryset()
            .select_related('id_precioPA', 'id_precioPA__id_puesto')
            .filter(id_proyecto_id=id_proyecto, id_precioPA__int_anio=int_anio)  # filtra por año del tabulador
        )

        # Detalles (pasamos el año en context)
        detalles = self.get_serializer(qs, many=True, context={'int_anio': int_anio}).data

        # Total: usa la propiedad subtotal (tarifa × horas × numPuestos)
        total = Decimal('0')
        for obj in qs:
            if obj.subtotal is not None:
                total += obj.subtotal

        return Response({
            "id_proyecto": int(id_proyecto),
            "int_anio": int_anio,
            "detalles": detalles,
            "total_estimado": float(total)
        }, status=status.HTTP_200_OK)