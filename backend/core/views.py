from django.shortcuts import render

# Create your views here.
from rest_framework import generics
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