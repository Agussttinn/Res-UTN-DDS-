import datetime

from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Rol, Tutor, Usuario,Especialidad,Materia,EstadoMaterial,Material,ClaseApoyo,Ponderacion,MensajeClase,Notificacion
from .permissions import TUTOR


class UsuarioSerializer(serializers.ModelSerializer):
    # Solo se escribe (alta/cambio de clave por un administrador), nunca se devuelve en el JSON.
    # Se guarda hasheada, jamás en texto plano.
    contraseña = serializers.CharField(write_only=True, required=False)
    rol = serializers.SlugRelatedField(slug_field='nombre', queryset=Rol.objects.all())
    class Meta:
        model = Usuario
        fields = ('legajo','nombre_y_apellido','correo','rol','contraseña')
    
    def validate_contraseña(self, value):
        validate_password(value)  # largo mínimo, no demasiado común, no solo números
        return value

    def validate(self, attrs):
        if self.instance is None and 'contraseña' not in attrs:
            raise serializers.ValidationError({'contraseña': 'Este campo es obligatorio.'})
        # Cambiar de rol a alguien con apuntes, puntuaciones, clases o mensajes de su rol anterior no se permite.
        if self.instance is not None and 'rol' in attrs and attrs['rol'].id != self.instance.rol_id:
            motivo = self.instance.motivo_para_no_dejar_el_rol()
            if motivo:
                raise serializers.ValidationError({'rol': motivo})
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
    rol = serializers.SlugRelatedField(slug_field='nombre', read_only=True)
    class Meta:
        model = Usuario
        fields = ('legajo','nombre_y_apellido','rol')


class EspecialidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidad
        fields = ('id','nombre')

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ('id','nombre')

class MateriaSerializer(serializers.ModelSerializer):
    especialidad_id = serializers.IntegerField(write_only=True)
    especialidad = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        fields = ('id','nombre','anio','electiva','especialidad','especialidad_id')

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
    estado = serializers.SerializerMethodField()
    validacion = serializers.SerializerMethodField()
    promedio_ponderacion = serializers.SerializerMethodField()
    cantidad_ponderaciones = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = ('id','materia','usuario','titulo','fecha_de_carga','tipo','estado','validacion','motivo_rechazo','comentario','archivo','promedio_ponderacion','cantidad_ponderaciones','materia_id')
        # estado y validacion NO se pueden escribir desde afuera: un material nace pendiente y solo un
        # administrador lo aprueba (POST /materiales/<id>/moderar/). Si no, cada alumno se auto-validaría.
        read_only_fields = ('motivo_rechazo',)
        # El autor (alumno) tampoco se manda en el JSON: sale del token del que está logueado
        # (la vista lo pasa con serializer.save(alumno=...)), así nadie sube material a nombre de otro.
 
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

        # validated_data ya trae 'alumno' (lo agrega la vista con serializer.save(alumno=...))
        material = Material.objects.create(
            materia_id = materia_id,
            estado = EstadoMaterial.objects.get(nombre=EstadoMaterial.PENDIENTE),
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
        return UsuarioPublicoSerializer(obj.alumno.usuario).data

    def get_estado(self, obj):
        return obj.estado.nombre

    def get_validacion(self, obj):
        # Compatibilidad con el frontend: true si el material ya pasó la moderación (aprobado o archivado).
        return obj.estado.nombre in (EstadoMaterial.APROBADO, EstadoMaterial.ARCHIVADO)
 
    # Ponderación del material = última media guardada de las estrellas (1 a 5) que le pusieron los usuarios.
    # Se actualiza al votar (ver Material.recalcular_ponderacion). Si todavía nadie lo puntuó es None
    # (null en el JSON) y la cantidad es 0.
    def get_promedio_ponderacion(self, obj):
        promedio = obj.promedio_ponderacion
        return round(float(promedio), 1) if promedio is not None else None

    def get_cantidad_ponderaciones(self, obj):
        return obj.cantidad_ponderaciones

# Franja en la que se pueden dar clases de apoyo (horario de la facultad) y duración mínima de una clase.
HORA_MINIMA_CLASE = datetime.time(9, 0)
HORA_MAXIMA_CLASE = datetime.time(23, 30)
DURACION_MINIMA_CLASE = datetime.timedelta(minutes=30)


def _minutos(hora):
    return hora.hour * 60 + hora.minute


class ClaseApoyoSerializer(serializers.ModelSerializer):
    materia_id = serializers.IntegerField(write_only=True)
    # Día (1 = lunes ... 6 = sábado) y horas "HH:MM". Se guardan por separado para poder validarlos y ordenar el cronograma.
    dia = serializers.ChoiceField(
        choices=ClaseApoyo.DIAS,
        error_messages={'invalid_choice': 'Elegí un día de lunes a sábado.', 'null': 'Elegí el día.'},
    )
    hora_inicio = serializers.TimeField(
        format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'],
        error_messages={'invalid': 'Usá el formato HH:MM (por ejemplo 14:00).', 'null': 'Indicá la hora de inicio.'},
    )
    hora_fin = serializers.TimeField(
        format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'],
        error_messages={'invalid': 'Usá el formato HH:MM (por ejemplo 16:00).', 'null': 'Indicá la hora de fin.'},
    )
    # Solo lectura, para mostrar: "lunes de 14:00 a 16:00" (o "a confirmar" en clases viejas sin datos).
    horario = serializers.CharField(read_only=True)
    # Opcional: si quien crea la clase es un tutor, el tutor es él mismo (sale del token).
    # Solo un administrador necesita indicar de qué tutor es la clase.
    tutor_id = serializers.CharField(write_only=True, required=False)
    materia = serializers.SerializerMethodField()
    tutor = serializers.SerializerMethodField()
    # Los calcula la vista en la misma consulta (ver _clases_apoyo_queryset); al crear una clase todavía son 0/False.
    suscrito = serializers.SerializerMethodField()
    cantidad_suscritos = serializers.SerializerMethodField()

    class Meta:
        model = ClaseApoyo
        fields = ('id','materia','tutor','dia','hora_inicio','hora_fin','horario','aula','suscrito','cantidad_suscritos','materia_id','tutor_id')

    def get_suscrito(self, obj):
        return bool(getattr(obj, 'suscrito', False))

    def get_cantidad_suscritos(self, obj):
        return getattr(obj, 'cantidad_suscritos', 0)

    def validate_materia_id(self, value):
        if not Materia.objects.filter(pk=value).exists():
            raise serializers.ValidationError("No existe una materia con ese id.")
        return value

    def validate_tutor_id(self, value):
        # Alcanza con que el usuario tenga rol tutor: su fila en la tabla tutores se completa al asignarle la clase.
        if not Usuario.objects.filter(pk=value, rol__nombre=TUTOR).exists():
            raise serializers.ValidationError("No existe un tutor con ese legajo.")
        return value

    def validate(self, attrs):
        """Día y horario completos, en la franja de la facultad, con el fin después del inicio y sin superponerse
        con otra clase del mismo tutor. Al modificar, se combinan los datos nuevos con los que ya tenía la clase."""
        clase = self.instance

        def valor(campo):
            return attrs[campo] if campo in attrs else getattr(clase, campo, None)

        dia, inicio, fin = valor('dia'), valor('hora_inicio'), valor('hora_fin')
        faltan = {
            campo: mensaje for campo, mensaje, dato in (
                ('dia', 'Elegí el día.', dia),
                ('hora_inicio', 'Indicá la hora de inicio.', inicio),
                ('hora_fin', 'Indicá la hora de fin.', fin),
            ) if dato is None
        }
        if faltan:
            raise serializers.ValidationError(faltan)

        rango = f'{HORA_MINIMA_CLASE:%H:%M} y {HORA_MAXIMA_CLASE:%H:%M}'
        errores = {}
        if not HORA_MINIMA_CLASE <= inicio <= HORA_MAXIMA_CLASE:
            errores['hora_inicio'] = f'Tiene que estar entre las {rango}.'
        if not HORA_MINIMA_CLASE <= fin <= HORA_MAXIMA_CLASE:
            errores['hora_fin'] = f'Tiene que estar entre las {rango}.'
        if not errores and _minutos(fin) - _minutos(inicio) < DURACION_MINIMA_CLASE.total_seconds() / 60:
            errores['hora_fin'] = (
                'Tiene que ser posterior a la hora de inicio.' if fin <= inicio
                else f'La clase tiene que durar al menos {int(DURACION_MINIMA_CLASE.total_seconds() // 60)} minutos.'
            )
        if errores:
            raise serializers.ValidationError(errores)

        # Un tutor no puede estar en dos clases a la vez.
        tutor_id = self._tutor_de_la_clase(attrs)
        if tutor_id is not None:
            superpuesta = ClaseApoyo.objects.filter(
                tutor_id=tutor_id, dia=dia, hora_inicio__lt=fin, hora_fin__gt=inicio,
            ).exclude(pk=getattr(clase, 'pk', None)).select_related('materia').first()
            if superpuesta:
                raise serializers.ValidationError({'hora_inicio': (
                    f'Se superpone con otra clase del mismo tutor: {superpuesta.materia.nombre}, '
                    f'{superpuesta.horario}.'
                )})
        return attrs

    def _tutor_de_la_clase(self, attrs):
        """El tutor que va a tener la clase: quien la crea si es tutor; si no, el indicado o el que ya tenía."""
        usuario = self.context['request'].user
        if usuario.rol.nombre == TUTOR and self.instance is None:
            return usuario.pk
        if attrs.get('tutor_id') and usuario.rol.nombre != TUTOR:
            return attrs['tutor_id']
        return getattr(self.instance, 'tutor_id', None)

    #Para el POST
    def create(self, validated_data):
        materia_id = validated_data.pop('materia_id')
        tutor_id = validated_data.pop('tutor_id', None)

        quien_crea = self.context['request'].user
        if quien_crea.rol.nombre == TUTOR:
            tutor_id = quien_crea.pk  # un tutor solo puede crear clases a su nombre
        if not tutor_id:
            raise serializers.ValidationError({'tutor_id': 'Indicá el legajo del tutor a cargo de la clase.'})

        Tutor.objects.get_or_create(usuario_id=tutor_id)  # por si le falta su fila en tutores
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
        if tutor_id is not None and self.context['request'].user.rol.nombre != TUTOR:
            Tutor.objects.get_or_create(usuario_id=tutor_id)
            instance.tutor_id = tutor_id

        instance.save()
        return instance


    #Para el GET
    def get_materia(self, obj):
        materia = obj.materia
        return MateriaSerializer(materia).data

    def get_tutor(self, obj):
        return UsuarioPublicoSerializer(obj.tutor.usuario).data


class PonderacionSerializer(serializers.ModelSerializer):
    material_id = serializers.IntegerField(write_only=True)
    material = serializers.SerializerMethodField()
    usuario = serializers.SerializerMethodField()

    class Meta:
        model = Ponderacion
        fields = ('material','usuario','valor','fecha','material_id')
        # Una ponderación no tiene sentido que tenga un id, por eso la API no lo va a devolver en el JSON
        # El alumno que puntúa sale del token (la vista hace serializer.save(alumno=...)):
        # nadie puede puntuar a nombre de otro.

    def validate_material_id(self, value):
        if not Material.objects.filter(pk=value).exists():
            raise serializers.ValidationError("No existe un material con ese id.")
        return value

    def validate(self, attrs):
    # Reglas de negocio al puntuar (no aplican al editar las estrellas de un voto existente).
        if self.instance is None:
            material = Material.objects.select_related('estado').get(pk=attrs['material_id'])
            if material.estado.nombre != EstadoMaterial.APROBADO:
                raise serializers.ValidationError({'material_id': 'Solo se pueden puntuar materiales ya validados.'})
            if material.alumno_id == self.context['request'].user.pk:
                raise serializers.ValidationError({'material_id': 'No podés puntuar tu propio material.'})
        return attrs

    #Para el POST
    # Un alumno tiene una sola ponderación por material: si ya había votado, se actualiza
    # su valor (cambia sus estrellas); si no, se crea una nueva.
    def create(self, validated_data):
        material_id = validated_data.pop('material_id')
        alumno = validated_data.pop('alumno')  # lo agrega la vista con serializer.save(alumno=...)

        ponderacion, _ = Ponderacion.objects.update_or_create(
            material_id = material_id,
            alumno = alumno,
            defaults = validated_data,
        )
        ponderacion.material.recalcular_ponderacion()

        return ponderacion

    def update(self, instance, validated_data):
        # De una ponderación existente solo se pueden cambiar las estrellas: ni el material ni
        # el alumno (cambiarlos podría chocar con otro voto y no tiene sentido de negocio).
        instance.valor = validated_data.get('valor', instance.valor)
        instance.save()
        instance.material.recalcular_ponderacion()
        return instance

    #Para el GET
    def get_material(self, obj):
        material = obj.material
        return MaterialSerializer(material, context=self.context).data

    def get_usuario(self, obj):
        return UsuarioPublicoSerializer(obj.alumno.usuario).data


class MensajeClaseSerializer(serializers.ModelSerializer):
    autor = serializers.SerializerMethodField()
    # El autor y la clase no se mandan: salen del token y de la URL.
    texto = serializers.CharField(max_length=1000, trim_whitespace=True)

    class Meta:
        model = MensajeClase
        fields = ('id', 'autor', 'texto', 'fecha')

    def get_autor(self, obj):
        return UsuarioPublicoSerializer(obj.tutor.usuario).data


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ('id', 'tipo', 'titulo', 'texto', 'fecha', 'leida', 'clase')
        read_only_fields = fields
