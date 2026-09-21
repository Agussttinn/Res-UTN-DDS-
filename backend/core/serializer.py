from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.db.models import Avg
from rest_framework import serializers

from .models import Usuario,Especialidad,Materia,Material,ClaseApoyo,Ponderacion
from .permissions import TUTOR


class UsuarioSerializer(serializers.ModelSerializer):
    # Solo se escribe (alta/cambio de clave por un administrador), nunca se devuelve en el JSON.
    # Se guarda hasheada, jamás en texto plano.
    contraseña = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Usuario
        fields = ('legajo','nombre_y_apellido','correo','rol','contraseña')

    def validate_contraseña(self, value):
        validate_password(value)  # largo mínimo, no demasiado común, no solo números
        return value

    def validate(self, attrs):
        if self.instance is None and 'contraseña' not in attrs:
            raise serializers.ValidationError({'contraseña': 'Este campo es obligatorio.'})
        return attrs

    def create(self, validated_data):
        validated_data['contraseña'] = make_password(validated_data['contraseña'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('legajo', None)  # el legajo es la clave primaria: no se cambia
        if 'contraseña' in validated_data:
            validated_data['contraseña'] = make_password(validated_data['contraseña'])
        return super().update(instance, validated_data)


class UsuarioPublicoSerializer(serializers.ModelSerializer):
    """Lo mínimo de un usuario para mostrarlo dentro de otros recursos (autor de un material,
    tutor de una clase). No incluye el correo: los demás usuarios no tienen por qué verlo."""
    class Meta:
        model = Usuario
        fields = ('legajo','nombre_y_apellido','rol')


class EspecialidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidad
        fields = ('id','nombre')

class MateriaSerializer(serializers.ModelSerializer):
    especialidad_id = serializers.IntegerField(write_only=True)
    especialidad = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        fields = ('id','nombre','anio','especialidad','especialidad_id')

    def validate_especialidad_id(self, value):
        if not Especialidad.objects.filter(pk=value).exists():
            raise serializers.ValidationError("No existe una especialidad con ese id.")
        return value

    #Para el POST
    def create(self, validated_data):
        especialidad_id = validated_data.pop('especialidad_id')
        return Materia.objects.create(especialidad_id=especialidad_id, **validated_data)

    def update(self, instance, validated_data):
        especialidad_id = validated_data.pop('especialidad_id', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if especialidad_id is not None:
            instance.especialidad_id = especialidad_id

        instance.save()
        return instance

    #Para el GET
    def get_especialidad(self, obj):
        especialidad = obj.especialidad
        return EspecialidadSerializer(especialidad).data


class MaterialSerializer(serializers.ModelSerializer):
    materia_id = serializers.IntegerField(write_only=True)
    materia = serializers.SerializerMethodField()
    usuario = serializers.SerializerMethodField()
    promedio_ponderacion = serializers.SerializerMethodField()
    cantidad_ponderaciones = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = ('id','materia','usuario','titulo','fecha_de_carga','tipo','validacion','comentario','archivo','promedio_ponderacion','cantidad_ponderaciones','materia_id')
        # validacion NO se puede escribir desde afuera: un material nace pendiente y solo un
        # administrador lo aprueba (POST /materiales/<id>/moderar/). Si no, cada alumno se auto-validaría.
        read_only_fields = ('validacion',)
        # El autor (usuario) tampoco se manda en el JSON: sale del token del que está logueado
        # (la vista lo pasa con serializer.save(usuario=request.user)), así nadie sube material a nombre de otro.

    def validate_materia_id(self, value):
        if not Materia.objects.filter(pk=value).exists():
            raise serializers.ValidationError("No existe una materia con ese id.")
        return value

    def validate(self, attrs):
        # Al crear, el archivo es obligatorio (a nivel base es opcional solo por los materiales viejos).
        if self.instance is None and not attrs.get('archivo'):
            raise serializers.ValidationError({'archivo': 'Tenés que adjuntar el archivo.'})
        return attrs

    #Para el POST
    def create(self, validated_data):
        materia_id = validated_data.pop('materia_id')

        # validated_data ya trae 'usuario' (lo agrega la vista con serializer.save(usuario=...))
        material = Material.objects.create(
            materia_id = materia_id,
            **validated_data
        )

        return material

    def update(self, instance, validated_data):

        materia_id = validated_data.pop('materia_id', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if materia_id is not None:
            instance.materia_id = materia_id

        instance.save()
        return instance

    #Para el GET
    def get_materia(self, obj):
        materia = obj.materia
        return MateriaSerializer(materia).data

    def get_usuario(self, obj):
        usuario = obj.usuario
        return UsuarioPublicoSerializer(usuario).data

    # Ponderación del material = promedio de las estrellas (1 a 5) que le pusieron los usuarios.
    # Si todavía nadie lo puntuó, el promedio es None (null en el JSON) y la cantidad es 0.
    # Las vistas de lista traen estos dos números ya calculados en la misma consulta (annotate);
    # si el objeto no los trae (por ejemplo, recién creado), se calculan acá.
    def get_promedio_ponderacion(self, obj):
        if hasattr(obj, 'promedio_anotado'):
            promedio = obj.promedio_anotado
        else:
            promedio = obj.ponderaciones.aggregate(promedio=Avg('valor'))['promedio']
        return round(promedio, 1) if promedio is not None else None

    def get_cantidad_ponderaciones(self, obj):
        if hasattr(obj, 'cantidad_anotada'):
            return obj.cantidad_anotada
        return obj.ponderaciones.count()

class ClaseApoyoSerializer(serializers.ModelSerializer):
    materia_id = serializers.IntegerField(write_only=True)
    # Opcional: si quien crea la clase es un tutor, el tutor es él mismo (sale del token).
    # Solo un administrador necesita indicar de qué tutor es la clase.
    tutor_id = serializers.CharField(write_only=True, required=False)
    materia = serializers.SerializerMethodField()
    tutor = serializers.SerializerMethodField()

    class Meta:
        model = ClaseApoyo
        fields = ('id','materia','tutor','horario','aula','materia_id','tutor_id')

    def validate_materia_id(self, value):
        if not Materia.objects.filter(pk=value).exists():
            raise serializers.ValidationError("No existe una materia con ese id.")
        return value

    def validate_tutor_id(self, value):
        if not Usuario.objects.filter(pk=value, rol=TUTOR).exists():
            raise serializers.ValidationError("No existe un tutor con ese legajo.")
        return value

    #Para el POST
    def create(self, validated_data):
        materia_id = validated_data.pop('materia_id')
        tutor_id = validated_data.pop('tutor_id', None)

        quien_crea = self.context['request'].user
        if quien_crea.rol == TUTOR:
            tutor_id = quien_crea.pk  # un tutor solo puede crear clases a su nombre
        if not tutor_id:
            raise serializers.ValidationError({'tutor_id': 'Indicá el legajo del tutor a cargo de la clase.'})

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
        # Cambiar de tutor una clase existente solo lo puede hacer un administrador.
        if tutor_id is not None and self.context['request'].user.rol != TUTOR:
            instance.tutor_id = tutor_id

        instance.save()
        return instance


    #Para el GET
    def get_materia(self, obj):
        materia = obj.materia
        return MateriaSerializer(materia).data

    def get_tutor(self, obj):
        tutor = obj.tutor
        return UsuarioPublicoSerializer(tutor).data


class PonderacionSerializer(serializers.ModelSerializer):
    material_id = serializers.IntegerField(write_only=True)
    material = serializers.SerializerMethodField()
    usuario = serializers.SerializerMethodField()

    class Meta:
        model = Ponderacion
        fields = ('material','usuario','valor','fecha','material_id')
        #Una ponderacion no tiene sentido que tenga un id, por eso la API no lo va a devolver en el JSON
        # El usuario que puntúa sale del token (la vista hace serializer.save(usuario=request.user)):
        # nadie puede puntuar a nombre de otro.

    def validate_material_id(self, value):
        if not Material.objects.filter(pk=value).exists():
            raise serializers.ValidationError("No existe un material con ese id.")
        return value

    def validate(self, attrs):
        # Reglas de negocio al puntuar (no aplican al editar las estrellas de un voto existente).
        if self.instance is None:
            material = Material.objects.get(pk=attrs['material_id'])
            if not material.validacion:
                raise serializers.ValidationError({'material_id': 'Solo se pueden puntuar materiales ya validados.'})
            if material.usuario_id == self.context['request'].user.pk:
                raise serializers.ValidationError({'material_id': 'No podés puntuar tu propio material.'})
        return attrs

    #Para el POST
    # Un usuario tiene una sola ponderación por material: si ya había votado, se actualiza
    # su valor (cambia sus estrellas); si no, se crea una nueva.
    def create(self, validated_data):
        material_id = validated_data.pop('material_id')
        usuario = validated_data.pop('usuario')  # lo agrega la vista con serializer.save(usuario=...)

        ponderacion, _ = Ponderacion.objects.update_or_create(
            material_id = material_id,
            usuario = usuario,
            defaults = validated_data,
        )

        return ponderacion

    def update(self, instance, validated_data):
        # De una ponderación existente solo se pueden cambiar las estrellas: ni el material ni
        # el usuario (cambiarlos podría chocar con otro voto y no tiene sentido de negocio).
        instance.valor = validated_data.get('valor', instance.valor)
        instance.save()
        return instance

    #Para el GET
    def get_material(self, obj):
        material = obj.material
        return MaterialSerializer(material, context=self.context).data

    def get_usuario(self, obj):
        usuario = obj.usuario
        return UsuarioPublicoSerializer(usuario).data
