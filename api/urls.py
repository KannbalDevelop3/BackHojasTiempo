# hojas_tiempo/urls.py
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf.urls.static import static

# Importa las vistas de Simple JWT
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from .views import TbAreaViewSet,TbAreaConPuestosViewSet, TbPuestoViewSet, TbPuestoConTarifasViewSet, TbColaboradorViewSet, TblIndustriaViewSet, \
    TbClienteViewSet, TbProyectoViewSet, RelAsignarViewSet , TbDireccionViewSet, TbContactoViewSet, \
    RelClienteHasContactoViewSet, RelCollabHasontactoViewSet, TbProveedorViewSet, RelProvHasContactViewSet, RelTenerProvViewSet,  \
    TblCategoriaViewSet, TbCatalogTiempoViewSet , TbCatalogActivViewSet, TbLaborViewSet, TbModuloViewSet,\
    UserProfileCognito,ResumenLaborMesViewSet,\
    LaborDetalleSerializerViewSet,LaborDetalleSinAreaViewSet,LaborDetalleMapaTablaViewSet,LaborDetalleMapaFechasViewSet,PromoverColaboradorAPIView, \
    TbPrecioPuestoAnualViewSet, TbProyectoPuestoAnioViewSet, UserViewSet,TbLineaNegocioViewSet,TbLineaServicioViewSet, \
    UserColaboradorUpsertViewSet , TbListadoServicioViewSet,GroupViewSet 
        
router = DefaultRouter()
router.register(r'relcollabhascontacto', RelCollabHasontactoViewSet, basename='collabhascontacto')
router.register(r'proveedor', TbProveedorViewSet, basename='proveedor')
router.register(r'relprovhascontact', RelProvHasContactViewSet, basename='provhascontact-list-create')
router.register(r'reltenerprov', RelTenerProvViewSet, basename='tenerprov')
router.register(r'categoria', TblCategoriaViewSet, basename='categoria-list-create')
router.register(r'catalogtiempo', TbCatalogTiempoViewSet, basename='catalogtiempo')
router.register(r'catalogactiv', TbCatalogActivViewSet, basename='catalogactiv-list-create')
router.register(r'labor', TbLaborViewSet, basename='laborcomun')
router.register(r'modulo', TbModuloViewSet, basename='modulo')
router.register(r'asignar', RelAsignarViewSet, basename='asignar')
router.register(r'areas', TbAreaViewSet, basename='areas')
router.register(r'areas_con_puestos', TbAreaConPuestosViewSet, basename='areas-con-puestos')
router.register(r'proyectos', TbProyectoViewSet, basename='proyectos')
router.register(r'lineas-negocio', TbLineaNegocioViewSet, basename='linea-negocio')
router.register(r'lineas-servicio', TbLineaServicioViewSet, basename='linea-servicio')
router.register(r'listado-servicios', TbListadoServicioViewSet, basename='listado-servicios')
router.register(r'contactos', TbContactoViewSet, basename='contactos')
router.register(r'direcciones', TbDireccionViewSet, basename='direcciones')
router.register(r'clientes', TbClienteViewSet, basename='clientes')
router.register(r'puestos', TbPuestoViewSet, basename='puestos')
router.register(r'puestos_con_tarifas', TbPuestoConTarifasViewSet, basename='puestos-con-tarifas')
router.register(r'colaboradores', TbColaboradorViewSet, basename='colaboradores')
router.register(r'colaboradores_upsert', UserColaboradorUpsertViewSet, basename='users-colaborador-upsert')
router.register(r'industrias', TblIndustriaViewSet, basename='industrias')
router.register(r'listadoFullDataCliente', RelClienteHasContactoViewSet, basename='relclientehascontacto')
router.register(r'resumen_calor', ResumenLaborMesViewSet, basename='resumen-calor')
router.register(r'labor_detalle', LaborDetalleSerializerViewSet, basename='resumen-detallado-labor')
router.register(r'labor_detalle2', LaborDetalleSinAreaViewSet, basename='resumen-detallado-labor2')
router.register(r'labor_mapa_tabla', LaborDetalleMapaTablaViewSet, basename='labor-mapa-tabla')
router.register(r'labor_mapa_fechas', LaborDetalleMapaFechasViewSet, basename='labor-mapa-fechas')
router.register(r'precioPuestoAnual', TbPrecioPuestoAnualViewSet, basename='precio-puesto-anual')
router.register(r'proyectoPuestoAnio', TbProyectoPuestoAnioViewSet, basename='proyecto-puesto-anio')
router.register(r'users', UserViewSet, basename='users')
router.register(r'grupos', GroupViewSet, basename='grupos')

urlpatterns = [
    path('api/', include(router.urls)),
#   path('api/login/', LoginView.as_view(), name='login'),
#    path('api/register/', RegisterView.as_view(), name='register'),
#   path('api/logout/', LogoutView.as_view(), name='logout'),
    path("colaboradores/promover/", PromoverColaboradorAPIView.as_view(), name="promover-colaborador"),    
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/user/profileCognito/', UserProfileCognito.as_view(), name='user-profile-cognito')
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)