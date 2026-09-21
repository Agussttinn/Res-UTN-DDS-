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
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='clases_apoyo')
    tutor = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='clases_apoyo')
    horario = models.CharField(max_length=20)
    aula = models.CharField(max_length=20)
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