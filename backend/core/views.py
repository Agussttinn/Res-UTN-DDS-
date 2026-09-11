from django.shortcuts import render
import requests
from django.contrib.auth.hashers import check_password, make_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# Create your views here.
from rest_framework import generics
from . import sysacad_client, sysacad_sync
from .models import Usuario, Especialidad, Materia, Material, ClaseApoyo, Ponderacion
from .serializer import (
    UsuarioSerializer,
    EspecialidadSerializer,
    MateriaSerializer,
    MaterialSerializer,
    ClaseApoyoSerializer,
    PonderacionSerializer,
)


class UsuarioListCreate(generics.ListCreateAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer


class UsuarioDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer


class EspecialidadListCreate(generics.ListCreateAPIView):
    queryset = Especialidad.objects.all()
    serializer_class = EspecialidadSerializer


class EspecialidadDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Especialidad.objects.all()
    serializer_class = EspecialidadSerializer


class MateriaListCreate(generics.ListCreateAPIView):
    queryset = Materia.objects.all()
    serializer_class = MateriaSerializer


class MateriaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Materia.objects.all()
    serializer_class = MateriaSerializer


class MateriaSincronizar(APIView):
    """Trae el plan de estudio de una carrera desde SySACAD y actualiza
    Especialidad/Materia locales. Devuelve las materias ya en el formato
    habitual de la API (MateriaSerializer), no el formato de SySACAD."""

    def post(self, request, carrera):
        try:
            materias = sysacad_sync.sync_materias(carrera.upper())
        except sysacad_client.PlanNoEncontrado:
            return Response(
                {"error": f'No existe un plan de estudio para la carrera "{carrera}" en SySACAD'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except sysacad_client.SysacadError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(MateriaSerializer(materias, many=True).data, status=status.HTTP_200_OK)


class MaterialListCreate(generics.ListCreateAPIView):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer


class MaterialDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer


class ClaseApoyoListCreate(generics.ListCreateAPIView):
    queryset = ClaseApoyo.objects.all()
    serializer_class = ClaseApoyoSerializer


class ClaseApoyoDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = ClaseApoyo.objects.all()
    serializer_class = ClaseApoyoSerializer


class PonderacionListCreate(generics.ListCreateAPIView):
    queryset = Ponderacion.objects.all()
    serializer_class = PonderacionSerializer


class PonderacionDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Ponderacion.objects.all()
    serializer_class = PonderacionSerializer

class LoginAlumno(APIView):
    def post(self,request):
        legajo = request.data.get('legajo')
        contrasena = request.data.get('contraseña')

        usuario = Usuario.objects.filter(legajo=legajo).first()
        if not usuario:
            return Response(
                {"error": "No existe un usuario con ese legajo"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not check_password(contrasena, usuario.contraseña):
            return Response(
                {"error": "Contraseña incorrecta"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return Response(
            {"message": "Login exitoso"},
            status=status.HTTP_200_OK
        )


class RegistroAlumno(APIView):
    def post(self, request):
        legajo = request.data.get('legajo')
        contrasena = request.data.get('contraseña')

        if not legajo or not contrasena:
            return Response(
                {"error": "Faltan legajo o contraseña"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. ¿Ya existe una cuenta con ese legajo en MI base?
        if Usuario.objects.filter(legajo=legajo).exists():
            return Response(
                {"error": "Ya existe una cuenta con ese legajo"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Consultar SysAcad para validar que sea un alumno real
        sysacad_response = requests.get(f"http://localhost:4000/alumnos/{legajo}")

        if sysacad_response.status_code == 404:
            return Response(
                {"error": "No existe ese legajo en SysAcad"},
                status=status.HTTP_400_BAD_REQUEST
            )

        datos_alumno = sysacad_response.json()

        # 3. Crear el Usuario en mi propia base
        nuevo_usuario = Usuario.objects.create(
            legajo=legajo,
            nombre_y_apellido=datos_alumno['nombre'],
            correo=datos_alumno['correo'],
            contraseña=make_password(contrasena),
            rol='alumno',
        )

        return Response(
            {"legajo": nuevo_usuario.legajo, "nombre_y_apellido": nuevo_usuario.nombre_y_apellido},
            status=status.HTTP_201_CREATED
        )