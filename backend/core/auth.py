"""Autenticación por token JWT para el modelo Usuario propio de RES-UTN.

Flujo: el usuario hace POST /api/login/ con legajo + contraseña y recibe un token firmado.
Después manda ese token en cada request:  Authorization: Bearer <token>
"""
import datetime

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

from .models import Usuario

ALGORITMO = 'HS256'


def crear_token(usuario: Usuario) -> str:
    """Genera un token firmado con la SECRET_KEY que identifica al usuario por su legajo."""
    ahora = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        'sub': usuario.legajo,
        'iat': ahora,
        'exp': ahora + datetime.timedelta(hours=settings.JWT_EXPIRACION_HORAS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITMO)


class JWTAuthentication(authentication.BaseAuthentication):
    """Lee el header `Authorization: Bearer <token>` y devuelve el Usuario dueño del token.

    El rol NO se lee del token sino de la base en cada request: si a alguien le cambian
    el rol (o lo borran), el cambio se aplica al instante y no cuando venza el token.
    """
    keyword = 'Bearer'

    def authenticate(self, request):
        partes = authentication.get_authorization_header(request).split()
        if not partes or partes[0].lower() != self.keyword.lower().encode():
            return None  # sin token: queda como anónimo (las vistas protegidas responden 401)
        if len(partes) != 2:
            raise exceptions.AuthenticationFailed('Encabezado Authorization inválido.')

        try:
            payload = jwt.decode(partes[1].decode(), settings.SECRET_KEY, algorithms=[ALGORITMO])
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('El token expiró, iniciá sesión de nuevo.')
        except (jwt.InvalidTokenError, UnicodeDecodeError):
            raise exceptions.AuthenticationFailed('Token inválido.')

        try:
            usuario = Usuario.objects.get(pk=payload['sub'])
        except (KeyError, Usuario.DoesNotExist):
            raise exceptions.AuthenticationFailed('El usuario de este token ya no existe.')
        return (usuario, payload)

    def authenticate_header(self, request):
        # Hace que DRF responda 401 (y no 403) cuando falta o falla el token.
        return self.keyword
