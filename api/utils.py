# utils.py
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import transaction
import base64
from django.core.files.base import ContentFile

MAX_IMAGE_SIZE_KB = 256  # Límite de tamaño en KB

def decode_base64_image(base64_string):
    try:
        # Separa el formato del contenido base64
        format, imgstr = base64_string.split(';base64,')
        ext = format.split('/')[-1]
        img_data = base64.b64decode(imgstr)

        # Calcula el tamaño en KB
        image_size_kb = len(img_data) / 1024

        # Verifica el tamaño máximo permitido
        if image_size_kb > MAX_IMAGE_SIZE_KB:
            return None, image_size_kb

        # Crea un archivo en memoria con los datos binarios
        image = ContentFile(img_data, name=f'image.{ext}')
        return image, image_size_kb
    except Exception as e:
        return None, str(e)


def promover_colaborador(colaborador, username, password=None, grupo_ids=None):
    """
    Promueve un colaborador a usuario del sistema.
    - Crea un User con los datos del colaborador.
    - No requiere contraseña si se usa login externo (como Cognito).
    - Asocia el usuario al colaborador y asigna grupos si se proporcionan.
    """

    if colaborador.user:
        raise ValidationError("Este colaborador ya tiene un usuario asociado.")
    
    if User.objects.filter(username=username).exists():
        raise ValidationError("El username ya está en uso.")

    with transaction.atomic():
        user = User.objects.create(
            username=username,
            email=colaborador.email or '',
            first_name=colaborador.first_name or '',
            last_name=colaborador.last_name or ''
        )

        if password:
            user.password = make_password(password)
            user.save(update_fields=['password'])

        if grupo_ids:
            user.groups.set(grupo_ids)

        colaborador.user = user
        colaborador.save(update_fields=['user'])

    return user