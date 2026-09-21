import re

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import sysacad_client, sysacad_sync
from .auth import crear_token
from .models import Usuario, Especialidad, Materia, Material, ClaseApoyo, Ponderacion
from .permissions import (
    ADMINISTRADOR,
    TUTOR,
    EsAdministrador,
    EsDuenioOAdministrador,
    PuedeModificarMaterial,
    PuedeVerUsuario,
    es_administrador,
    lectura_autenticada_escritura_para,
)
from .serializer import (
    UsuarioSerializer,
    EspecialidadSerializer,
    MateriaSerializer,
    MaterialSerializer,
    ClaseApoyoSerializer,
    PonderacionSerializer,
)

# Cualquier usuario logueado LEE; solo el rol indicado ESCRIBE.
SoloAdministradorEscribe = lectura_autenticada_escritura_para(ADMINISTRADOR)
TutorOAdministradorEscriben = lectura_autenticada_escritura_para(TUTOR, ADMINISTRADOR)

# El legajo va dentro de una URL hacia SySACAD: solo letras y números, sin "/" ni "..".
LEGAJO_VALIDO = re.compile(r'^[A-Za-z0-9]{1,20}$')


# ---------- helpers ----------

def _datos(request):
    """request.data como dict (si mandan un JSON que no es un objeto, por ejemplo una lista, queda vacío)."""
    return request.data if isinstance(request.data, dict) else {}


def _id_numerico(request, parametro):
    """Lee un filtro numérico de la URL (?materia=3). Si no viene devuelve None; si no es un número, 400."""
    valor = request.query_params.get(parametro)
    if valor is None:
        return None
    if not valor.isdigit():
        raise ValidationError({parametro: 'Tiene que ser un id numérico.'})
    return int(valor)


def materiales_visibles_para(usuario):
    """Materiales que puede ver `usuario` (RF03/RF08): los validados, más los suyos propios
    (para que el autor vea los que todavía están pendientes). El administrador ve todos.

    Trae en la misma consulta la materia, el autor y el promedio de estrellas, para no hacer
    varias consultas extra por cada material de la lista."""
    materiales = Material.objects.select_related('materia__especialidad', 'usuario').annotate(
        promedio_anotado=Avg('ponderaciones__valor'),
        cantidad_anotada=Count('ponderaciones'),
    )
    if usuario.rol != ADMINISTRADOR:
        materiales = materiales.filter(Q(validacion=True) | Q(usuario=usuario))
    return materiales


class ProtegidoAlBorrarMixin:
    """Si el objeto tiene otros registros que dependen de él (protegidos con on_delete=PROTECT),
    responde 409 con un mensaje claro en vez de un error 500."""

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"error": "No se puede eliminar: hay otros registros (materias, materiales, clases o ponderaciones) que dependen de este."},
                status=status.HTTP_409_CONFLICT,
            )


# ---------- usuarios ----------

class UsuarioListCreate(generics.ListCreateAPIView):
    """Listar y dar de alta usuarios a mano (por ejemplo tutores y administradores): solo administradores.
    Los alumnos se dan de alta solos con POST /api/registro/."""
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [EsAdministrador]


class UsuarioDetail(ProtegidoAlBorrarMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [PuedeVerUsuario]


# ---------- especialidades y materias ----------

class EspecialidadListCreate(generics.ListCreateAPIView):
    queryset = Especialidad.objects.all()
    serializer_class = EspecialidadSerializer
    permission_classes = [SoloAdministradorEscribe]


class EspecialidadDetail(ProtegidoAlBorrarMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Especialidad.objects.all()
    serializer_class = EspecialidadSerializer
    permission_classes = [SoloAdministradorEscribe]


class MateriaListCreate(generics.ListCreateAPIView):
    queryset = Materia.objects.select_related('especialidad')
    serializer_class = MateriaSerializer
    permission_classes = [SoloAdministradorEscribe]


class MateriaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Materia.objects.select_related('especialidad')
    serializer_class = MateriaSerializer
    permission_classes = [SoloAdministradorEscribe]


class MateriaSincronizar(APIView):
    """Trae el plan de estudio de una carrera desde SySACAD y actualiza
    Especialidad/Materia locales. Devuelve las materias ya en el formato
    habitual de la API (MateriaSerializer), no el formato de SySACAD."""
    permission_classes = [EsAdministrador]

    def post(self, request, carrera):
        try:
            materias = sysacad_sync.sync_materias(carrera.upper())
        except sysacad_client.PlanNoEncontrado:
            return Response(
                {"error": f'No existe un plan de estudio para la carrera "{carrera}" en SySACAD'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except sysacad_client.SysacadError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(MateriaSerializer(materias, many=True).data, status=status.HTTP_200_OK)


# ---------- materiales ----------

class MaterialListCreate(generics.ListCreateAPIView):
    """GET: materiales validados (más los propios pendientes). Filtro opcional: ?materia=<id>.
    POST: cualquier usuario logueado carga un material (multipart, con el archivo); queda PENDIENTE."""
    serializer_class = MaterialSerializer

    def get_queryset(self):
        materiales = materiales_visibles_para(self.request.user).order_by('-fecha_de_carga', '-id')
        materia_id = _id_numerico(self.request, 'materia')
        if materia_id is not None:
            materiales = materiales.filter(materia_id=materia_id)
        return materiales

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)  # el autor es quien está logueado


class MaterialDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated, PuedeModificarMaterial]

    def get_queryset(self):
        return materiales_visibles_para(self.request.user)


class MaterialPendientes(generics.ListAPIView):
    """Cola de moderación (CU11): materiales que todavía nadie validó, los más viejos primero."""
    serializer_class = MaterialSerializer
    permission_classes = [EsAdministrador]

    def get_queryset(self):
        return (
            materiales_visibles_para(self.request.user)
            .filter(validacion=False)
            .order_by('fecha_de_carga', 'id')
        )


class MaterialModerar(APIView):
    """Body: {"accion": "aprobar"} -> el material pasa a estar validado y visible para todos.
             {"accion": "rechazar"} -> el material y su archivo se eliminan."""
    permission_classes = [EsAdministrador]

    def post(self, request, pk):
        material = get_object_or_404(Material, pk=pk)
        accion = _datos(request).get('accion')

        if accion == 'aprobar':
            material.validacion = True
            material.save(update_fields=['validacion'])
            return Response(MaterialSerializer(material, context={'request': request}).data)

        if accion == 'rechazar':
            if material.archivo:
                material.archivo.delete(save=False)
            material.delete()
            return Response({"detalle": "Material rechazado y eliminado."})

        return Response(
            {"error": 'La acción tiene que ser "aprobar" o "rechazar".'},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ---------- clases de apoyo ----------

def _clases_apoyo_queryset(request):
    clases = ClaseApoyo.objects.select_related('materia__especialidad', 'tutor')
    materia_id = _id_numerico(request, 'materia')
    if materia_id is not None:
        clases = clases.filter(materia_id=materia_id)
    return clases


class ClaseApoyoListCreate(generics.ListCreateAPIView):
    """GET: cualquier usuario logueado (filtro opcional ?materia=<id>). POST: solo tutores y administradores."""
    serializer_class = ClaseApoyoSerializer
    permission_classes = [TutorOAdministradorEscriben]

    def get_queryset(self):
        return _clases_apoyo_queryset(self.request)


class ClaseApoyoDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ClaseApoyoSerializer
    permission_classes = [IsAuthenticated, TutorOAdministradorEscriben, EsDuenioOAdministrador]
    campo_duenio = 'tutor'  # solo el tutor a cargo de la clase (o un administrador) la modifica

    def get_queryset(self):
        return _clases_apoyo_queryset(self.request)


# ---------- ponderaciones (estrellas) ----------

def _ponderaciones_queryset(request):
    """Cada usuario ve solo sus propias ponderaciones (el administrador, todas).
    Filtro opcional: ?material=<id> para saber qué estrellas le puso el usuario a ese material."""
    ponderaciones = Ponderacion.objects.select_related(
        'material__materia__especialidad', 'material__usuario', 'usuario'
    )
    if not es_administrador(request):
        ponderaciones = ponderaciones.filter(usuario=request.user)
    material_id = _id_numerico(request, 'material')
    if material_id is not None:
        ponderaciones = ponderaciones.filter(material_id=material_id)
    return ponderaciones


class PonderacionListCreate(generics.ListCreateAPIView):
    serializer_class = PonderacionSerializer

    def get_queryset(self):
        return _ponderaciones_queryset(self.request)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)  # puntúa quien está logueado


class PonderacionDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PonderacionSerializer
    permission_classes = [IsAuthenticated, EsDuenioOAdministrador]
    campo_duenio = 'usuario'

    def get_queryset(self):
        return _ponderaciones_queryset(self.request)


# ---------- login y registro (públicos) ----------

class LoginAlumno(APIView):
    """POST {"legajo": "...", "contraseña": "..."} -> {"access": "<token>", "usuario": {...}}
    El token se manda después en cada request:  Authorization: Bearer <token>"""
    authentication_classes = []  # es público: un token viejo o inválido en el header no debe impedir loguearse
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        datos = _datos(request)
        legajo = datos.get('legajo')
        contrasena = datos.get('contraseña')

        if not legajo or not isinstance(contrasena, str) or not contrasena:
            return Response(
                {"error": "Faltan legajo o contraseña"},
                status=status.HTTP_400_BAD_REQUEST
            )

        usuario = Usuario.objects.filter(pk=str(legajo)).first()

        # Mismo mensaje si el legajo no existe o la contraseña está mal:
        # así no se puede averiguar qué legajos están registrados.
        if usuario is None or not check_password(contrasena, usuario.contraseña):
            return Response(
                {"error": "Legajo o contraseña incorrectos"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {"access": crear_token(usuario), "usuario": UsuarioSerializer(usuario).data},
            status=status.HTTP_200_OK
        )


class RegistroAlumno(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'registro'

    def post(self, request):
        datos = _datos(request)
        legajo = datos.get('legajo')
        contrasena = datos.get('contraseña')

        if not legajo or not isinstance(contrasena, str) or not contrasena:
            return Response(
                {"error": "Faltan legajo o contraseña"},
                status=status.HTTP_400_BAD_REQUEST
            )

        legajo = str(legajo)
        if not LEGAJO_VALIDO.match(legajo):
            return Response(
                {"error": "El legajo solo puede tener letras y números (hasta 20 caracteres)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. ¿Ya existe una cuenta con ese legajo en MI base?
        if Usuario.objects.filter(pk=legajo).exists():
            return Response(
                {"error": "Ya existe una cuenta con ese legajo"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. La contraseña tiene que cumplir las reglas de seguridad de Django (largo, no común, no solo números)
        try:
            validate_password(contrasena)
        except DjangoValidationError as exc:
            return Response({"error": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Consultar SysAcad para validar que sea un alumno real
        try:
            datos_alumno = sysacad_client.get_alumno(legajo)
        except sysacad_client.AlumnoNoEncontrado:
            return Response(
                {"error": "No existe ese legajo en SysAcad"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except sysacad_client.SysacadError:
            return Response(
                {"error": "No se pudo verificar el legajo con SySACAD. Intentá de nuevo en unos minutos."},
                status=status.HTTP_502_BAD_GATEWAY
            )

        nombre = datos_alumno.get('nombre')
        correo = datos_alumno.get('correo')
        if not nombre or not correo:
            return Response(
                {"error": "SySACAD devolvió datos incompletos para ese legajo."},
                status=status.HTTP_502_BAD_GATEWAY
            )

        if Usuario.objects.filter(correo=correo).exists():
            return Response(
                {"error": "Ese correo ya está asociado a otra cuenta"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Crear el Usuario en mi propia base
        try:
            with transaction.atomic():
                nuevo_usuario = Usuario.objects.create(
                    legajo=legajo,
                    nombre_y_apellido=nombre,
                    correo=correo,
                    contraseña=make_password(contrasena),
                    rol='alumno',
                )
        except IntegrityError:
            # Dos registros simultáneos con el mismo legajo/correo: gana el primero.
            return Response(
                {"error": "Ya existe una cuenta con ese legajo o correo"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"legajo": nuevo_usuario.legajo, "nombre_y_apellido": nuevo_usuario.nombre_y_apellido},
            status=status.HTTP_201_CREATED
        )
