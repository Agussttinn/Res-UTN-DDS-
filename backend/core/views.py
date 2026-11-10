import re

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core import signing
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, Q
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
from .models import Rol, EstadoMaterial, Alumno, Usuario, Especialidad, Materia, Material, ClaseApoyo, Ponderacion, Suscripcion, Notificacion
from .observador import EventoClase, SujetoClase
from .permissions import (
    ADMINISTRADOR,
    ALUMNO,
    TUTOR,
    EsAdministrador,
    EsDuenioOAdministrador,
    PuedeModificarMaterial,
    PuedeVerUsuario,
    es_administrador,
    lectura_autenticada_escritura_para,
    rol_de,
)
from .serializer import (
    UsuarioSerializer,
    RolSerializer,
    EspecialidadSerializer,
    MateriaSerializer,
    MaterialSerializer,
    ClaseApoyoSerializer,
    PonderacionSerializer,
    MensajeClaseSerializer,
    NotificacionSerializer,
)

ESTADOS_PUBLICOS = (EstadoMaterial.APROBADO, EstadoMaterial.ARCHIVADO)

# Cualquier usuario logueado LEE; solo el rol indicado ESCRIBE.
SoloAdministradorEscribe = lectura_autenticada_escritura_para(ADMINISTRADOR)
TutorOAdministradorEscriben = lectura_autenticada_escritura_para(TUTOR, ADMINISTRADOR)
SoloAlumnoEscribe = lectura_autenticada_escritura_para(ALUMNO)

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
    materiales = Material.objects.select_related('materia__especialidad', 'alumno__usuario__rol', 'estado')
    if usuario.rol.nombre != ADMINISTRADOR:
        materiales = materiales.filter(Q(estado__nombre__in=ESTADOS_PUBLICOS) | Q(alumno_id=usuario.pk))
    return materiales

def _eliminar_material_y_archivo(material):
    """Borra el material y también su archivo del disco (si no, quedaría un archivo huérfano en media/).
    Primero se borra el registro: si eso falla, el archivo sigue estando y no se pierde nada."""
    archivo = material.archivo
    material.delete()
    if archivo:
        archivo.delete(save=False)


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
    queryset = Usuario.objects.select_related('rol')
    serializer_class = UsuarioSerializer
    permission_classes = [EsAdministrador]


class UsuarioDetail(ProtegidoAlBorrarMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Usuario.objects.select_related('rol')
    serializer_class = UsuarioSerializer
    permission_classes = [PuedeVerUsuario]


class RolList(generics.ListAPIView):
    """Roles disponibles (alumno, tutor, administrador...). Solo lectura: se agregan como filas de la tabla roles."""
    queryset = Rol.objects.order_by('id')
    serializer_class = RolSerializer
    permission_classes = [EsAdministrador]


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
    """GET: materias de las carreras habilitadas (settings.CARRERAS_HABILITADAS), ordenadas por año y nombre.
    Filtros opcionales: ?especialidad=<id>, ?anio=<n>, ?electiva=true|false y ?buscar=<parte del nombre>.
    Se resuelven en la base local, no en SySACAD."""
    serializer_class = MateriaSerializer
    permission_classes = [SoloAdministradorEscribe]

    def get_queryset(self):
        materias = Materia.objects.select_related('especialidad').filter(
            especialidad__codigo_sysacad__in=settings.CARRERAS_HABILITADAS,
        ).order_by('anio', 'nombre')
        especialidad_id = _id_numerico(self.request, 'especialidad')
        if especialidad_id is not None:
            materias = materias.filter(especialidad_id=especialidad_id)
        anio = _id_numerico(self.request, 'anio')
        if anio is not None:
            materias = materias.filter(anio=anio)
        buscar = self.request.query_params.get('buscar', '').strip()
        if buscar:
            # Con la collation de MariaDB/MySQL (utf8mb4_general_ci) no distingue mayúsculas ni acentos.
            materias = materias.filter(nombre__icontains=buscar)
        electiva = self.request.query_params.get('electiva')
        if electiva is not None:
            if electiva not in ('true', 'false'):
                raise ValidationError({'electiva': 'Tiene que ser true o false.'})
            materias = materias.filter(electiva=electiva == 'true')
        return materias


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
        except sysacad_sync.CarreraNoHabilitada:
            return Response(
                {"error": f'Por ahora RES-UTN solo trabaja con: {", ".join(settings.CARRERAS_HABILITADAS)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
    POST: solo los alumnos cargan un material (multipart, con el archivo); queda PENDIENTE."""
    serializer_class = MaterialSerializer
    permission_classes = [SoloAlumnoEscribe]

    def get_queryset(self):
        materiales = materiales_visibles_para(self.request.user).order_by('-fecha_de_carga', '-id')
        materia_id = _id_numerico(self.request, 'materia')
        if materia_id is not None:
            materiales = materiales.filter(materia_id=materia_id)
        return materiales

    def perform_create(self, serializer):
        serializer.save(alumno=self.request.user.como_alumno())


class MaterialDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated, PuedeModificarMaterial]

    def get_queryset(self):
        return materiales_visibles_para(self.request.user)
    
    def perform_update(self, serializer):
        # Si el autor corrige un material RECHAZADO, vuelve a la cola de revisión (pendiente).
        reenvia = serializer.instance.estado.nombre == EstadoMaterial.RECHAZADO and not es_administrador(self.request)
        archivo_anterior = serializer.instance.archivo.name if serializer.instance.archivo else None
        material = serializer.save()
        if reenvia:
            material.estado = EstadoMaterial.objects.get(nombre=EstadoMaterial.PENDIENTE)
            material.motivo_rechazo = None
            material.save(update_fields=['estado', 'motivo_rechazo'])
        # Si reemplazó el archivo, el anterior ya no se usa: se borra del disco para no dejarlo huérfano.
        if archivo_anterior and archivo_anterior != (material.archivo.name if material.archivo else None):
            material.archivo.storage.delete(archivo_anterior)

    def perform_destroy(self, instance):
        _eliminar_material_y_archivo(instance)
    


class MaterialPendientes(generics.ListAPIView):
    """Cola de moderación (CU11): materiales que todavía nadie validó, los más viejos primero."""
    serializer_class = MaterialSerializer
    permission_classes = [EsAdministrador]

    def get_queryset(self):
        return (
            materiales_visibles_para(self.request.user)
            .filter(estado__nombre=EstadoMaterial.PENDIENTE)
            .order_by('fecha_de_carga', 'id')
        )


class MaterialModerar(APIView):
    """Body: {"accion": "aprobar"}  -> pendiente -> aprobado (visible para todos).
             {"accion": "rechazar", "motivo": "..."} -> pendiente o aprobado -> rechazado (solo lo ven el autor y los
                                                      administradores, que lo puede corregir y reenviar).
             {"accion": "desaprobar"} -> aprobado -> pendiente (por si se aprobó sin querer: deja de verse y vuelve a la cola).
             {"accion": "archivar"} -> aprobado -> archivado (solo lectura, ya no se puede puntuar)."""
    permission_classes = [EsAdministrador]

    # acción -> (estados desde los que se puede hacer, estado al que pasa)
    ACCIONES = {
        'aprobar': ((EstadoMaterial.PENDIENTE,), EstadoMaterial.APROBADO),
        'rechazar': ((EstadoMaterial.PENDIENTE, EstadoMaterial.APROBADO), EstadoMaterial.RECHAZADO),
        'desaprobar': ((EstadoMaterial.APROBADO,), EstadoMaterial.PENDIENTE),
        'archivar': ((EstadoMaterial.APROBADO,), EstadoMaterial.ARCHIVADO),
    }

    def post(self, request, pk):
        material = get_object_or_404(
            Material.objects.select_related('materia__especialidad', 'alumno__usuario__rol', 'estado'), pk=pk,
        )
        accion = _datos(request).get('accion')

        if accion not in self.ACCIONES:
            return Response(
                {"error": 'La acción tiene que ser "aprobar", "rechazar", "desaprobar" o "archivar".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        estados_permitidos, estado_nuevo = self.ACCIONES[accion]
        if material.estado.nombre not in estados_permitidos:
            return Response(
                {"error": f'No se puede {accion} un material que está {material.estado.nombre}.'},
                status=status.HTTP_409_CONFLICT,
            )

        material.estado = EstadoMaterial.objects.get(nombre=estado_nuevo)
        if accion == 'rechazar':
            material.motivo_rechazo = str(_datos(request).get('motivo') or '').strip() or None
        material.save(update_fields=['estado', 'motivo_rechazo'])
        self._avisar_al_autor(material, accion)
        return Response(MaterialSerializer(material, context={'request': request}).data)

    @staticmethod
    def _avisar_al_autor(material, accion):
        """Le llega al alumno autor una notificación (la campanita) cada vez que un administrador cambia
        el estado de su apunte."""
        if accion == 'rechazar':
            tipo = Notificacion.RECHAZO
            titulo = f'Rechazaron tu apunte "{material.titulo}"'
            texto = 'Podés corregirlo y reenviarlo desde Materiales: vuelve a quedar pendiente de revisión.'
            if material.motivo_rechazo:
                texto = f'Motivo: {material.motivo_rechazo}. ' + texto
        elif accion == 'aprobar':
            tipo = Notificacion.APROBACION
            titulo = f'Aprobaron tu apunte "{material.titulo}"'
            texto = 'Ya lo ven todos los alumnos en Materiales. ¡Gracias por compartirlo!'
        elif accion == 'desaprobar':
            tipo = Notificacion.REVISION
            titulo = f'Tu apunte "{material.titulo}" volvió a revisión'
            texto = 'Dejó de verse para los demás alumnos hasta que un administrador lo revise de nuevo.'
        else:  # archivar
            tipo = Notificacion.ARCHIVO
            titulo = f'Archivaron tu apunte "{material.titulo}"'
            texto = 'Sigue disponible para consulta, pero ya no se puede puntuar.'
        Notificacion.objects.create(alumno=material.alumno, tipo=tipo, titulo=titulo, texto=texto)


# ---------- clases de apoyo ----------

def _clases_apoyo_queryset(request):
    """Las clases con, en la misma consulta, cuántos suscritos tienen y si quien consulta es uno de ellos."""
    clases = ClaseApoyo.objects.select_related('materia__especialidad', 'tutor__usuario__rol').annotate(
        cantidad_suscritos=Count('suscripciones', distinct=True),
        suscrito=Exists(Suscripcion.objects.filter(clase=OuterRef('pk'), alumno_id=request.user.pk)),
    ).order_by('dia', 'hora_inicio', 'id')  # como un cronograma
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
    """Modificar o cancelar una clase avisa a sus suscritos (patrón Observer, ver observador.py)."""
    serializer_class = ClaseApoyoSerializer
    permission_classes = [IsAuthenticated, TutorOAdministradorEscriben, EsDuenioOAdministrador]
    campo_duenio = 'tutor'  # solo el tutor a cargo de la clase (o un administrador) la modifica

    def get_queryset(self):
        return _clases_apoyo_queryset(self.request)

    @transaction.atomic
    def perform_update(self, serializer):
        antes = serializer.instance
        valores_antes = {'Materia': antes.materia.nombre, 'Día y horario': antes.horario, 'Aula': antes.aula}
        clase = serializer.save()
        clase.refresh_from_db(fields=['materia'])
        valores_despues = {'Materia': clase.materia.nombre, 'Día y horario': clase.horario, 'Aula': clase.aula}
        cambios = [
            f'{campo}: {valor} → {valores_despues[campo]}'
            for campo, valor in valores_antes.items() if valor != valores_despues[campo]
        ]
        if cambios:
            SujetoClase(clase).notificar(EventoClase(
                tipo=Notificacion.MODIFICACION,
                clase=clase,
                titulo=f'Cambió la clase de apoyo de {clase.materia.nombre}',
                texto='. '.join(cambios) + '.',
            ))

    @transaction.atomic
    def perform_destroy(self, instance):
        # Primero se avisa (la notificación queda aunque la clase ya no exista) y después se borra.
        SujetoClase(instance).notificar(EventoClase(
            tipo=Notificacion.CANCELACION,
            clase=instance,
            titulo=f'Se canceló la clase de apoyo de {instance.materia.nombre}',
            texto=f'La clase del {instance.horario} en el aula {instance.aula} ya no se dicta.',
        ))
        instance.delete()


def _clase_de_la_url(request, pk):
    return get_object_or_404(_clases_apoyo_queryset(request), pk=pk)


def _puede_gestionar(request, clase):
    """El tutor a cargo de la clase o un administrador."""
    return es_administrador(request) or clase.tutor_id == request.user.pk


def _es_tutor_de(request, clase):
    """Solo el tutor a cargo de la clase (un administrador no habla en nombre del tutor)."""
    return rol_de(request) == TUTOR and clase.tutor_id == request.user.pk


class ClaseApoyoSuscripcion(APIView):
    """POST: el alumno logueado se suscribe a la clase (recibe avisos de cambios y mensajes).
    DELETE: deja de seguirla. Solo los alumnos se suscriben."""

    def post(self, request, pk):
        clase = _clase_de_la_url(request, pk)
        if rol_de(request) != ALUMNO:
            return Response({"error": "Solo los alumnos pueden suscribirse a una clase."}, status=status.HTTP_403_FORBIDDEN)
        nueva = SujetoClase(clase).suscribir(request.user.como_alumno())
        return self._estado(clase, status.HTTP_201_CREATED if nueva else status.HTTP_200_OK)

    def delete(self, request, pk):
        clase = _clase_de_la_url(request, pk)
        if rol_de(request) == ALUMNO:
            SujetoClase(clase).desuscribir(request.user.como_alumno())
        return self._estado(clase, status.HTTP_200_OK)

    def _estado(self, clase, codigo):
        return Response({
            "suscrito": clase.suscripciones.filter(alumno_id=self.request.user.pk).exists(),
            "cantidad_suscritos": clase.suscripciones.count(),
        }, status=codigo)


class ClaseApoyoMensajes(generics.ListCreateAPIView):
    """GET: mensajes de la clase, los más nuevos primero (sus suscritos, su tutor o un administrador).
    POST: el tutor de la clase manda un mensaje, que les llega a todos los suscritos."""
    serializer_class = MensajeClaseSerializer

    def get_clase(self):
        if not hasattr(self, '_clase'):
            self._clase = _clase_de_la_url(self.request, self.kwargs['pk'])
        return self._clase

    def get_queryset(self):
        clase = self.get_clase()
        if not (_puede_gestionar(self.request, clase) or clase.suscrito):
            self.permission_denied(self.request, message='Para ver los mensajes tenés que estar suscrito a la clase.')
        return clase.mensajes.select_related('tutor__usuario__rol')

    @transaction.atomic
    def perform_create(self, serializer):
        clase = self.get_clase()
        if not _es_tutor_de(self.request, clase):
            self.permission_denied(self.request, message='Solo el tutor de la clase puede enviar mensajes.')
        mensaje = serializer.save(clase=clase, tutor=clase.tutor)
        SujetoClase(clase).notificar(EventoClase(
            tipo=Notificacion.MENSAJE,
            clase=clase,
            titulo=f'Mensaje de {clase.tutor.usuario.nombre_y_apellido} ({clase.materia.nombre})',
            texto=mensaje.texto,
        ))


# ---------- notificaciones ----------

class NotificacionList(generics.ListAPIView):
    """Las últimas 50 notificaciones del usuario logueado, las más nuevas primero."""
    serializer_class = NotificacionSerializer

    def get_queryset(self):
        return Notificacion.objects.filter(alumno_id=self.request.user.pk)[:50]


class NotificacionesMarcarLeidas(APIView):
    """Marca como leídas todas las notificaciones del usuario logueado."""

    def post(self, request):
        marcadas = Notificacion.objects.filter(alumno_id=request.user.pk, leida=False).update(leida=True)
        return Response({"marcadas": marcadas})


# ---------- ponderaciones (estrellas) ----------

def _ponderaciones_queryset(request):
    """Cada usuario ve solo sus propias ponderaciones (el administrador, todas).
    Filtro opcional: ?material=<id> para saber qué estrellas le puso el usuario a ese material."""
    ponderaciones = Ponderacion.objects.select_related(
        'material__materia__especialidad', 'material__alumno__usuario__rol', 'material__estado', 'alumno__usuario__rol'
    )
    if not es_administrador(request):
        ponderaciones = ponderaciones.filter(alumno_id=request.user.pk)
    material_id = _id_numerico(request, 'material')
    if material_id is not None:
        ponderaciones = ponderaciones.filter(material_id=material_id)
    return ponderaciones


class PonderacionListCreate(generics.ListCreateAPIView):
    """POST: solo los alumnos puntúan."""
    serializer_class = PonderacionSerializer
    permission_classes = [SoloAlumnoEscribe]

    def get_queryset(self):
        return _ponderaciones_queryset(self.request)

    def perform_create(self, serializer):
        serializer.save(alumno=self.request.user.como_alumno())  # puntúa quien está logueado


class PonderacionDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PonderacionSerializer
    permission_classes = [IsAuthenticated, EsDuenioOAdministrador]
    campo_duenio = 'alumno'

    def get_queryset(self):
        return _ponderaciones_queryset(self.request)

    def perform_destroy(self, instance):
        material = instance.material
        instance.delete()
        material.recalcular_ponderacion()


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

        usuario = Usuario.objects.select_related('rol').filter(pk=str(legajo)).first()

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
                    rol=Rol.objects.get(nombre=ALUMNO),
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


# ---------- recuperación de contraseña (pública) ----------

SAL_RECUPERACION = 'recuperar-contrasena'


def _sal_de(usuario):
    """La sal incluye el hash actual de la contraseña: apenas se cambia, el link usado deja de servir."""
    return f'{SAL_RECUPERACION}:{usuario.contraseña[-16:]}'


def crear_token_recuperacion(usuario):
    """Token 'legajo~firma'. El legajo va a la vista (solo sirve para buscar al usuario); lo que vale es la firma."""
    return f'{usuario.pk}~{signing.dumps(usuario.pk, salt=_sal_de(usuario))}'


def usuario_de_token_recuperacion(token):
    """Devuelve el Usuario dueño del token, o None si está vencido, alterado o ya se usó."""
    if not isinstance(token, str) or '~' not in token:
        return None
    legajo, firma = token.split('~', 1)
    usuario = Usuario.objects.filter(pk=legajo).first()
    if usuario is None:
        return None
    try:
        if signing.loads(firma, salt=_sal_de(usuario), max_age=settings.RECUPERACION_MINUTOS * 60) != usuario.pk:
            return None
    except signing.BadSignature:
        return None
    return usuario


class RecuperarContrasena(APIView):
    """POST {"legajo": "..."} -> manda un mail con un link para elegir una contraseña nueva.
    Responde siempre lo mismo, exista o no el legajo, para no revelar qué legajos están registrados."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'recuperacion'

    def post(self, request):
        legajo = _datos(request).get('legajo')
        if not legajo:
            return Response({"error": "Ingresá tu legajo"}, status=status.HTTP_400_BAD_REQUEST)

        usuario = Usuario.objects.filter(pk=str(legajo)).first()
        if usuario is not None:
            link = f"{settings.FRONTEND_URL}/restablecer?token={crear_token_recuperacion(usuario)}"
            send_mail(
                'RES-UTN: recuperación de contraseña',
                f'Hola {usuario.nombre_y_apellido},\n\n'
                f'Pediste restablecer tu contraseña. Entrá a este link para elegir una nueva '
                f'(vence en {settings.RECUPERACION_MINUTOS} minutos y sirve una sola vez):\n\n{link}\n\n'
                'Si no fuiste vos, ignorá este mensaje: tu contraseña sigue igual.',
                None,
                [usuario.correo],
            )
        return Response({"mensaje": "Si el legajo está registrado, te enviamos un mail con las instrucciones."})


class RestablecerContrasena(APIView):
    """POST {"token": "...", "contraseña": "..."} -> cambia la contraseña si el link es válido."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'recuperacion'

    def post(self, request):
        datos = _datos(request)
        contrasena = datos.get('contraseña')
        if not isinstance(contrasena, str) or not contrasena:
            return Response({"error": "Ingresá la contraseña nueva"}, status=status.HTTP_400_BAD_REQUEST)

        usuario = usuario_de_token_recuperacion(datos.get('token'))
        if usuario is None:
            return Response(
                {"error": "El link no es válido o venció. Pedí uno nuevo."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            validate_password(contrasena, user=None)
        except DjangoValidationError as exc:
            return Response({"error": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        usuario.contraseña = make_password(contrasena)
        usuario.save(update_fields=['contraseña'])
        return Response({"mensaje": "Contraseña actualizada. Ya podés iniciar sesión."})
