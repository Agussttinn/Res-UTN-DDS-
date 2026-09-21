"""Reglas para los archivos que suben los usuarios (apuntes, resúmenes, parciales...)."""
import os
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# Solo formatos de estudio. Nada de .html/.svg/.js: un archivo así, servido desde nuestro dominio,
# podría ejecutar código en el navegador de quien lo abra.
EXTENSIONES_PERMITIDAS = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'png', 'jpg', 'jpeg']
TAMANO_MAXIMO_MB = 10


def ruta_material(instance, filename):
    """Guarda cada archivo como materiales/<uuid>.<ext>: evita colisiones de nombre y que
    alguien adivine la URL de un material que todavía no fue validado."""
    extension = os.path.splitext(filename)[1].lower()
    return f'materiales/{uuid.uuid4().hex}{extension}'


def validar_tamano(archivo):
    if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise ValidationError(f'El archivo no puede pesar más de {TAMANO_MAXIMO_MB} MB.')


validar_extension = FileExtensionValidator(allowed_extensions=EXTENSIONES_PERMITIDAS)
