import jwt
import json
import requests
from jwt import algorithms
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.contrib.auth.models import User

class CognitoJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        # Esperamos que el Authorization header contenga 'Bearer <id_token>'
        token = auth_header.split(' ')[1]
        try:
            # Obtener las llaves públicas desde Cognito
            jwks_url = settings.COGNITO_JWKS_URL
            jwks_client = requests.get(jwks_url).json()
            headers = jwt.get_unverified_header(token)
            kid = headers['kid']
            public_key = next((key for key in jwks_client['keys'] if key['kid'] == kid), None)

            if public_key is None:
                raise AuthenticationFailed('Public key not found.')

            rsa_key = {
                'kty': public_key['kty'],
                'kid': public_key['kid'],
                'use': public_key['use'],
                'n': public_key['n'],
                'e': public_key['e'],
            }

            # Convertir rsa_key (diccionario) a cadena JSON
            rsa_key_json = json.dumps(rsa_key)

            # Usar la cadena JSON en lugar del diccionario
            key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key_json)

            # Verificar y decodificar el token ID
            decoded_token = jwt.decode(
                token,
                key=key,
                algorithms=['RS256'],
                options={"verify_aud": False},  # Omitir la verificación de 'aud'
                issuer=f'https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}'
            )

            # Extraer la información del usuario del id_token
            username = decoded_token.get('cognito:username', decoded_token.get('sub'))
            email = decoded_token.get('email')

            if not email:
                raise AuthenticationFailed('Email is required in the token.')

            # Buscar o crear el usuario en la base de datos de Django
            user, created = User.objects.get_or_create(username=username, defaults={'email': email})

            return (user, None)  # Retorna el usuario autenticado y las credenciales (None en este caso)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired.')
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(f'Invalid token: {str(e)}')

        return None