from django.utils.deprecation import MiddlewareMixin
from django.utils.module_loading import import_string

class SyncCognitoGroupsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            # Importar el modelo Group de Django
            Group = import_string('django.contrib.auth.models.Group')
            
            # Verificar que el usuario tenga un JWT con la claim `cognito:groups`
            jwt_payload = getattr(request, 'auth', None)
            if jwt_payload:
                cognito_groups = jwt_payload.get('cognito:groups', [])
                
                # Asignar al grupo de Django correspondiente
                if 'us-east-1_xxxxxx' in cognito_groups:
                    group, created = Group.objects.get_or_create(name='GoogleUsers')
                    if not request.user.groups.filter(name='GoogleUsers').exists():
                        request.user.groups.add(group)
