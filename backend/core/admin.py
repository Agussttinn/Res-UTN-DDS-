from django.contrib import admin

# Register your models here.
from .models import Usuario, Especialidad, Materia, Material, ClaseApoyo, Ponderacion

admin.site.register(Usuario)
admin.site.register(Especialidad)
admin.site.register(Materia)
admin.site.register(Material)
admin.site.register(ClaseApoyo)
admin.site.register(Ponderacion)