from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .archivos import ruta_material, validar_extension, validar_tamano

# Create your models here.
class Usuario(models.Model):
    legajo = models.CharField(max_length=20, primary_key=True) #El legajo debería ser único para cada usuario
    nombre_y_apellido = models.CharField(max_length=100)
    correo = models.EmailField(unique=True) # valida formato y evita duplicados.
    contraseña = models.CharField(max_length=255)
    rol = models.CharField(max_length=20, choices=[
        ('alumno', 'Alumno'), 
        ('tutor', 'Tutor'), 
        ('administrador', 'Administrador'),
    ])# aca cuando haga usuario.rol deberia devolver el valor de la tupla, no el string que se le asigna al campo rol
    def __str__(self):
        return self.nombre_y_apellido

    # DRF necesita estas dos propiedades para tratar a un Usuario (que no hereda del User de Django)
    # como "usuario logueado" cuando llega un token válido.
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

class Especialidad(models.Model):
    nombre = models.CharField(max_length=100)
    # Código de carrera en SySACAD (ej. "ISI", "QUI"), usado para sincronizar el plan de estudio. Null si la especialidad no viene de SySACAD.
    codigo_sysacad = models.CharField(max_length=10, unique=True, null=True, blank=True)
    def __str__(self):
        return self.nombre

class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    anio = models.IntegerField()
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT, related_name='materias')#aca va a buscar en la tabla Especialidad y va a traer el id de la especialidad que le corresponde a la materia. El related_name es para poder acceder a las materias desde la especialidad.
    # idMateria en SySACAD (ej. "QUI-2023-301"), usado para sincronizar y para consultar el estado de un alumno en esta materia. Null si la materia no viene de SySACAD.
    id_sysacad = models.CharField(max_length=30, unique=True, null=True, blank=True)
    # Electiva del plan de estudio. `anio` es igual el nivel desde el que se puede cursar.
    electiva = models.BooleanField(default=False)
    def __str__(self):
        return self.nombre


class Material(models.Model): 
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='materiales') 
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='materiales')
    titulo = models.CharField(max_length=100)
    fecha_de_carga = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=20, choices=[
            ('resumen', 'Resumen'), 
            ('parcial', 'Parcial'), 
            ('final', 'Final'),
        ])
    validacion = models.BooleanField(default=False)
    comentario = models.TextField(blank=True, null=True)
    # El apunte en sí. Nullable en la base solo para no romper los materiales cargados antes de que
    # existiera este campo; al crear uno nuevo por la API, el serializer lo exige.
    archivo = models.FileField(
        upload_to=ruta_material, null=True, blank=True,
        validators=[validar_extension, validar_tamano],
    )
    def __str__(self):
        return self.titulo

class ClaseApoyo(models.Model):
    # Día de la semana con la numeración ISO (1 = lunes), así el cronograma se ordena solo por día y hora.
    DIAS = [
        (1, 'Lunes'),
        (2, 'Martes'),
        (3, 'Miércoles'),
        (4, 'Jueves'),
        (5, 'Viernes'),
        (6, 'Sábado'),
    ]

    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='clases_apoyo')
    tutor = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='clases_apoyo')
    # Día y horas pueden ser null solo en clases viejas cuyo horario (antes texto libre) no se pudo interpretar
    # al migrar: quedan "a confirmar" hasta que el tutor las complete. La API exige los tres.
    dia = models.PositiveSmallIntegerField(choices=DIAS, null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    aula = models.CharField(max_length=20)

    class Meta:
        ordering = ['dia', 'hora_inicio', 'id']

    @property
    def horario(self):
        """Ej: "lunes de 14:00 a 16:00", o "a confirmar" si falta algún dato."""
        if self.dia is None or self.hora_inicio is None or self.hora_fin is None:
            return 'a confirmar'
        return f"{self.get_dia_display().lower()} de {self.hora_inicio:%H:%M} a {self.hora_fin:%H:%M}"

    def __str__(self):
        return f"{self.materia} - {self.horario}"

class Ponderacion(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='ponderaciones')
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='ponderaciones')
    valor = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])  # estrellas de 1 a 5
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        # un usuario solo puede tener una ponderación por material (si vota de nuevo, se actualiza la anterior)
        constraints = [
            models.UniqueConstraint(fields=['material', 'usuario'], name='ponderacion_unica_por_usuario_y_material'),
        ]

    def __str__(self):
        return f"{self.material} - {self.usuario}"

class Suscripcion(models.Model):
    """Un alumno que sigue una clase de apoyo para enterarse de sus cambios y mensajes.
    En el patrón Observer es un observador registrado en esa clase (ver observador.py)."""
    clase = models.ForeignKey(ClaseApoyo, on_delete=models.CASCADE, related_name='suscripciones')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='suscripciones')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['clase', 'usuario'], name='suscripcion_unica_por_usuario_y_clase'),
        ]

    def __str__(self):
        return f"{self.usuario} sigue {self.clase}"


class MensajeClase(models.Model):
    """Mensaje que el tutor de una clase (o un administrador) les manda a sus suscritos."""
    clase = models.ForeignKey(ClaseApoyo, on_delete=models.CASCADE, related_name='mensajes')
    autor = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='mensajes_de_clases')
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"{self.clase}: {self.texto[:30]}"


class Notificacion(models.Model):
    """Aviso que recibe un usuario en la app (la campanita). Lo genera el patrón Observer."""
    MODIFICACION = 'modificacion'
    CANCELACION = 'cancelacion'
    MENSAJE = 'mensaje'

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones')
    # Si la clase se cancela (se borra), el aviso queda igual: por eso SET_NULL y no CASCADE.
    clase = models.ForeignKey(ClaseApoyo, on_delete=models.SET_NULL, null=True, blank=True, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=[
        (MODIFICACION, 'Modificación'),
        (CANCELACION, 'Cancelación'),
        (MENSAJE, 'Mensaje'),
    ])
    titulo = models.CharField(max_length=150)
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"{self.usuario}: {self.titulo}"
