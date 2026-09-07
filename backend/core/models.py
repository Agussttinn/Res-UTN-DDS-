from django.db import models

# Create your models here.
class Usuario(models.Model):
    legajo = models.CharField(max_length=20, primary_key=True) #El legajo debería ser único para cada usuario
    nombre = models.CharField(max_length=100)
    correo = models.EmailField(unique=True) # valida formato y evita duplicados.
    contraseña = models.CharField(max_length=255)
    rol = models.CharField(max_length=20, choices=[
        ('alumno', 'Alumno'), 
        ('tutor', 'Tutor'), 
        ('administrador', 'Administrador'),
    ])# aca cuando haga usuario.rol deberia devolver el valor de la tupla, no el string que se le asigna al campo rol
    def __str__(self):
        return self.nombre

class Especialidad(models.Model):
    nombre = models.CharField(max_length=100)
    def __str__(self):
        return self.nombre

class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    anio=models.IntegerField()
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT, related_name='materias')#aca va a buscar en la tabla Especialidad y va a traer el id de la especialidad que le corresponde a la materia. El related_name es para poder acceder a las materias desde la especialidad.
    def __str__(self):
        return self.nombre