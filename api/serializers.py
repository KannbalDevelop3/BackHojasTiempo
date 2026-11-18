from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User, Group
from rest_framework import serializers

from .models import (    TbArea,    TbPuesto,    TbColaborador,    TbCliente,    TbLineaNegocio,
    TbLineaServicio,    TbListadoServicio,    TbProyecto,    TbProyCliente,    RelAsignar,
    TbContacto,    TbDireccion,    TblIndustria,    RelClienteHasContacto,    RelCollabHasContacto,
    TbProveedor,    RelProvHasContact,    RelTenerProv,    TblCategoria,    TbCatalogActiv,
    TbLabor,    TbModulo,    TbCatalogTiempo,    RelActCatTiempo,    TbPrecioPuestoAnual,    TbProyectoPuestoAnio,
)


from .utils import decode_base64_image


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


    

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'first_name', 'last_name']

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

class TbAreaMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = TbArea
        fields = ['id_area', 'vc_nomb_area']

class TbPuestoMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = TbPuesto
        fields = ['id_puesto', 'vc_puesto']

class TbPuestoSerializer(serializers.ModelSerializer):
    area = TbAreaMiniSerializer(source='id_area', read_only=True)
    id_area = serializers.PrimaryKeyRelatedField(
        queryset=TbArea.objects.all(), write_only=True
    )

    class Meta:
        model = TbPuesto
        fields = ['id_puesto', 'id_area', 'vc_puesto', 'vc_desc', 'chr_status', 'area']



class TbDireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TbDireccion
        fields = '__all__'


class UserDataColabSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']  # Campos nativos del modelo User

class UserColaboradorUpsertSerializer(serializers.Serializer):
    """
    Upsert unificado de User/TbColaborador.
    - 'grupo_ids' (write-only) asigna grupos.
    - Requiere id_puesto al crear el colaborador (POST o PATCH sobre User sin colaborador).
    """

    # Identificación (la vista resuelve por query param; aquí es informativo)
    user_id = serializers.IntegerField(required=False)
    email = serializers.EmailField(required=False)

    # Datos de User
    username = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name  = serializers.CharField(required=False, allow_blank=True)
    user_email = serializers.EmailField(required=False)

    # Datos de TbColaborador
    id_puesto        = serializers.PrimaryKeyRelatedField(queryset=TbPuesto.objects.all(), required=False, allow_null=True)
    vc_emailPersonal = serializers.CharField(required=False, allow_blank=True)
    vc_numEmpleado   = serializers.CharField(required=False, allow_blank=True)
    vc_telefono      = serializers.CharField(required=False, allow_blank=True)
    vc_telefonoT     = serializers.CharField(required=False, allow_blank=True)
    vc_nivelEstudios = serializers.CharField(required=False, allow_blank=True)
    dt_ingreso       = serializers.DateField(required=False, allow_null=True)
    dt_baja          = serializers.DateField(required=False, allow_null=True)
    vc_RFC           = serializers.CharField(required=False, allow_blank=True)
    vc_consFiscal    = serializers.FileField(required=False, allow_null=True)
    vc_clabe         = serializers.CharField(required=False, allow_blank=True)
    vc_banco         = serializers.CharField(required=False, allow_blank=True)
    vc_cv            = serializers.FileField(required=False, allow_null=True)
    img_colab        = serializers.ImageField(required=False, allow_null=True)
    chr_status       = serializers.BooleanField(required=False)

    # Dirección anidada
    direccion_usuario = TbDireccionSerializer(required=False)

    # Grupos (entrada)
    grupo_ids = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), many=True, required=False, write_only=True
    )

    # --------- Representación ---------
    def to_representation(self, instance):
        if isinstance(instance, User):
            data = UserSerializer(instance).data
            data['grupos'] = list(instance.groups.values('id', 'name'))
            colab = TbColaborador.objects.filter(user=instance).select_related('id_puesto', 'id_direccion').first()
            if colab:
                data['colaborador'] = TbColaboradorSerializer(colab).data
            return data
        if isinstance(instance, TbColaborador):
            return TbColaboradorSerializer(instance).data
        return {}

    # --------- Validación cruzada ---------
    def validate(self, attrs):
        """
        Exige id_puesto cuando se vaya a crear TbColaborador:
          - POST (create)
          - PATCH sobre User que aún no tiene colaborador
        Valida unicidad de username (permitiendo el propio en edición).
        """
        instance = getattr(self, 'instance', None)

        will_create_colab = False
        if instance is None:
            will_create_colab = True
        elif isinstance(instance, User):
            if not TbColaborador.objects.filter(user=instance).exists():
                will_create_colab = True

        if will_create_colab and not attrs.get('id_puesto'):
            raise serializers.ValidationError({'id_puesto': 'Este campo es obligatorio para crear el colaborador.'})

        username = attrs.get('username')
        if username:
            qs = User.objects.filter(username=username)
            if isinstance(instance, User):
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'username': 'Ya existe un usuario con ese username.'})

        return attrs

    # --------- CREATE ---------
    def create(self, validated):
        grupo_ids = validated.pop('grupo_ids', [])
        username  = validated.get('username')

        # Dirección (opcional)
        direccion = None
        dir_data = validated.get('direccion_usuario')
        if isinstance(dir_data, dict):
            dir_ser = TbDireccionSerializer(data=dir_data)
            dir_ser.is_valid(raise_exception=True)
            direccion = dir_ser.save()

        # Datos base
        first_name = validated.get('first_name') or ''
        last_name  = validated.get('last_name') or ''
        email      = validated.get('user_email') or ''

        # Crear User (opcional)
        user = None
        if username:
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            if validated.get('password'):
                user.password = make_password(validated['password'])
                user.save(update_fields=['password'])
            if grupo_ids:
                user.groups.set(grupo_ids)

        # Chequeo duro antes de crear colaborador
        if not validated.get('id_puesto'):
            raise serializers.ValidationError({'id_puesto': 'Este campo es obligatorio para crear el colaborador.'})

        colab = TbColaborador.objects.create(
            user=user,
            id_puesto=validated.get('id_puesto'),
            vc_emailPersonal=validated.get('vc_emailPersonal'),
            vc_numEmpleado=validated.get('vc_numEmpleado'),
            vc_telefono=validated.get('vc_telefono'),
            vc_telefonoT=validated.get('vc_telefonoT'),
            vc_nivelEstudios=validated.get('vc_nivelEstudios'),
            dt_ingreso=validated.get('dt_ingreso'),
            dt_baja=validated.get('dt_baja'),
            vc_RFC=validated.get('vc_RFC'),
            vc_consFiscal=validated.get('vc_consFiscal'),
            vc_clabe=validated.get('vc_clabe'),
            vc_banco=validated.get('vc_banco'),
            vc_cv=validated.get('vc_cv'),
            img_colab=validated.get('img_colab'),
            chr_status=validated.get('chr_status', True),
            id_direccion=direccion,
            # Locales si no hay user
            first_name=first_name if not user else None,
            last_name=last_name if not user else None,
            email=email if not user else None,
        )
        return user or colab

    # --------- UPDATE ---------
    def update(self, instance, validated):
        grupo_ids = validated.pop('grupo_ids', None)

        # ===== Caso A: instance = TbColaborador =====
        if isinstance(instance, TbColaborador):
            colab = instance

            # Campos de colaborador
            for f in (
                'id_puesto', 'vc_emailPersonal', 'vc_numEmpleado', 'vc_telefono',
                'vc_telefonoT', 'vc_nivelEstudios', 'dt_ingreso', 'dt_baja', 'vc_RFC',
                'vc_consFiscal', 'vc_clabe', 'vc_banco', 'vc_cv', 'img_colab', 'chr_status'
            ):
                if f in validated:
                    setattr(colab, f, validated.get(f))

            # Dirección
            dir_data = validated.get('direccion_usuario')
            if isinstance(dir_data, dict):
                if colab.id_direccion:
                    dir_ser = TbDireccionSerializer(colab.id_direccion, data=dir_data, partial=True)
                    dir_ser.is_valid(raise_exception=True)
                    dir_ser.save()
                else:
                    dir_ser = TbDireccionSerializer(data=dir_data)
                    dir_ser.is_valid(raise_exception=True)
                    colab.id_direccion = dir_ser.save()

            # Si tiene user, también actualizarlo
            if colab.user:
                user = colab.user
                user_fields = {}
                if 'first_name' in validated: user_fields['first_name'] = validated['first_name'] or ''
                if 'last_name'  in validated: user_fields['last_name']  = validated['last_name']  or ''
                if 'user_email' in validated: user_fields['email']      = validated['user_email'] or ''
                if 'username'   in validated and validated['username']:
                    user_fields['username'] = validated['username']
                if user_fields:
                    for k, v in user_fields.items():
                        setattr(user, k, v)
                    user.save()
                if validated.get('password'):
                    user.password = make_password(validated['password'])
                    user.save(update_fields=['password'])
                if grupo_ids is not None:
                    user.groups.set(grupo_ids)
            else:
                # Sin user: actualizar locales o promover a User si llega username
                if 'first_name' in validated: colab.first_name = validated['first_name'] or ''
                if 'last_name'  in validated: colab.last_name  = validated['last_name']  or ''
                if 'user_email' in validated: colab.email      = validated['user_email'] or ''
                if validated.get('username'):
                    username = validated['username']
                    user = User.objects.create(
                        username=username,
                        email=validated.get('user_email') or colab.email or '',
                        first_name=validated.get('first_name') or colab.first_name or '',
                        last_name=validated.get('last_name')  or colab.last_name  or '',
                    )
                    if validated.get('password'):
                        user.password = make_password(validated['password'])
                        user.save(update_fields=['password'])
                    if grupo_ids:
                        user.groups.set(grupo_ids)
                    colab.user = user

            colab.save()
            return colab

        # ===== Caso B: instance = User =====
        user = instance

        # User fields
        user_fields = {}
        for f in ['user_email', 'first_name', 'last_name', 'username']:
            if f in validated:
                field = 'email' if f == 'user_email' else f
                user_fields[field] = validated.get(f) or ''
        if user_fields:
            for k, v in user_fields.items():
                setattr(user, k, v)
            user.save()

        if validated.get('password'):
            user.password = make_password(validated['password'])
            user.save(update_fields=['password'])

        if grupo_ids is not None:
            user.groups.set(grupo_ids)

        # Upsert de colaborador SIN get_or_create (evita NOT NULL)
        colab = TbColaborador.objects.filter(user=user).first()
        if not colab:
            id_puesto_obj = validated.get('id_puesto')
            if not id_puesto_obj:
                raw_id = self.initial_data.get('id_puesto')
                if not raw_id:
                    raise serializers.ValidationError({'id_puesto': 'Este campo es obligatorio para crear el colaborador.'})
                try:
                    id_puesto_obj = TbPuesto.objects.get(pk=raw_id)
                except TbPuesto.DoesNotExist:
                    raise serializers.ValidationError({'id_puesto': f'No existe TbPuesto con id={raw_id}.'})

            colab = TbColaborador.objects.create(
                user=user,
                id_puesto=id_puesto_obj,
                first_name=validated.get('first_name') or None,
                last_name=validated.get('last_name') or None,
                email=validated.get('user_email') or None,
            )

        # Campos del colaborador
        for f in (
            'id_puesto', 'vc_emailPersonal', 'vc_numEmpleado', 'vc_telefono',
            'vc_telefonoT', 'vc_nivelEstudios', 'dt_ingreso', 'dt_baja', 'vc_RFC',
            'vc_consFiscal', 'vc_clabe', 'vc_banco', 'vc_cv', 'img_colab', 'chr_status'
        ):
            if f in validated:
                setattr(colab, f, validated.get(f))

        # Dirección
        dir_data = validated.get('direccion_usuario')
        if isinstance(dir_data, dict):
            if colab.id_direccion:
                dir_ser = TbDireccionSerializer(colab.id_direccion, data=dir_data, partial=True)
                dir_ser.is_valid(raise_exception=True)
                dir_ser.save()
            else:
                dir_ser = TbDireccionSerializer(data=dir_data)
                dir_ser.is_valid(raise_exception=True)
                colab.id_direccion = dir_ser.save()

        colab.save()
        return user

class TbColaboradorSerializer(serializers.ModelSerializer):
    # relaciones enriquecidas
    puesto = TbPuestoSerializer(source='id_puesto', read_only=True)
    direccion = TbDireccionSerializer(source='id_direccion', read_only=True)

    # campos calculados
    username = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()

    # grupos debe mostrarse solo si hay user
    grupos = serializers.SerializerMethodField()

    class Meta:
        model = TbColaborador
        fields = '__all__'  # incluye todos los campos del modelo + los calculados

    def get_username(self, obj):
        return obj.user.username if obj.user_id else None

    def get_first_name(self, obj):
        return obj.user.first_name if obj.user_id else obj.first_name

    def get_last_name(self, obj):
        return obj.user.last_name if obj.user_id else obj.last_name

    def get_email(self, obj):
        return obj.user.email if obj.user_id else obj.email

    def get_nombre_completo(self, obj):
        fn = self.get_first_name(obj) or ''
        ln = self.get_last_name(obj) or ''
        return f"{fn} {ln}".strip()

    def get_grupos(self, obj):
        if not obj.user_id:
            return None
        return list(obj.user.groups.values('id', 'name'))

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if data.get('grupos') is None:
            data.pop('grupos', None)
        return data

class TbColaboradorMinimalSerializer(serializers.ModelSerializer):
    puesto = TbPuestoSerializer(source='id_puesto', read_only=True)
    direccion = TbDireccionSerializer(source='id_direccion', read_only=True)
    usuario = UserDataColabSerializer(source='user', read_only=True)

    class Meta:
        model = TbColaborador
        fields = ['puesto', 'direccion', 'usuario', 'vc_emailPersonal', 'img_colab']

from rest_framework import serializers
from .models import TbColaborador, TbPuesto

class TbColaboradorUpdateSerializer(serializers.Serializer):
    # Campos editables de TbColaborador (todos opcionales; PATCH parcial)
    id_puesto        = serializers.PrimaryKeyRelatedField(queryset=TbPuesto.objects.all(), required=False)
    first_name       = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    last_name        = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email            = serializers.EmailField(required=False, allow_null=True)
    vc_emailPersonal = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vc_numEmpleado   = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vc_telefono      = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vc_telefonoT     = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vc_nivelEstudios = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    dt_ingreso       = serializers.DateField(required=False, allow_null=True)
    dt_baja          = serializers.DateField(required=False, allow_null=True)
    vc_RFC           = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vc_consFiscal    = serializers.FileField(required=False, allow_null=True)
    vc_clabe         = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vc_banco         = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vc_cv            = serializers.FileField(required=False, allow_null=True)
    img_colab        = serializers.ImageField(required=False, allow_null=True)
    chr_status       = serializers.BooleanField(required=False)
    vc_tipoSangre    = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vc_nota          = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Dirección anidada (upsert parcial sobre TbDireccion)
    direccion_usuario = serializers.DictField(required=False)

    def to_representation(self, instance):
        # Usa tu serializer “rico” para salida
        from .serializers import TbColaboradorSerializer  # evita dependencia circular en import de módulo
        return TbColaboradorSerializer(instance).data

    def create(self, validated_data):
        raise NotImplementedError("Este serializer no crea TbColaborador, solo actualiza.")

    def update(self, instance: TbColaborador, validated_data):
        # Campos simples
        for f in (
            'id_puesto', 'first_name', 'last_name', 'email', 'vc_emailPersonal', 'vc_numEmpleado',
            'vc_telefono', 'vc_telefonoT', 'vc_nivelEstudios', 'dt_ingreso', 'dt_baja', 'vc_RFC',
            'vc_consFiscal', 'vc_clabe', 'vc_banco', 'vc_cv', 'img_colab', 'chr_status',
            'vc_tipoSangre', 'vc_nota'
        ):
            if f in validated_data:
                setattr(instance, f, validated_data.get(f))

        # Dirección anidada
        if 'direccion_usuario' in validated_data and isinstance(validated_data['direccion_usuario'], dict):
            from .serializers import TbDireccionSerializer  # import local para evitar ciclos
            dir_data = validated_data['direccion_usuario']
            if instance.id_direccion:
                dir_ser = TbDireccionSerializer(instance.id_direccion, data=dir_data, partial=True)
                dir_ser.is_valid(raise_exception=True)
                dir_ser.save()
            else:
                dir_ser = TbDireccionSerializer(data=dir_data)
                dir_ser.is_valid(raise_exception=True)
                instance.id_direccion = dir_ser.save()

        instance.save()
        return instance


class UserSerializer(serializers.ModelSerializer):
    colaborador = TbColaboradorSerializer(read_only=True)
    grupos = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'colaborador', 'grupos'
        ]

    def get_grupos(self, obj):
        if not hasattr(obj, '_prefetched_objects_cache') or 'groups' not in obj._prefetched_objects_cache:
            obj = User.objects.prefetch_related('groups').filter(pk=obj.pk).first() or obj
        return list(obj.groups.values('id', 'name'))


class TblIndustriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TblIndustria
        fields = '__all__'

class TbClienteSerializer(serializers.ModelSerializer):
    # Solo lectura (embed)
    industria = TblIndustriaSerializer(source='id_industria', read_only=True)
    direccion = TbDireccionSerializer(source='id_direccion', read_only=True)

    # Escritura por PK (recomendado poner write_only para no duplicar info en la salida)
    id_direccion = serializers.PrimaryKeyRelatedField(
        queryset=TbDireccion.objects.all(),
        required=False,
        allow_null=True,
        write_only=True
    )

    # Escritura anidada para crear/actualizar dirección en el mismo POST/PATCH
    direccion_cliente = TbDireccionSerializer(write_only=True, required=False)

    class Meta:
        model = TbCliente
        fields = '__all__'  # Incluye los campos declarados arriba

    def create(self, validated_data):
        # Si viene la dirección anidada, se crea y se asigna
        dir_data = validated_data.pop('direccion_cliente', None)
        if dir_data:
            direccion = TbDireccion.objects.create(**dir_data)
            validated_data['id_direccion'] = direccion

        # Si viene id_direccion como PK, DRF ya lo convirtió en instancia
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Permitir actualizar/crear dirección anidada también en PATCH/PUT
        dir_data = validated_data.pop('direccion_cliente', None)
        if dir_data:
            if instance.id_direccion:
                # Actualizamos la dirección existente con partial=True
                dir_serializer = TbDireccionSerializer(
                    instance.id_direccion, data=dir_data, partial=True
                )
                dir_serializer.is_valid(raise_exception=True)
                dir_serializer.save()
            else:
                # Creamos y vinculamos si no existía
                instance.id_direccion = TbDireccion.objects.create(**dir_data)
                instance.save(update_fields=['id_direccion'])

        return super().update(instance, validated_data)

class TbAreaConPuestosSerializer(serializers.ModelSerializer):
    puestos = TbPuestoMiniSerializer(source='tbpuesto_set', many=True, read_only=True)

    class Meta:
        model = TbArea
        fields = ['id_area', 'vc_nomb_area', 'puestos']


class TbAreaSerializer(serializers.ModelSerializer):
    colaboradores = TbColaboradorSerializer(many=True, read_only=True)
    puestos = TbPuestoSerializer(many=True, read_only=True)

    class Meta:
        model = TbArea
        fields = '__all__'


class TbContactoSerializer(serializers.ModelSerializer):
    Direccion_Personal = TbDireccionSerializer(source='id_direccion', read_only=False, required=False)
    fecha_cumpleanos = serializers.DateField(required=False, allow_null=True)
    
    class Meta:
        model = TbContacto
        fields = '__all__'

    def create(self, validated_data):
        direccion_data = validated_data.pop('id_direccion', None)
        if direccion_data:
            direccion = TbDireccion.objects.create(**direccion_data)
            validated_data['id_direccion'] = direccion
        return super().create(validated_data)

    def to_internal_value(self, data):
        data = data.copy()
        if isinstance(data, dict) and data.get('fecha_cumpleanos', None) == "":
            data['fecha_cumpleanos'] = None
        return super().to_internal_value(data)

class TbProyClienteSerializer(serializers.ModelSerializer):
    cliente = TbClienteSerializer(source='id_cliente', read_only=True)  # Relación anidada

    class Meta:
        model = TbProyCliente
        fields = '__all__'


class TbLineaNegocioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TbLineaNegocio
        fields = ['id_lineaNegocio', 'vc_nombre', 'vc_descripcion']


class TbLineaServicioSerializer(serializers.ModelSerializer):
    linea_negocio = TbLineaNegocioSerializer(source='vc_linea_negocio', read_only=True)

    class Meta:
        model = TbLineaServicio
        fields = ['id_lineaServicio', 'vc_nombre', 'vc_descripcion', 'vc_linea_negocio', 'linea_negocio']


class TbListadoServicioSerializer(serializers.ModelSerializer):
    linea_servicio = TbLineaServicioSerializer(source='id_linea_servicio', read_only=True)

    class Meta:
        model = TbListadoServicio
        fields = ['id_servicio', 'vc_nombre', 'vc_descripcion', 'id_linea_servicio', 'linea_servicio']


class TbProyectoSerializer(serializers.ModelSerializer):
    # ---------- Escritura ----------
    id_colab_resp = serializers.PrimaryKeyRelatedField(
        queryset=TbColaborador.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    img_proyecto = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
    )

    # ---------- Lectura enriquecida ----------
    responsable = TbColaboradorMinimalSerializer(source='id_colab_resp', read_only=True)
    servicio = TbListadoServicioSerializer(source='id_servicio', read_only=True)

    # Lectura: objeto cliente/proyecto
    proy_cliente = TbProyClienteSerializer(read_only=True)
    # Alias de lectura para el front: mismo contenido que proy_cliente
    proy_cliente_data = TbProyClienteSerializer(source='proy_cliente', read_only=True)

    # ---------- Campos calculados ----------
    dec_precio = serializers.SerializerMethodField(read_only=True)
    dec_presupuestoCollab = serializers.SerializerMethodField(read_only=True)
    dec_costo = serializers.SerializerMethodField(read_only=True)
    dec_ganancia = serializers.SerializerMethodField(read_only=True)
    dec_margen = serializers.SerializerMethodField(read_only=True)
    puestos_anio = serializers.SerializerMethodField(read_only=True)
    total_puestos_anio = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TbProyecto
        fields = [
            'id_proyecto', 'vc_nomProy', 'img_proyecto', 'vc_estado', 'vc_tipo',
            'id_colab_resp', 'responsable',
            'dec_precio', 'dec_presupuestoCollab', 'dec_presupuestoProv',
            'dec_costo', 'dec_ganancia', 'dec_margen',
            'dt_inicio_real', 'dt_fin_real', 'dec_sem_comer', 'vc_desc',
            'vc_producto', 'bool_isActive',
            'servicio', 'proy_cliente', 'proy_cliente_data',
            'puestos_anio', 'total_puestos_anio',
        ]

    # ---------- Base64 Imagen ----------
    def _handle_image(self, validated_data):
        from .utils import decode_base64_image  # asegura que exista el import

        img_b64 = validated_data.pop('img_proyecto', None)
        if img_b64:
            image, size = decode_base64_image(img_b64)
            if not image:
                raise serializers.ValidationError({
                    "img_proyecto": f"Imagen inválida o excede el tamaño permitido ({size} KB)"
                })
            validated_data['img_proyecto'] = image
        return validated_data

    # ---------- CREATE ----------
    def create(self, validated_data):
        # OJO: tomamos los datos RAW que manda el front, no los validados,
        # para no tener problemas con id_proyecto requerido en TbProyCliente.
        cliente_data = self.initial_data.get('proy_cliente_data')
        validated_data = self._handle_image(validated_data)

        proyecto = super().create(validated_data)

        # Si vienen datos de cliente, creamos TbProyCliente
        if isinstance(cliente_data, dict) and cliente_data:
            from .models import TbProyCliente

            TbProyCliente.objects.create(
                id_proyecto=proyecto,
                # El front manda "id_cliente": <int>
                id_cliente_id=cliente_data.get('id_cliente'),
                vc_nompropuesta=cliente_data.get('vc_nompropuesta'),
                dec_precio=cliente_data.get('dec_precio'),
                dec_horasfacturables=cliente_data.get('dec_horasfacturables'),
            )

        return proyecto

    # ---------- UPDATE ----------
    def update(self, instance, validated_data):
        cliente_data = self.initial_data.get('proy_cliente_data')
        validated_data = self._handle_image(validated_data)

        proyecto = super().update(instance, validated_data)

        # Si vienen datos de cliente, actualizamos/creamos TbProyCliente
        if isinstance(cliente_data, dict):
            from .models import TbProyCliente

            if cliente_data:
                TbProyCliente.objects.update_or_create(
                    id_proyecto=proyecto,
                    defaults={
                        'id_cliente_id': cliente_data.get('id_cliente'),
                        'vc_nompropuesta': cliente_data.get('vc_nompropuesta'),
                        'dec_precio': cliente_data.get('dec_precio'),
                        'dec_horasfacturables': cliente_data.get('dec_horasfacturables'),
                    },
                )
            # Si quieres que un PATCH con "proy_cliente_data": {} borre la relación,
            # puedes descomentar lo siguiente:
            # else:
            #     TbProyCliente.objects.filter(id_proyecto=proyecto).delete()

        return proyecto

    # ---------- Auxiliar: Año desde contexto ----------
    def _anio_from_context(self):
        anio = self.context.get('int_anio')
        try:
            return int(anio)
        except (TypeError, ValueError):
            return None

    # ---------- Campos Calculados ----------
    def get_dec_precio(self, obj):
        pc = getattr(obj, 'proy_cliente', None)
        return float(pc.dec_precio) if pc and pc.dec_precio is not None else None

    def get_dec_presupuestoCollab(self, obj):
        from .models import TbProyectoPuestoAnio

        anio = self._anio_from_context()
        if anio is None:
            return None
        total = sum([
            getattr(row, 'subtotal', Decimal('0'))
            for row in TbProyectoPuestoAnio.objects.filter(
                id_proyecto=obj, id_precioPA__int_anio=anio
            )
        ])
        return float(total) if total else 0.0

    def get_dec_costo(self, obj):
        collab = self.get_dec_presupuestoCollab(obj)
        prov = getattr(obj, 'dec_presupuestoProv', None)
        total = Decimal(str(collab or 0)) + Decimal(str(prov or 0))
        return float(total)

    def get_dec_ganancia(self, obj):
        precio = self.get_dec_precio(obj)
        costo = self.get_dec_costo(obj)
        if precio is None or costo is None:
            return None
        return float(Decimal(str(precio)) - Decimal(str(costo)))

    def get_dec_margen(self, obj):
        ganancia = self.get_dec_ganancia(obj)
        costo = self.get_dec_costo(obj)
        if not ganancia or not costo:
            return None
        try:
            margen = (Decimal(str(ganancia)) / Decimal(str(costo))) * 100
            return f"{margen.quantize(Decimal('0.01'))}%"
        except (InvalidOperation, ZeroDivisionError):
            return None

    def get_puestos_anio(self, obj):
        from .models import TbProyectoPuestoAnio
        from .serializers import TbProyectoPuestoAnioSerializer

        anio = self._anio_from_context()
        if anio is None:
            return None
        qs = TbProyectoPuestoAnio.objects.filter(
            id_proyecto=obj, id_precioPA__int_anio=anio
        ).select_related('id_precioPA__id_puesto')
        return TbProyectoPuestoAnioSerializer(qs, many=True, context={'int_anio': anio}).data

    def get_total_puestos_anio(self, obj):
        from .models import TbProyectoPuestoAnio

        anio = self._anio_from_context()
        if anio is None:
            return None
        total = sum([
            getattr(row, 'subtotal', Decimal('0'))
            for row in TbProyectoPuestoAnio.objects.filter(
                id_proyecto=obj, id_precioPA__int_anio=anio
            )
        ])
        return float(total)



class RelAsignarSerializer(serializers.ModelSerializer):
    colaborador_id = serializers.PrimaryKeyRelatedField(
        source='id_colaborador', queryset=TbColaborador.objects.all(), required=True
    )
    proyecto_id = serializers.PrimaryKeyRelatedField(
        source='id_proyecto', queryset=TbProyecto.objects.all(), required=True
    )

    # Acepta números o strings para decimales
    dec_dias_plan = serializers.DecimalField(max_digits=7, decimal_places=1, required=False, allow_null=True)
    dec_fact      = serializers.DecimalField(max_digits=7, decimal_places=1, required=False, allow_null=True)
    dec_no_fact   = serializers.DecimalField(max_digits=7, decimal_places=1, required=False, allow_null=True)

    colaborador = TbColaboradorSerializer(source='id_colaborador', read_only=True)
    proyecto    = TbProyectoSerializer(source='id_proyecto', read_only=True)

    class Meta:
        model = RelAsignar
        fields = [
            'id_asignar', 'dec_dias_plan', 'dec_fact', 'dec_no_fact',
            'colaborador_id', 'proyecto_id',
            'colaborador', 'proyecto'
        ]

    def validate(self, attrs):
        col = attrs.get('id_colaborador') or getattr(self.instance, 'id_colaborador', None)
        pro = attrs.get('id_proyecto')    or getattr(self.instance, 'id_proyecto', None)
        if col and pro:
            qs = RelAsignar.objects.filter(id_colaborador=col, id_proyecto=pro)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Ya existe una asignación para ese colaborador en ese proyecto.")
        return attrs



class RelClienteHasContactoSerializer(serializers.ModelSerializer):
    # ---- Lectura (embed) ----
    cliente = TbClienteSerializer(source='id_cliente', read_only=True)
    contacto = TbContactoSerializer(source='id_contacto', read_only=True)
    recurso_Responsable = TbColaboradorSerializer(source='id_RecursoResp', read_only=True)
    direccionOficina = TbDireccionSerializer(source='id_direccion', read_only=True)

    # ---- Escritura ----
    id_contacto = serializers.PrimaryKeyRelatedField(
        queryset=TbContacto.objects.all(),
        required=False, allow_null=True, write_only=True
    )
    data_contacto = TbContactoSerializer(source='id_contacto', required=False)
    data_cliente = TbClienteSerializer(source='id_cliente', required=False)
    data_direccion = TbDireccionSerializer(source='id_direccion', required=False)

    class Meta:
        model = RelClienteHasContacto
        fields = '__all__'
        extra_kwargs = {
            'id_contacto': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        # ---- Cliente anidado (opcional) ----
        if isinstance(validated_data.get('id_cliente'), dict):
            cliente_data = validated_data.pop('id_cliente')
            dir_cli = cliente_data.pop('id_direccion', None)
            if isinstance(dir_cli, dict):
                dir_cli = TbDireccion.objects.create(**dir_cli)
                cliente_data['id_direccion'] = dir_cli
            cliente = TbCliente.objects.create(**cliente_data)
            validated_data['id_cliente'] = cliente

        # ---- Contacto anidado (opcional) ----
        if isinstance(validated_data.get('id_contacto'), dict):
            contacto_data = validated_data.pop('id_contacto')
            dir_cto = contacto_data.pop('id_direccion', None)
            if isinstance(dir_cto, dict):
                dir_cto = TbDireccion.objects.create(**dir_cto)
                contacto_data['id_direccion'] = dir_cto
            contacto = TbContacto.objects.create(**contacto_data)
            validated_data['id_contacto'] = contacto

        # ---- Dirección anidada para la relación ----
        if isinstance(validated_data.get('id_direccion'), dict):
            dir_rel = validated_data.pop('id_direccion')
            dir_rel = TbDireccion.objects.create(**dir_rel)
            validated_data['id_direccion'] = dir_rel

        return super().create(validated_data)




class RelProvHasContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelProvHasContact
        fields = '__all__'


class TbProveedorSerializer(serializers.ModelSerializer):
    # Serializer anidado para RelProvHasContact
    contactos = RelProvHasContactSerializer(many=True, read_only=True)

    class Meta:
        model = TbProveedor
        fields = '__all__'

class RelCollabHasContactoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelCollabHasContacto
        fields = '__all__'

class RelTenerProvSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelTenerProv
        fields = '__all__'
        
class TblCategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TblCategoria
        fields = ['id_categoria', 'vc_nombre', 'vc_desc', 'chr_status']

class TbCatalogTiempoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TbCatalogTiempo
        fields = ['id_catalogTiempo', 'vc_nombre', 'vc_desc']
        
class RelActCatTiempoSerializer(serializers.ModelSerializer):
    id_categoria = TblCategoriaSerializer()  # Anidar datos de la categoría
    id_catalogTiempo = TbCatalogTiempoSerializer()  # Anidar datos del tiempo

    class Meta:
        model = RelActCatTiempo
        fields = ['id_categoria', 'id_catalogTiempo']

class TblCategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TblCategoria
        fields = '__all__'


class TbCatalogActivSerializer(serializers.ModelSerializer):
    categorias = RelActCatTiempoSerializer(many=True, source='relactcattiempo_set', read_only=True)
    # relaciones: [{"id_categoria": <int>, "id_catalogTiempo": <int>}, ...]
    relaciones = serializers.ListField(write_only=True, child=serializers.DictField(), required=False)

    class Meta:
        model = TbCatalogActiv
        fields = ['id_codigoAct', 'vc_nombre', 'vc_desc', 'vc_codigo', 'categorias', 'relaciones','chr_status']

    def create(self, validated_data):
        relaciones = validated_data.pop('relaciones', [])
        activ = TbCatalogActiv.objects.create(**validated_data)

        # Crear las relaciones en la tabla intermedia
        from .models import RelActCatTiempo, TblCategoria, TbCatalogTiempo
        rel_objs = []
        for item in relaciones:
            id_cat = item.get('id_categoria')
            id_time = item.get('id_catalogTiempo')
            if id_cat is None or id_time is None:
                # Puedes decidir: ignorar, o lanzar error
                raise serializers.ValidationError("Cada relación requiere 'id_categoria' e 'id_catalogTiempo'.")
            rel_objs.append(RelActCatTiempo(
                id_codigoAct=activ,
                id_categoria=TblCategoria.objects.get(pk=id_cat),
                id_catalogTiempo=TbCatalogTiempo.objects.get(pk=id_time),
            ))
        if rel_objs:
            RelActCatTiempo.objects.bulk_create(rel_objs, ignore_conflicts=True) 

        return activ

    def update(self, instance, validated_data):
        relaciones = validated_data.pop('relaciones', None)
        instance = super().update(instance, validated_data)

        if relaciones is not None:
            from .models import RelActCatTiempo, TblCategoria, TbCatalogTiempo
            # estrategia simple: limpiar y volver a crear
            RelActCatTiempo.objects.filter(id_codigoAct=instance).delete()
            rel_objs = []
            for item in relaciones:
                id_cat = item.get('id_categoria')
                id_time = item.get('id_catalogTiempo')
                if id_cat is None or id_time is None:
                    raise serializers.ValidationError("Cada relación requiere 'id_categoria' e 'id_catalogTiempo'.")
                rel_objs.append(RelActCatTiempo(
                    id_codigoAct=instance,
                    id_categoria=TblCategoria.objects.get(pk=id_cat),
                    id_catalogTiempo=TbCatalogTiempo.objects.get(pk=id_time),
                ))
            if rel_objs:
                RelActCatTiempo.objects.bulk_create(rel_objs, ignore_conflicts=True)

        return instance



class TbLaborSerializer(serializers.ModelSerializer):
    codigoAct = TbCatalogActivSerializer(source='id_codigoAct', read_only=True)
    colaborador = TbColaboradorSerializer(source='id_colaborador', read_only=True)
    dec_horasInvertidas = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = TbLabor
        fields = '__all__'

    def validate_dec_horasInvertidas(self, value):
        """Convierte el valor hh:mm a decimal (por ejemplo 2:30 -> 2.5)."""
        if value:
            try:
                parts = value.split(':')
                if len(parts) != 2:
                    raise ValueError
                hours, minutes = map(int, parts)
                if minutes < 0 or minutes >= 60:
                    raise ValueError
                return round(hours + minutes / 60.0, 4)  # Precisión de 4 decimales
            except ValueError:
                raise serializers.ValidationError("El formato de horas debe ser hh:mm y los minutos deben estar entre 00 y 59.")
        return value

    def to_representation(self, instance):
        """Convierte el valor decimal a hh:mm al leer los datos."""
        representation = super().to_representation(instance)
        if instance.dec_horasInvertidas is not None:
            total_minutes = round(instance.dec_horasInvertidas * 60)  # Redondeo para precisión
            hours, minutes = divmod(total_minutes, 60)  # Obtiene horas y minutos

            # Ajustar en caso de redondeo que lleve a 60 minutos
            if minutes == 60:
                hours += 1
                minutes = 0

            representation['dec_horasInvertidas'] = f"{hours}:{minutes:02d}"
        return representation

    def create(self, validated_data):
        if isinstance(validated_data, list):
            return TbLabor.objects.bulk_create([TbLabor(**item) for item in validated_data])
        return TbLabor.objects.create(**validated_data)

class TbModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = TbModulo
        fields = '__all__'


class LaborResumenMesSerializer(serializers.Serializer):
    nombre_colaborador = serializers.CharField()
    mes = serializers.CharField()
    total_horas = serializers.DecimalField(max_digits=10, decimal_places=2)


class LaborDetalleSerializer(serializers.Serializer):
    proyecto = serializers.CharField()
    nombre_colaborador = serializers.CharField()
    nombre_actividad = serializers.CharField()
    comentarios = serializers.CharField(allow_blank=True)  # Permite valores en blanco
    mes = serializers.CharField()
    area = serializers.CharField()
    total_horas_decimal = serializers.DecimalField(max_digits=10, decimal_places=2)
    tipo_tiempo = serializers.CharField()  

class LaborDetalleSinAreaSerializer(serializers.Serializer):
    proyecto = serializers.CharField()
    cliente = serializers.CharField(required=False, allow_blank=True, allow_null=True) 
    nombre_colaborador = serializers.CharField()
    nombre_actividad = serializers.CharField()
    comentarios = serializers.CharField(allow_blank=True)
    mes = serializers.CharField()
    total_horas_decimal = serializers.DecimalField(max_digits=10, decimal_places=2)
    tipo_tiempo = serializers.CharField()

#serializer por fecha
class LaborDetallePorFechaSerializer(serializers.Serializer):
    proyecto = serializers.CharField()
    nombre_colaborador = serializers.CharField()
    nombre_actividad = serializers.CharField()
    comentarios = serializers.CharField(allow_blank=True)
    fecha = serializers.CharField()
    total_horas_decimal = serializers.DecimalField(max_digits=10, decimal_places=2)
    tipo_tiempo = serializers.CharField()


#-- Proyectos tiempos---
class TbPrecioPuestoAnualSerializer(serializers.ModelSerializer):
    # incluir el puesto anidado para lectura
    from .serializers import TbPuestoSerializer as _TbPuestoSerializer  # evitar colisión si ya existe
    puesto = _TbPuestoSerializer(source='id_puesto', read_only=True)

    class Meta:
        model = TbPrecioPuestoAnual
        fields = [
            'id',               # id del registro de precio
            'id_puesto',        # FK numérico
            'puesto',           # objeto anidado (lectura)
            'int_anio',
            'dec_precio_unitario'
        ]


class TbPuestoTarifaMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = TbPrecioPuestoAnual
        fields = ['id', 'int_anio', 'dec_precio_unitario']

class TbPuestoConTarifasSerializer(serializers.ModelSerializer):
    area = TbAreaMiniSerializer(source='id_area', read_only=True)
    tarifas = TbPuestoTarifaMiniSerializer(source='precios_anuales', many=True, read_only=True)

    class Meta:
        model = TbPuesto
        fields = ['id_puesto', 'vc_puesto', 'vc_desc', 'chr_status', 'area', 'tarifas']

class TbProyectoPuestoAnioSerializer(serializers.ModelSerializer):
    # lectura: precio anidado (puesto + tarifa + año)
    precio_puesto = TbPrecioPuestoAnualSerializer(source='id_precioPA', read_only=True)
    # opcional: escritura anidada para crear/usar precio si haces POST de un solo registro
    precio_puesto_data = serializers.DictField(write_only=True, required=False)

    # año de solo lectura tomado del tabulador
    anio = serializers.IntegerField(source='id_precioPA.int_anio', read_only=True)

    tarifa_resuelta = serializers.ReadOnlyField()
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = TbProyectoPuestoAnio
        fields = [
            'id_proyecto',
            'id_precioPA',
            'precio_puesto',
            'precio_puesto_data',
            'int_numPuestos',           #  NUEVO (default 1)
            'dec_horas_estimadas',
            'dec_tarifa_hora_override',
            'tarifa_resuelta',
            'subtotal',
            'anio',
        ]

    # ---------------- helpers ----------------
    def _anio_from_context(self):
        anio = self.context.get('int_anio')
        if anio is None:
            return None
        try:
            return int(anio)
        except (TypeError, ValueError):
            return None

    def _resolve_or_create_precio(self, data):
        from .models import TbPrecioPuestoAnual, TbPuesto

        puesto_in = data.get('puesto_in')
        id_puesto = data.get('id_puesto')
        if puesto_in:
            puesto_obj = TbPuesto.objects.create(**puesto_in)
            id_puesto = puesto_obj.id_puesto
        if not id_puesto:
            raise serializers.ValidationError("precio_puesto_data requiere id_puesto o puesto_in.")

        anio_tab = data.get('int_anio', self._anio_from_context())
        if anio_tab is None:
            raise serializers.ValidationError(
                "Debes indicar el año (precio_puesto_data.int_anio) o enviarlo como ?int_anio=YYYY."
            )
        try:
            anio_tab = int(anio_tab)
        except (TypeError, ValueError):
            raise serializers.ValidationError("El año debe ser numérico (int_anio).")

        dec_precio_unitario = data.get('dec_precio_unitario')
        precio_row, created = TbPrecioPuestoAnual.objects.get_or_create(
            id_puesto_id=id_puesto,
            int_anio=anio_tab,
            defaults={'dec_precio_unitario': dec_precio_unitario} if dec_precio_unitario is not None else {}
        )
        if not created and dec_precio_unitario is not None:
            precio_row.dec_precio_unitario = dec_precio_unitario
            precio_row.save(update_fields=['dec_precio_unitario'])
        return precio_row

    # ---------------- validations ----------------
    def validate(self, attrs):
        if not attrs.get('id_precioPA') and not self.initial_data.get('precio_puesto_data'):
            raise serializers.ValidationError("Debes enviar id_precioPA o precio_puesto_data.")

        # Asegurar int_numPuestos >= 1 (por si el front manda 0 o negativo)
        num_puestos = attrs.get('int_numPuestos', 1)
        try:
            if int(num_puestos) < 1:
                raise serializers.ValidationError("int_numPuestos debe ser >= 1.")
        except (TypeError, ValueError):
            raise serializers.ValidationError("int_numPuestos debe ser un entero >= 1.")
        return attrs

    # ---------------- CRUD ----------------
    def create(self, validated_data):
        precio_data = validated_data.pop('precio_puesto_data', None)
        if precio_data:
            precio_row = self._resolve_or_create_precio(precio_data)
            ctx_anio = self._anio_from_context()
            if ctx_anio is not None and precio_row.int_anio != ctx_anio:
                raise serializers.ValidationError(
                    f"El año del tabulador ({precio_row.int_anio}) no coincide con ?int_anio={ctx_anio}."
                )
            validated_data['id_precioPA'] = precio_row

        # default de seguridad por si no vino
        if 'int_numPuestos' not in validated_data or validated_data['int_numPuestos'] in (None, ''):
            validated_data['int_numPuestos'] = 1

        return super().create(validated_data)

    def update(self, instance, validated_data):
        precio_data = validated_data.pop('precio_puesto_data', None)
        if precio_data:
            precio_row = self._resolve_or_create_precio(precio_data)
            ctx_anio = self._anio_from_context()
            if ctx_anio is not None and precio_row.int_anio != ctx_anio:
                raise serializers.ValidationError(
                    f"El año del tabulador ({precio_row.int_anio}) no coincide con ?int_anio={ctx_anio}."
                )
            validated_data['id_precioPA'] = precio_row

        if 'int_numPuestos' in validated_data:
            try:
                if int(validated_data['int_numPuestos']) < 1:
                    raise serializers.ValidationError("int_numPuestos debe ser >= 1.")
            except (TypeError, ValueError):
                raise serializers.ValidationError("int_numPuestos debe ser un entero >= 1.")

        return super().update(instance, validated_data)
