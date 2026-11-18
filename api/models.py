from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
from decimal import Decimal

class TbArea(models.Model):
    id_area = models.AutoField(primary_key=True)
    vc_nomb_area = models.CharField(max_length=45)
    vc_desc = models.TextField(null=True, blank=True, default=None)
    vc_centro_costos = models.CharField(max_length=45,null=True,  blank=True, default=None)
    vc_icono = models.ImageField(upload_to='media/areas/',null=True,blank=True)
    chr_status = models.BooleanField(default=True, null=True)

class TbPuesto(models.Model):
    id_puesto = models.AutoField(primary_key=True)
    id_area = models.ForeignKey(TbArea, on_delete=models.CASCADE)
    vc_puesto = models.CharField(max_length=128, null=True,  blank=True, default=None)
    vc_desc =  models.TextField(null=True, blank=True, default=None)
    chr_status = models.BooleanField(default=True, null=True)

class TbColaborador(models.Model):
    id_colaborador = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='colaborador',null=True, blank=True)  
    id_puesto = models.ForeignKey(TbPuesto, on_delete=models.CASCADE)
    vc_emailPersonal = models.CharField(max_length=45, null=True, blank=True, default=None)
    vc_numEmpleado = models.CharField(max_length=45, null=True, blank=True, default=None)
    vc_telefono = models.CharField(max_length=40, null=True, blank=True, default=None)
    vc_telefonoT = models.CharField(max_length=40, null=True, blank=True, default=None)
    vc_nivelEstudios = models.CharField(max_length=45, null=True, blank=True, default=None)
    dt_ingreso = models.DateField(null=True, blank=True, default=None)
    dt_baja = models.DateField(null=True, blank=True, default=None)
    vc_RFC = models.CharField(max_length=13, null=True, blank=True, default=None)
    vc_consFiscal = models.FileField(upload_to='files/colaboradores/consFiscal', null=True, blank=True)
    vc_clabe = models.CharField(max_length=18, null=True, blank=True, default=None)
    vc_banco = models.CharField(max_length=45, null=True, blank=True, default=None)
    vc_tipoSangre = models.CharField(max_length=45, null=True, blank=True, default=None)
    vc_cv = models.FileField(upload_to='files/colaboradores/cv', null=True, blank=True)
    chr_status = models.BooleanField(default=True, null=True)
    id_direccion = models.ForeignKey('TbDireccion', on_delete=models.SET_NULL, null=True, blank=True, default=None)
    img_colab = models.ImageField(upload_to='media/colaboradores/', null=True, blank=True)
    vc_nota =  models.TextField(null=True, blank=True, default=None)


class TblIndustria(models.Model):
    id_industria = models.AutoField(primary_key=True)
    vc_nombreInd = models.CharField(max_length=255, null=True,  blank=True, default=None)

class TbDireccion(models.Model):
    id_direccion = models.AutoField(primary_key=True)
    vc_num_ext = models.CharField(max_length=255, null=True,  blank=True, default=None)
    vc_num_int = models.CharField(max_length=255, null=True,  blank=True, default=None)
    vc_calle = models.CharField(max_length=255, null=True,  blank=True, default=None)
    vc_localidad = models.CharField(max_length=255, null=True,  blank=True, default=None)
    vc_estado = models.CharField(max_length=255, null=True,  blank=True, default=None)
    vc_codigo_postal = models.CharField(max_length=20, null=True,  blank=True, default=None)
    vc_pais = models.CharField(max_length=50, null=True,  blank=True, default=None)
    chr_status = models.BooleanField(default=True, null=True)

class TbCliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    vc_nomb_cliente = models.CharField(max_length=45)
    vc_desc =  models.TextField(null=True, blank=True, default=None)
    id_industria = models.ForeignKey(TblIndustria, on_delete=models.SET_NULL, null=True,  blank=True, default=None)
    vc_clasifVolActual = models.CharField(max_length=15, null=True,  blank=True, default=None)
    vc_clasifVolPotencial = models.CharField(max_length=15, null=True,  blank=True, default=None)
    bool_clienteActivo = models.BooleanField(null=True,  blank=True, default=None)
    bool_clienteKannbal = models.BooleanField(null=True,  blank=True, default=None)
    bool_prospecto = models.BooleanField(null=True,  blank=True, default=None)
    vc_pais = models.CharField(max_length=50, null=True,  blank=True, default=None)
    vc_distGeografica = models.CharField(max_length=50, null=True,  blank=True, default=None)
    id_direccion = models.ForeignKey('TbDireccion', on_delete=models.SET_NULL, null=True,  blank=True, default=None)
    img_cliente = models.ImageField(upload_to='media/cliente/',null=True,blank=True)
    chr_status = models.BooleanField(default=True, null=True)

class TbLineaNegocio(models.Model):  # Tabla Business Line
    id_lineaNegocio = models.AutoField(primary_key=True)
    vc_nombre = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Ej: CONSULTING, TECHNOLOGY, ESTUDIO
    vc_descripcion =  models.TextField(null=True, blank=True, default=None)  # Descripción opcional

    def __str__(self):
        return self.vc_nombre 
    

class TbLineaServicio(models.Model):  # Tabla Service Line
    id_lineaServicio = models.AutoField(primary_key=True)
    vc_nombre = models.CharField(max_length=255)  # Ej: APRENDIZAJE Y DESARROLLO, LIDERAZGO
    vc_descripcion =  models.TextField(null=True, blank=True, default=None) # Descripción opcional
    vc_linea_negocio = models.ForeignKey(TbLineaNegocio, on_delete=models.CASCADE, related_name='lineas_servicio')

    class Meta:
        unique_together = ('vc_nombre', 'vc_linea_negocio')  # Evitar duplicados dentro de una Línea de Negocio

    def __str__(self):
        return f"{self.vc_nombre} ({self.vc_linea_negocio.vc_nombre})"


class TbListadoServicio(models.Model):  # Tabla Service
    id_servicio = models.AutoField(primary_key=True)
    vc_nombre = models.CharField(max_length=255, null=True, blank=True)  # Ej: ONBOARDING, BOOTCAMPS PARA LÍDERES
    vc_descripcion = models.TextField(null=True, blank=True, default=None)  # Descripción opcional
    id_linea_servicio = models.ForeignKey(TbLineaServicio, on_delete=models.CASCADE, related_name='listado_servicios')

    class Meta:
        unique_together = ('vc_nombre', 'id_linea_servicio') 
    def __str__(self):
        return f"{self.vc_nombre} ({self.id_linea_servicio.vc_nombre})"  # Corregido 'self.linea_servicio' a 'self.id_linea_servicio'


class TbProyecto(models.Model):  # Tabla Proyectos
    id_proyecto  = models.AutoField(primary_key=True)
    vc_nomProy  = models.CharField(max_length=255, null=True, blank=True, default=None) 
    vc_estado = models.CharField(max_length=45, null=True, blank=True, default=None)  
    id_colab_resp  = models.ForeignKey('TbColaborador', on_delete=models.CASCADE, null=True, blank=True, default=None)  
    vc_tipo  = models.CharField(max_length=45, null=True, blank=True, default=None) 
#    dec_costo  = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, default=None) 
#    dec_precio  = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None) 
    dec_presupuestoCollab  = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None) 
    dec_presupuestoProv  = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None) 
    dt_inicio_real  = models.DateField(null=True, blank=True, default=None)  
    dt_fin_real  = models.DateField(null=True, blank=True, default=None) 
    dec_sem_comer  = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=None)  
    vc_desc = models.TextField(null=True, blank=True, default=None)
    vc_producto = models.CharField(max_length=255, null=True, blank=True, default=None) 
    bool_isActive  = models.BooleanField(default=True, null=True)
    img_proyecto = models.ImageField(upload_to='media/proyecto/',null=True,blank=True)
    # Relación jerárquica con TbListadoServicio
    id_servicio = models.ForeignKey(TbListadoServicio, on_delete=models.CASCADE, related_name='proyectos',null=True, blank=True)

    def __str__(self):
        return self.nombre_proyecto


class TbProyCliente(models.Model):
    # Relación con TbProyecto (One-to-One)
    id_proyecto = models.OneToOneField(TbProyecto, on_delete=models.CASCADE, related_name='proy_cliente')

    # Campos relacionados a cliente y propuesta
    id_cliente = models.ForeignKey('TbCliente', on_delete=models.CASCADE, null=True, blank=True)  # Cliente asociado
    vc_nompropuesta  = models.CharField(max_length=255, null=True, blank=True, default=None) 
    dec_precio  = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, default=None) 
    data_cotizador  = models.FileField(upload_to='media/docs/propuesta/cotizador/', null=True, blank=True)  # Archivo de propuesta
    data_propuesta  = models.FileField(upload_to='media/docs/propuesta/data/', null=True, blank=True)  # Archivo de propuesta
    dec_horasfacturables = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True, default=None)  # Horas facturables
    # Campos temporales de proyecto (a futuro mover a tablas relacionales)


    def __str__(self):
        return f"Cliente del Proyecto {self.proyecto.nombre_proyecto}"

class RelAsignar(models.Model):
    id_asignar =models.AutoField(primary_key=True)
    id_colaborador = models.ForeignKey('TbColaborador', on_delete=models.CASCADE)
    id_proyecto = models.ForeignKey(TbProyecto, on_delete=models.CASCADE, null=True,  blank=True, default=None)
    dec_dias_plan = models.DecimalField(max_digits=7, decimal_places=1, null=True,  blank=True, default=None)
    dec_fact = models.DecimalField(max_digits=7, decimal_places=1, null=True,  blank=True, default=None)
    dec_no_fact = models.DecimalField(max_digits=7, decimal_places=1, null=True,  blank=True, default=None)

    class Meta:
        unique_together = ('id_colaborador', 'id_proyecto')
        indexes = [models.Index(fields=['id_proyecto', 'id_colaborador'])]

class TbContacto(models.Model):
    id_contacto = models.AutoField(primary_key=True)
    vc_contacto_nombre = models.CharField(max_length=255, null=True,  blank=True, default=None)
    vc_email = models.CharField(max_length=255, null=True,  blank=True, default=None)
    vc_genero = models.CharField(max_length=255, null=True,  blank=True, default=None)
    vc_celular = models.CharField(max_length=255, null=True,  blank=True, default=None)
    bool_contacto_whatsapp = models.BooleanField(null=True,  blank=True, default=None)
    vc_nacionalidad_contacto = models.CharField(max_length=255, null=True,  blank=True, default=None)
    fecha_cumpleanos = models.DateField(null=True,  blank=True, default=None)
    vc_linkedin = models.TextField(null=True, blank=True, default=None)
    id_direccion = models.ForeignKey('TbDireccion', on_delete=models.SET_NULL, null=True,  blank=True, default=None)
    chr_status = models.BooleanField(default=True, null=True)



class RelClienteHasContacto(models.Model):
    id_ClienteHasContacto = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey('TbCliente', on_delete=models.CASCADE)
    id_contacto = models.ForeignKey('TbContacto', on_delete=models.CASCADE)
    id_RecursoResp = models.ForeignKey('TbColaborador', on_delete=models.SET_NULL, null=True,  blank=True, default=None)
    id_direccion = models.ForeignKey('TbDireccion', on_delete=models.SET_NULL, null=True,  blank=True, default=None)
    int_anioIngreso = models.CharField(max_length=4, null=True,  blank=True, default=None)
    vc_contArea = models.CharField(max_length=50, null=True,  blank=True, default=None)
    vc_contNivInterlocucion = models.CharField(max_length=50, null=True,  blank=True, default=None)
    vc_cargo = models.CharField(max_length=150, null=True,  blank=True, default=None)
    vc_telOficina = models.CharField(max_length=50, null=True,  blank=True, default=None)    
    bool_seguimientoCobro = models.BooleanField(null=True,  blank=True, default=None)
    bool_stillWorking = models.BooleanField(null=True,  blank=True, default=None)
    vc_antiguedadCompania = models.CharField(max_length=50, null=True,  blank=True, default=None)
    vc_NPS = models.CharField(max_length=255, null=True,  blank=True, default=None)
    vc_CompDigital = models.CharField(max_length=255,null=True,  blank=True, default=None)


class RelCollabHasContacto(models.Model):
    id_CollabHasContacto = models.AutoField(primary_key=True)
    id_colaborador = models.ForeignKey('TbColaborador', on_delete=models.CASCADE)
    id_Contacto = models.ForeignKey('TbContacto', on_delete=models.CASCADE)
    bool_emergencia = models.BooleanField(null=True,  blank=True, default=None)

class TbProveedor(models.Model):
    id_prov = models.AutoField(primary_key=True)
    vc_nom_prov = models.CharField(max_length=45)
    vc_tipo = models.CharField(max_length=45)
    vc_desc = models.TextField(null=True, blank=True, default=None)
    vc_RFC = models.CharField(max_length=45)
    chr_status = models.BooleanField(default=True, null=True)

class RelProvHasContact(models.Model):
    id_ProvHasContact = models.AutoField(primary_key=True)
    id_contacto = models.ForeignKey('TbContacto', on_delete=models.CASCADE)
    id_Proveedor = models.ForeignKey(TbProveedor, on_delete=models.CASCADE)

class RelTenerProv(models.Model):
    id_tenerProv = models.AutoField(primary_key=True)
    int_proyecto = models.ForeignKey('TbProyecto', on_delete=models.CASCADE)
    int_prov = models.ForeignKey(TbProveedor, on_delete=models.CASCADE)

class TblCategoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    vc_nombre = models.CharField(max_length=45, null=True, blank=True, default=None)
    vc_desc = models.TextField(null=True, blank=True, default=None)
    chr_status = models.BooleanField(default=True, null=True)

class TbCatalogTiempo(models.Model):
    id_catalogTiempo = models.AutoField(primary_key=True)
    vc_nombre = models.CharField(max_length=45, null=True, blank=True, default=None)
    vc_desc = models.TextField(null=True, blank=True, default=None)

class TbCatalogActiv(models.Model):
    id_codigoAct = models.AutoField(primary_key=True)
    vc_nombre = models.CharField(max_length=255)
    vc_desc = models.TextField(null=True, blank=True, default=None)
    vc_codigo = models.CharField(max_length=4, null=True)
    # Relación con categorías y tiempos específicos por categoría
    categorias = models.ManyToManyField(TblCategoria, through='RelActCatTiempo')
    chr_status = models.BooleanField(default=True, null=True)

class RelActCatTiempo(models.Model):
    id_codigoAct = models.ForeignKey(TbCatalogActiv, on_delete=models.CASCADE)
    id_categoria = models.ForeignKey(TblCategoria, on_delete=models.CASCADE)
    id_catalogTiempo = models.ForeignKey(TbCatalogTiempo, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('id_codigoAct', 'id_categoria')

class TbModulo(models.Model):
    id_modulo = models.AutoField(primary_key=True)
    id_proyecto = models.ForeignKey('TbProyecto', on_delete=models.CASCADE, null=True, blank=True, default=None)
    vc_nombre = models.CharField(max_length=45, null=True, blank=True, default=None)
    vc_descripcion = models.CharField(max_length=400, null=True, blank=True, default=None)
    chr_status = models.BooleanField(default=True, null=True)

class TbLabor(models.Model): 
    id_labor = models.AutoField(primary_key=True)
    id_colaborador = models.ForeignKey('TbColaborador', on_delete=models.CASCADE)
    id_codigoAct = models.ForeignKey(TbCatalogActiv, on_delete=models.CASCADE)
    dt_dia = models.DateTimeField(null=True, blank=True, default=None)
    dec_horasInvertidas = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True, default=None)
    vc_desc = models.CharField(max_length=255, null=True, blank=True, default=None)
    vc_color = models.CharField(max_length=45, null=True, blank=True, default=None)
    en_tipoLabor = models.CharField(max_length=20, choices=[('General', 'General'), ('Proyecto Cliente', 'Proyecto Cliente'), ('Proyecto Interno', 'Proyecto Interno')])
    id_proyecto = models.ForeignKey('TbProyecto', on_delete=models.CASCADE, null=True, blank=True)
    id_modulo = models.ForeignKey('TbModulo', on_delete=models.CASCADE, null=True, blank=True)
    dt_fechaRegistro = models.DateTimeField(null=True,blank=True,auto_now_add=True)
    dt_ultimaActualizacion = models.DateTimeField(null=True,blank=True,auto_now=True)


#  TABULADOR HISTÓRICO DE TARIFAS: (puesto, año) -> precio/hora
class TbPrecioPuestoAnual(models.Model):
    id = models.AutoField(primary_key=True)

    id_puesto = models.ForeignKey( 'TbPuesto', on_delete=models.CASCADE, related_name='precios_anuales' )
    int_anio = models.PositiveIntegerField(help_text="Año calendario (e.g., 2022, 2023, 2024)")
    dec_precio_unitario = models.DecimalField( max_digits=10, decimal_places=2, help_text="Precio/hora del puesto en ese año (tabulador de lista)" )
    dt_fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Precio de Puesto por Año'
        verbose_name_plural = 'Precios de Puesto por Año'
        constraints = [
            models.UniqueConstraint(
                fields=['id_puesto', 'int_anio'],
                name='uq_puesto_anio_en_tabulador'
            )
        ]
        indexes = [
            models.Index(fields=['int_anio', 'id_puesto'], name='ix_tab_anio_puesto'),
            models.Index(fields=['id_puesto'], name='ix_tab_puesto'),
        ]

    def __str__(self):
        return f"{self.id_puesto} {self.int_anio}: {self.dec_precio_unitario}"


class TbProyectoPuestoAnio(models.Model):
    id_proyecto = models.ForeignKey('TbProyecto', on_delete=models.CASCADE)

    # FK al tabulador (puesto + año -> precio unitario)
    id_precioPA = models.ForeignKey(
        'TbPrecioPuestoAnual',
        on_delete=models.CASCADE,
        related_name='proyectos',
        null=True,
        blank=True
    )

    # NUEVO: cuántos puestos de este tipo están asignados al proyecto en ese año
    int_numPuestos = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Cantidad de recursos de ese puesto (>=1)."
    )

    dec_horas_estimadas = models.DecimalField(max_digits=9, decimal_places=2)
    dec_tarifa_hora_override = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('id_proyecto', 'id_precioPA')

    @property
    def tarifa_resuelta(self):
        """Override > precio unitario del tabulador."""
        if self.dec_tarifa_hora_override is not None:
            return self.dec_tarifa_hora_override
        return self.id_precioPA.dec_precio_unitario if self.id_precioPA else None

    @property
    def subtotal(self):
        """
        total = tarifa_resuelta × horas_estimadas × numPuestos
        """
        tarifa = self.tarifa_resuelta
        if tarifa is None or self.dec_horas_estimadas is None or self.int_numPuestos is None:
            return None
        return (
            Decimal(str(tarifa))
            * Decimal(str(self.dec_horas_estimadas))
            * Decimal(str(self.int_numPuestos))
        )

    @property
    def anio(self):
        """Acceso directo al año desde el tabulador."""
        return self.id_precioPA.int_anio if self.id_precioPA else None



class AuditLog(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    metodo = models.CharField(max_length=10)
    endpoint = models.CharField(max_length=255, db_index=True)
    id_obj = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    ip_addr = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    exito = models.BooleanField(default=True, db_index=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "tb_audit_log"
        ordering = ["-fecha"]

    def __str__(self):
        u = self.usuario.username if self.usuario else "Anon"
        id_part = f" id={self.id_obj}" if self.id_obj else ""
        return f"[{self.fecha:%Y-%m-%d %H:%M:%S}] {u} {self.metodo} {self.endpoint}{id_part}"