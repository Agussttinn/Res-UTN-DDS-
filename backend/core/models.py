from django.db import models

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

class Especialidad(models.Model):
    nombre = models.CharField(max_length=100)
    def __str__(self):
        return self.nombre

class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    anio = models.IntegerField()
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT, related_name='materias')#aca va a buscar en la tabla Especialidad y va a traer el id de la especialidad que le corresponde a la materia. El related_name es para poder acceder a las materias desde la especialidad.
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
    valor = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.material} - {self.usuario}"