from django.contrib import admin
from django.contrib.auth.hashers import identify_hasher, make_password

# Register your models here.
from .models import Usuario, Especialidad, Materia, Material, ClaseApoyo, Ponderacion


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('legajo', 'nombre_y_apellido', 'correo', 'rol')

    def save_model(self, request, obj, form, change):
        # La contraseña se guarda hasheada (como en el registro y el login por API). Este formulario la
        # muestra como texto: si lo que hay escrito no es un hash, es una contraseña nueva y se hashea acá.
        # Sirve para dar de alta a mano al primer administrador o cambiarle la clave a alguien.
        try:
            identify_hasher(obj.contraseña)
        except ValueError:
            obj.contraseña = make_password(obj.contraseña)
        super().save_model(request, obj, form, change)


admin.site.register(Especialidad)
admin.site.register(Materia)
admin.site.register(Material)
admin.site.register(ClaseApoyo)
admin.site.register(Ponderacion)
