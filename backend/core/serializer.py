from rest_framework import serializers
from .models import Usuario,Especialidad,Materia,Material,ClaseApoyo,Ponderacion


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ('legajo','nombre','correo')

class EspecialidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidad
        fields = '__all__'

class MateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materia
        fields = '__all__'

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = '__all__'

class ClaseApoyoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaseApoyo
        fields = '__all__'

class PonderacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ponderacion
        fields = '__all__'

#Por ahora puse que serialice todos los campos, despues en el futuro vemos si necesitamos acotar lo que devuelva el JSON de cada Modelo
