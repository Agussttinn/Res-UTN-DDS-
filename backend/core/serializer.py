from rest_framework import serializers
from .models import Usuario,Especialidad,Materia,Material,ClaseApoyo,Ponderacion


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ('legajo','nombre_y_apellido','correo','rol')

class EspecialidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidad
        fields = ('id','nombre')

class MateriaSerializer(serializers.ModelSerializer):
    especialidad = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        fields = ('id','nombre','anio','especialidad')


    def get_especialidad(self, obj):
        especialidad = obj.especialidad
        return EspecialidadSerializer(especialidad).data

        
        

class MaterialSerializer(serializers.ModelSerializer):
    materia_id = serializers.IntegerField(write_only=True)
    usuario_id = serializers.CharField(write_only=True)
    materia = serializers.SerializerMethodField()
    usuario = serializers.SerializerMethodField()


    class Meta:
        model = Material
        fields = ('id','materia','usuario','titulo','fecha_de_carga','tipo','validacion','comentario','materia_id','usuario_id')
        #agregue materia_id y usuario_id porque como se puede publicar material, significa que va a haber un metodo POST que recibe un JSON con los datos del material, y en ese JSON no se puede enviar el objeto completo de materia y usuario, sino que se envia el id de la materia y el id del usuario. Entonces para poder serializar eso, agregue esos campos.

    #Para el POST
    def create(self, validated_data):
        materia_id = validated_data.pop('materia_id')
        usuario_id = validated_data.pop('usuario_id')

        material = Material.objects.create(
            materia_id = materia_id,
            usuario_id = usuario_id,
            **validated_data
        )

        return material

    def update(self, instance, validated_data):

        materia_id = validated_data.pop('materia_id', None)
        usuario_id = validated_data.pop('usuario_id', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if materia_id is not None:
            instance.materia_id = materia_id
        if usuario_id is not None:
            instance.usuario_id = usuario_id

        instance.save()
        return instance

    #Para el GET
    def get_materia(self, obj):
        materia = obj.materia
        return MateriaSerializer(materia).data
    
    def get_usuario(self, obj):
        usuario = obj.usuario
        return UsuarioSerializer(usuario).data

class ClaseApoyoSerializer(serializers.ModelSerializer):
    materia_id = serializers.IntegerField(write_only=True)
    tutor_id = serializers.CharField(write_only=True)
    materia = serializers.SerializerMethodField()
    tutor = serializers.SerializerMethodField()

    class Meta:
        model = ClaseApoyo
        fields = ('id','materia','tutor','horario','aula','materia_id','tutor_id')

    #Para el POST
    def create(self, validated_data):
        materia_id = validated_data.pop('materia_id')
        tutor_id = validated_data.pop('tutor_id')

        clase_apoyo = ClaseApoyo.objects.create(
            materia_id = materia_id,
            tutor_id = tutor_id,
            **validated_data
        )

        return clase_apoyo

    def update(self, instance, validated_data):

        materia_id = validated_data.pop('materia_id', None)
        tutor_id = validated_data.pop('tutor_id', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if materia_id is not None:
            instance.materia_id = materia_id
        if tutor_id is not None:
            instance.tutor_id = tutor_id

        instance.save()
        return instance


    #Para el GET
    def get_materia(self, obj):
        materia = obj.materia
        return MateriaSerializer(materia).data

    def get_tutor(self, obj):
        tutor = obj.tutor
        return UsuarioSerializer(tutor).data
    

class PonderacionSerializer(serializers.ModelSerializer):
    material_id = serializers.IntegerField(write_only=True)
    usuario_id = serializers.CharField(write_only=True)
    material = serializers.SerializerMethodField()
    usuario = serializers.SerializerMethodField()

    class Meta:
        model = Ponderacion
        fields = ('material','usuario','valor','fecha','material_id','usuario_id')
        #Una ponderacion no tiene sentido que tenga un id, por eso la API no lo va a devolver en el JSON
    
    #Para el POST
    def create(self, validated_data):
        material_id = validated_data.pop('material_id')
        usuario_id = validated_data.pop('usuario_id')

        ponderacion = Ponderacion.objects.create(
            material_id = material_id,
            usuario_id = usuario_id,
            **validated_data
        )

        return ponderacion

    def update(self, instance, validated_data):

        material_id = validated_data.pop('material_id', None)
        usuario_id = validated_data.pop('usuario_id', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if material_id is not None:
            instance.material_id = material_id
        if usuario_id is not None:
            instance.usuario_id = usuario_id

        instance.save()
        return instance

    #Para el GET
    def get_material(self, obj):
        material = obj.material
        return MaterialSerializer(material).data

    def get_usuario(self, obj):
        usuario = obj.usuario
        return UsuarioSerializer(usuario).data
