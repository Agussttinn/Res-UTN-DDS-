"""Permisos por rol (Alumno / Tutor / Administrador, ver RNF03 del README)."""
from rest_framework.permissions import SAFE_METHODS, BasePermission

ALUMNO = 'alumno'
TUTOR = 'tutor'
ADMINISTRADOR = 'administrador'


def rol_de(request):
    """Rol del usuario logueado, o None si es anónimo."""
    return getattr(request.user, 'rol', None)


def es_administrador(request):
    return rol_de(request) == ADMINISTRADOR


class EsAdministrador(BasePermission):
    """Solo el administrador (lectura y escritura)."""
    message = 'Esta acción es solo para administradores.'

    def has_permission(self, request, view):
        return es_administrador(request)


def lectura_autenticada_escritura_para(*roles):
    """Cualquier usuario logueado puede LEER; solo los `roles` indicados pueden ESCRIBIR."""

    class LecturaAutenticadaEscrituraRestringida(BasePermission):
        message = 'No tenés permiso para modificar este recurso: se necesita rol ' + ' o '.join(roles) + '.'

        def has_permission(self, request, view):
            if request.method in SAFE_METHODS:
                return rol_de(request) is not None
            return rol_de(request) in roles

    return LecturaAutenticadaEscrituraRestringida


class EsDuenioOAdministrador(BasePermission):
    """Sobre un objeto concreto: solo su dueño o un administrador.

    La vista indica qué campo apunta al dueño con `campo_duenio` (ej. 'usuario' o 'tutor').
    """
    message = 'Solo el dueño o un administrador puede hacer esto.'

    def has_object_permission(self, request, view, obj):
        if es_administrador(request):
            return True
        return getattr(obj, f'{view.campo_duenio}_id') == request.user.pk


class PuedeVerUsuario(BasePermission):
    """Un usuario puede ver su propio perfil; el administrador ve y modifica a todos."""
    message = 'Solo podés ver tu propio perfil.'

    def has_permission(self, request, view):
        return rol_de(request) is not None

    def has_object_permission(self, request, view, obj):
        if es_administrador(request):
            return True
        return request.method in SAFE_METHODS and obj.pk == request.user.pk


class PuedeModificarMaterial(BasePermission):
    """El autor puede editar su material SOLO mientras está pendiente (si no, se saltearía
    la moderación cambiando el archivo después de que lo aprueben) y borrarlo cuando quiera.
    El administrador puede todo."""
    message = 'Un material ya validado solo lo puede modificar un administrador.'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or es_administrador(request):
            return True
        if obj.usuario_id != request.user.pk:
            self.message = 'Solo el autor o un administrador puede modificar este material.'
            return False
        if request.method == 'DELETE':
            return True
        return not obj.validacion
