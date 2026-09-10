from django.urls import path
from . import views

urlpatterns = [
    path('usuarios/', views.UsuarioListCreate.as_view()),
    path('usuarios/<str:pk>/', views.UsuarioDetail.as_view()),

    path('especialidades/', views.EspecialidadListCreate.as_view()),
    path('especialidades/<int:pk>/', views.EspecialidadDetail.as_view()),

    path('materias/', views.MateriaListCreate.as_view()),
    path('materias/<int:pk>/', views.MateriaDetail.as_view()),

    path('materiales/', views.MaterialListCreate.as_view()),
    path('materiales/<int:pk>/', views.MaterialDetail.as_view()),

    path('clases-apoyo/', views.ClaseApoyoListCreate.as_view()),
    path('clases-apoyo/<int:pk>/', views.ClaseApoyoDetail.as_view()),

    path('ponderaciones/', views.PonderacionListCreate.as_view()),
    path('ponderaciones/<int:pk>/', views.PonderacionDetail.as_view()),
]
