import datetime
import io
from importlib import import_module
import os
import shutil
import tempfile
from unittest.mock import Mock, patch

import jwt
import requests
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APITestCase

from . import sysacad_client
from .admin import UsuarioAdmin
from .archivos import TAMANO_MAXIMO_MB
from .auth import crear_token
from .models import (
    Administrador, Alumno, ClaseApoyo, Especialidad, EstadoMaterial, Materia, Material, MensajeClase, Notificacion,
    Ponderacion, Rol, Suscripcion, Tutor, Usuario,
)
from .observador import EventoClase, ObservadorClase, SujetoClase

CONTRASENA = 'claveSegura123'
# Los tests parchean la función de red que usa el cliente de SySACAD: nunca dependen del mock real.
PARCHE_SYSACAD = 'core.sysacad_client.requests.get'


class ApiTestCase(APITestCase):
    """Base común: hasher rápido, caché limpia (los límites de intentos viven ahí), archivos en una carpeta
    temporal (los tests nunca escriben en media/ de verdad) y algunos datos de ejemplo."""

    def setUp(self):
        cache.clear()
        self.enterContext(override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']))
        carpeta_media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, carpeta_media, ignore_errors=True)
        self.enterContext(override_settings(MEDIA_ROOT=carpeta_media))

        self.especialidad = Especialidad.objects.create(nombre='Sistemas', codigo_sysacad='ISI')
        self.materia = Materia.objects.create(nombre='Algoritmos', anio=1, especialidad=self.especialidad)
        self.otra_materia = Materia.objects.create(nombre='Física', anio=1, especialidad=self.especialidad)

        self.admin = self.crear_usuario('1', 'administrador')
        self.tutor = self.crear_usuario('2', 'tutor')
        self.otro_tutor = self.crear_usuario('3', 'tutor')
        self.alumno = self.crear_usuario('4')
        self.otro_alumno = self.crear_usuario('5')

    @staticmethod
    def crear_usuario(legajo, rol='alumno', contrasena=CONTRASENA):
        return Usuario.objects.create(
            legajo=legajo, nombre_y_apellido=f'Usuario {legajo}', correo=f'u{legajo}@mail.com',
            contraseña=make_password(contrasena), rol=Rol.objects.get(nombre=rol),
        )

    def como(self, usuario):
        """Los próximos requests los hace `usuario` (equivale a mandar su token)."""
        self.client.force_authenticate(user=usuario)

    def crear_material(self, autor=None, validado=False, materia=None, titulo='Resumen U1'):
        return Material.objects.create(
            materia=materia or self.materia, alumno=(autor or self.alumno).alumno, titulo=titulo,
            tipo='resumen',
            estado=EstadoMaterial.objects.get(nombre='aprobado' if validado else 'pendiente'),
            archivo=SimpleUploadedFile('apunte.pdf', b'%PDF-1.4 contenido', content_type='application/pdf'),
        )


# ---------------------------------------------------------------- registro

class RegistroAlumnoTests(ApiTestCase):
    url = '/api/registro/'

    @staticmethod
    def _sysacad_ok(legajo="48293", nombre="Sofía Martínez", correo="smartinez@frd.utn.edu.ar"):
        """Simula la respuesta 200 de GET /alumnos/{legajo} en el mock-sysacad."""
        respuesta = Mock()
        respuesta.status_code = 200
        respuesta.json.return_value = {"legajo": legajo, "nombre": nombre, "correo": correo, "carrera": "ISI"}
        return respuesta

    @staticmethod
    def _sysacad_404():
        """Simula que el legajo no existe en SysAcad."""
        respuesta = Mock()
        respuesta.status_code = 404
        return respuesta

    def registrar(self, legajo="48293", contrasena="miclave123"):
        return self.client.post(self.url, {"legajo": legajo, "contraseña": contrasena}, format='json')

    @patch(PARCHE_SYSACAD)
    def test_registro_exitoso(self, mock_get):
        mock_get.return_value = self._sysacad_ok()

        response = self.registrar()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['legajo'], "48293")
        self.assertEqual(response.data['nombre_y_apellido'], "Sofía Martínez")

        usuario = Usuario.objects.get(legajo="48293")
        self.assertEqual(usuario.correo, "smartinez@frd.utn.edu.ar")
        self.assertEqual(usuario.rol.nombre, "alumno")
        # la contraseña nunca se guarda en texto plano
        self.assertNotEqual(usuario.contraseña, "miclave123")
        self.assertTrue(check_password("miclave123", usuario.contraseña))
        # se consulta SySACAD con timeout (si SySACAD se cuelga, el registro no se queda esperando para siempre)
        mock_get.assert_called_once_with(f"{settings.SYSACAD_API_URL}/alumnos/48293", timeout=sysacad_client.TIMEOUT_SEGUNDOS)

    @patch(PARCHE_SYSACAD)
    def test_legajo_ya_registrado(self, mock_get):
        response = self.registrar(legajo=self.alumno.legajo)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        # si ya existe localmente, ni hace falta preguntarle a SysAcad
        mock_get.assert_not_called()
        self.assertEqual(Usuario.objects.filter(legajo=self.alumno.legajo).count(), 1)

    @patch(PARCHE_SYSACAD)
    def test_legajo_inexistente_en_sysacad(self, mock_get):
        mock_get.return_value = self._sysacad_404()
        cantidad_antes = Usuario.objects.count()

        response = self.registrar(legajo="99999")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(Usuario.objects.count(), cantidad_antes)

    def test_faltan_campos(self):
        cantidad_antes = Usuario.objects.count()
        response = self.client.post(self.url, {"legajo": "48293"}, format='json')  # sin contraseña

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(Usuario.objects.count(), cantidad_antes)

    def test_body_que_no_es_un_objeto_json(self):
        response = self.client.post(self.url, [1, 2, 3], format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(PARCHE_SYSACAD)
    def test_legajo_con_caracteres_raros_no_llega_a_sysacad(self, mock_get):
        for legajo in ("../admin", "12/34", "12 34", "a" * 21):
            response = self.registrar(legajo=legajo)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, legajo)
        mock_get.assert_not_called()

    @patch(PARCHE_SYSACAD)
    def test_contrasena_debil(self, mock_get):
        for contrasena in ("123", "12345678", "password"):
            response = self.registrar(contrasena=contrasena)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, contrasena)
        mock_get.assert_not_called()

    @patch(PARCHE_SYSACAD)
    def test_sysacad_caido(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("mock caído")
        cantidad_antes = Usuario.objects.count()

        response = self.registrar()

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(Usuario.objects.count(), cantidad_antes)

    @patch(PARCHE_SYSACAD)
    def test_sysacad_devuelve_datos_incompletos(self, mock_get):
        respuesta = Mock(status_code=200)
        respuesta.json.return_value = {"legajo": "48293"}  # sin nombre ni correo
        mock_get.return_value = respuesta

        self.assertEqual(self.registrar().status_code, status.HTTP_502_BAD_GATEWAY)

    @patch(PARCHE_SYSACAD)
    def test_correo_ya_asociado_a_otra_cuenta(self, mock_get):
        mock_get.return_value = self._sysacad_ok(correo=self.alumno.correo)

        response = self.registrar()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Usuario.objects.filter(legajo="48293").exists())

    @patch(PARCHE_SYSACAD)
    def test_registro_ignora_un_token_invalido(self, mock_get):
        mock_get.return_value = self._sysacad_ok()

        response = self.client.post(
            self.url, {"legajo": "48293", "contraseña": "miclave123"}, format='json',
            HTTP_AUTHORIZATION='Bearer token-basura',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(PARCHE_SYSACAD)
    def test_limite_de_intentos(self, mock_get):
        mock_get.return_value = self._sysacad_404()
        for _ in range(10):
            self.assertEqual(self.registrar(legajo="99999").status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.registrar(legajo="99999").status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class SysacadClientTests(ApiTestCase):
    @patch(PARCHE_SYSACAD)
    def test_el_legajo_se_escapa_en_la_url(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {})

        sysacad_client.get_alumno("../admin")

        url = mock_get.call_args[0][0]
        self.assertEqual(url, f"{settings.SYSACAD_API_URL}/alumnos/..%2Fadmin")

    @patch(PARCHE_SYSACAD)
    def test_errores_de_red_y_respuestas_raras_son_SysacadError(self, mock_get):
        mock_get.side_effect = requests.Timeout("tardó demasiado")
        with self.assertRaises(sysacad_client.SysacadError):
            sysacad_client.get_alumno("1")

        mock_get.side_effect = None
        respuesta_500 = Mock(status_code=500)
        respuesta_500.raise_for_status.side_effect = requests.HTTPError("500")
        mock_get.return_value = respuesta_500
        with self.assertRaises(sysacad_client.SysacadError):
            sysacad_client.get_alumno("1")

        respuesta_no_json = Mock(status_code=200)
        respuesta_no_json.json.side_effect = ValueError("no es JSON")
        mock_get.return_value = respuesta_no_json
        with self.assertRaises(sysacad_client.SysacadError):
            sysacad_client.get_plan("ISI")

    @patch(PARCHE_SYSACAD)
    def test_404_es_alumno_o_plan_no_encontrado(self, mock_get):
        mock_get.return_value = Mock(status_code=404)

        with self.assertRaises(sysacad_client.AlumnoNoEncontrado):
            sysacad_client.get_alumno("1")
        with self.assertRaises(sysacad_client.PlanNoEncontrado):
            sysacad_client.get_plan("XXX")


# ---------------------------------------------------------------- login y token

class LoginTests(ApiTestCase):
    url = '/api/login/'

    def login(self, legajo=None, contrasena=CONTRASENA, **extra):
        return self.client.post(
            self.url, {"legajo": legajo or self.alumno.legajo, "contraseña": contrasena}, format='json', **extra
        )

    def test_login_devuelve_token_y_datos_del_usuario(self):
        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['usuario']['legajo'], self.alumno.legajo)
        self.assertEqual(response.data['usuario']['rol'], 'alumno')
        self.assertNotIn('contraseña', response.data['usuario'])
        payload = jwt.decode(response.data['access'], settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(payload['sub'], self.alumno.legajo)

    def test_el_token_sirve_para_entrar_a_la_api(self):
        token = self.login().data['access']

        response = self.client.get('/api/materias/', HTTP_AUTHORIZATION=f'Bearer {token}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_contrasena_incorrecta(self):
        response = self.login(contrasena='otra-clave')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)

    def test_legajo_inexistente_da_el_mismo_error_que_contrasena_incorrecta(self):
        # así no se puede averiguar qué legajos están registrados
        mal_legajo = self.login(legajo='no-existe')
        mala_clave = self.login(contrasena='otra-clave')

        self.assertEqual(mal_legajo.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(mal_legajo.data, mala_clave.data)

    def test_faltan_campos_o_body_invalido(self):
        self.assertEqual(self.client.post(self.url, {"legajo": "4"}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, {}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, [1, 2], format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, {"legajo": "4", "contraseña": 1234}, format='json').status_code, 400)

    def test_login_ignora_un_token_invalido(self):
        response = self.login(HTTP_AUTHORIZATION='Bearer token-basura')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_limite_de_intentos(self):
        for _ in range(10):
            self.assertEqual(self.login(contrasena='mal').status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(self.login().status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class AutenticacionTests(ApiTestCase):
    def get(self, authorization=None):
        extra = {'HTTP_AUTHORIZATION': authorization} if authorization else {}
        return self.client.get('/api/materias/', **extra)

    def test_sin_token_es_401(self):
        response = self.get()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response['WWW-Authenticate'], 'Bearer')

    def test_token_invalido_o_mal_formado(self):
        self.assertEqual(self.get('Bearer basura').status_code, 401)
        self.assertEqual(self.get('Bearer').status_code, 401)
        self.assertEqual(self.get('Bearer a b').status_code, 401)
        self.assertEqual(self.get('Basic abc').status_code, 401)

    def test_token_firmado_con_otra_clave(self):
        falso = jwt.encode({'sub': self.admin.legajo, 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)},
                           'otra-clave-que-no-es-la-del-servidor-1234567890', algorithm='HS256')

        self.assertEqual(self.get(f'Bearer {falso}').status_code, 401)

    def test_token_vencido(self):
        vencido = jwt.encode({'sub': self.alumno.legajo, 'exp': datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)},
                             settings.SECRET_KEY, algorithm='HS256')

        response = self.get(f'Bearer {vencido}')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_de_un_usuario_que_ya_no_existe(self):
        token = crear_token(self.otro_alumno)
        self.otro_alumno.delete()

        self.assertEqual(self.get(f'Bearer {token}').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_el_rol_se_lee_de_la_base_no_del_token(self):
        token = crear_token(self.admin)
        self.assertEqual(self.client.get('/api/usuarios/', HTTP_AUTHORIZATION=f'Bearer {token}').status_code, 200)

        Usuario.objects.filter(pk=self.admin.pk).update(rol=Rol.objects.get(nombre='alumno'))  # le sacan el rol de administrador

        self.assertEqual(self.client.get('/api/usuarios/', HTTP_AUTHORIZATION=f'Bearer {token}').status_code, 403)


# ---------------------------------------------------------------- usuarios, especialidades, materias

class PermisosGeneralesTests(ApiTestCase):
    def test_ningun_recurso_es_publico_salvo_login_y_registro(self):
        rutas = [
            '/api/usuarios/', '/api/usuarios/4/', '/api/roles/', '/api/especialidades/', '/api/materias/',
            '/api/materiales/', '/api/materiales/pendientes/', '/api/clases-apoyo/', '/api/ponderaciones/',
        ]
        for ruta in rutas:
            self.assertEqual(self.client.get(ruta).status_code, status.HTTP_401_UNAUTHORIZED, ruta)
        self.assertEqual(self.client.post('/api/usuarios/', {}, format='json').status_code, 401)
        self.assertEqual(self.client.delete('/api/usuarios/4/').status_code, 401)
        self.assertEqual(self.client.post('/api/materias/sincronizar/ISI/').status_code, 401)
        self.assertEqual(self.client.post('/api/materiales/1/moderar/', {'accion': 'aprobar'}, format='json').status_code, 401)


class UsuarioApiTests(ApiTestCase):
    def datos_nuevo_tutor(self, **cambios):
        datos = {"legajo": "77", "nombre_y_apellido": "Nuevo Tutor", "correo": "nuevo@mail.com", "rol": "tutor", "contraseña": CONTRASENA}
        datos.update(cambios)
        return datos

    def test_un_alumno_no_puede_crear_usuarios_ni_administradores(self):
        self.como(self.alumno)

        response = self.client.post('/api/usuarios/', self.datos_nuevo_tutor(rol='administrador'), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Usuario.objects.filter(legajo='77').exists())

    def test_el_administrador_da_de_alta_un_tutor_con_contrasena_hasheada(self):
        self.como(self.admin)

        response = self.client.post('/api/usuarios/', self.datos_nuevo_tutor(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('contraseña', response.data)
        tutor = Usuario.objects.get(legajo='77')
        self.assertEqual(tutor.rol.nombre, 'tutor')
        self.assertNotEqual(tutor.contraseña, CONTRASENA)
        self.assertTrue(check_password(CONTRASENA, tutor.contraseña))

    def test_alta_sin_contrasena_o_con_contrasena_debil(self):
        self.como(self.admin)
        sin_clave = self.datos_nuevo_tutor()
        del sin_clave['contraseña']

        self.assertEqual(self.client.post('/api/usuarios/', sin_clave, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/usuarios/', self.datos_nuevo_tutor(contraseña='123'), format='json').status_code, 400)
        self.assertFalse(Usuario.objects.filter(legajo='77').exists())

    def test_el_listado_de_usuarios_es_solo_para_administradores(self):
        self.como(self.alumno)
        self.assertEqual(self.client.get('/api/usuarios/').status_code, status.HTTP_403_FORBIDDEN)

        self.como(self.admin)
        response = self.client.get('/api/usuarios/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        self.assertTrue(all('contraseña' not in usuario for usuario in response.data))

    def test_un_usuario_ve_su_perfil_pero_no_el_de_otros(self):
        self.como(self.alumno)

        self.assertEqual(self.client.get(f'/api/usuarios/{self.alumno.legajo}/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/usuarios/{self.otro_alumno.legajo}/').status_code, 403)

    def test_un_alumno_no_puede_editarse_a_si_mismo_el_rol(self):
        self.como(self.alumno)

        response = self.client.patch(f'/api/usuarios/{self.alumno.legajo}/', {'rol': 'administrador'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.rol.nombre, 'alumno')

    def test_el_administrador_cambia_la_contrasena_y_no_puede_cambiar_el_legajo(self):
        self.como(self.admin)

        response = self.client.patch(
            f'/api/usuarios/{self.alumno.legajo}/', {'contraseña': 'otraClave456', 'legajo': '999'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alumno.refresh_from_db()
        self.assertTrue(check_password('otraClave456', self.alumno.contraseña))
        self.assertFalse(Usuario.objects.filter(legajo='999').exists())

    def test_borrar_un_usuario_con_material_da_409_y_no_500(self):
        self.crear_material(autor=self.alumno)
        self.como(self.admin)

        response = self.client.delete(f'/api/usuarios/{self.alumno.legajo}/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Usuario.objects.filter(pk=self.alumno.pk).exists())

    def test_borrar_un_usuario_sin_dependencias(self):
        self.como(self.admin)

        self.assertEqual(self.client.delete(f'/api/usuarios/{self.otro_alumno.legajo}/').status_code, 204)


class UsuarioAdminDjangoTests(ApiTestCase):
    """El formulario del admin de Django guarda la contraseña como texto: tiene que hashearla."""

    def guardar(self, usuario):
        UsuarioAdmin(Usuario, admin.site).save_model(request=None, obj=usuario, form=None, change=False)

    def test_hashea_una_contrasena_en_texto_plano(self):
        usuario = Usuario(legajo='88', nombre_y_apellido='A', correo='a88@mail.com', rol=Rol.objects.get(nombre='administrador'), contraseña='texto-plano')

        self.guardar(usuario)

        guardado = Usuario.objects.get(legajo='88')
        self.assertNotEqual(guardado.contraseña, 'texto-plano')
        self.assertTrue(check_password('texto-plano', guardado.contraseña))

    def test_no_vuelve_a_hashear_un_hash_existente(self):
        hash_original = self.alumno.contraseña

        self.guardar(self.alumno)

        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.contraseña, hash_original)


class EspecialidadYMateriaApiTests(ApiTestCase):
    def test_solo_el_administrador_lista_los_roles(self):
        self.como(self.alumno)
        self.assertEqual(self.client.get('/api/roles/').status_code, 403)

        self.como(self.admin)
        response = self.client.get('/api/roles/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r['nombre'] for r in response.data], ['alumno', 'tutor', 'administrador'])
        self.assertEqual(self.client.post('/api/roles/', {'nombre': 'X'}, format='json').status_code, 405)

    def test_filtra_materias_por_especialidad(self):
        otra = Especialidad.objects.create(nombre='Química', codigo_sysacad='QUI')
        quimica = Materia.objects.create(nombre='Química General', anio=1, especialidad=otra)
        self.como(self.alumno)

        with override_settings(CARRERAS_HABILITADAS=['ISI', 'QUI']):
            response = self.client.get(f'/api/materias/?especialidad={otra.id}')

        self.assertEqual([m['id'] for m in response.data], [quimica.id])

    def test_un_alumno_lee_pero_no_escribe(self):
        self.como(self.alumno)

        self.assertEqual(self.client.get('/api/materias/').status_code, 200)
        self.assertEqual(self.client.get('/api/especialidades/').status_code, 200)
        self.assertEqual(self.client.post('/api/especialidades/', {'nombre': 'X'}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/materias/', {'nombre': 'X', 'anio': 1, 'especialidad_id': self.especialidad.id}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/materias/{self.materia.id}/').status_code, 403)
        self.assertTrue(Materia.objects.filter(pk=self.materia.pk).exists())

    def test_el_administrador_crea_una_materia_con_su_especialidad(self):
        self.como(self.admin)

        response = self.client.post(
            '/api/materias/', {'nombre': 'Química', 'anio': 1, 'especialidad_id': self.especialidad.id}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['especialidad']['nombre'], 'Sistemas')
        self.assertEqual(Materia.objects.get(nombre='Química').especialidad, self.especialidad)

    def test_materia_sin_especialidad_o_con_una_inexistente_es_400_y_no_500(self):
        self.como(self.admin)

        sin_especialidad = self.client.post('/api/materias/', {'nombre': 'X', 'anio': 1}, format='json')
        inexistente = self.client.post('/api/materias/', {'nombre': 'X', 'anio': 1, 'especialidad_id': 9999}, format='json')

        self.assertEqual(sin_especialidad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(inexistente.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('especialidad_id', inexistente.data)

    def test_el_administrador_puede_cambiar_la_especialidad_de_una_materia(self):
        otra = Especialidad.objects.create(nombre='Química')
        self.como(self.admin)

        response = self.client.patch(f'/api/materias/{self.materia.id}/', {'especialidad_id': otra.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.materia.refresh_from_db()
        self.assertEqual(self.materia.especialidad, otra)

    def test_borrar_una_especialidad_con_materias_da_409_y_no_500(self):
        self.como(self.admin)

        response = self.client.delete(f'/api/especialidades/{self.especialidad.id}/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    @patch(PARCHE_SYSACAD)
    def test_sincronizar_es_solo_para_administradores(self, mock_get):
        plan = {"nombre": "Ingeniería en Sistemas", "materias": [{"idMateria": "ISI-1", "nombre": "Análisis", "nivel": 1}]}
        mock_get.return_value = Mock(status_code=200, json=lambda: plan)

        self.como(self.alumno)
        self.assertEqual(self.client.post('/api/materias/sincronizar/ISI/').status_code, 403)
        mock_get.assert_not_called()

        self.como(self.admin)
        response = self.client.post('/api/materias/sincronizar/isi/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['nombre'], 'Análisis')
        self.assertTrue(Materia.objects.filter(id_sysacad='ISI-1').exists())

    @patch(PARCHE_SYSACAD)
    def test_sincronizar_con_sysacad_caido_o_carrera_inexistente(self, mock_get):
        self.como(self.admin)

        mock_get.side_effect = requests.ConnectionError('caído')
        self.assertEqual(self.client.post('/api/materias/sincronizar/ISI/').status_code, status.HTTP_502_BAD_GATEWAY)

        mock_get.side_effect = None
        mock_get.return_value = Mock(status_code=404)
        self.assertEqual(self.client.post('/api/materias/sincronizar/ISI/').status_code, status.HTTP_404_NOT_FOUND)

    @patch(PARCHE_SYSACAD)
    def test_solo_se_sincronizan_las_carreras_habilitadas(self, mock_get):
        self.como(self.admin)

        response = self.client.post('/api/materias/sincronizar/QUI/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ISI', response.data['error'])
        mock_get.assert_not_called()

    @patch(PARCHE_SYSACAD)
    def test_sincronizar_separa_las_electivas_y_no_duplica(self, mock_get):
        plan = {"nombre": "Ingeniería en Sistemas de Información", "materias": [
            {"idMateria": "5-2023-101", "nombre": "Análisis Matemático I", "nivel": 1},
            {"idMateria": "5-2023-212", "nombre": "Entornos Gráficos (Elec.)", "nivel": 2},
        ]}
        mock_get.return_value = Mock(status_code=200, json=lambda: plan)
        self.como(self.admin)

        self.client.post('/api/materias/sincronizar/ISI/')
        self.client.post('/api/materias/sincronizar/ISI/')

        electiva = Materia.objects.get(id_sysacad='5-2023-212')
        self.assertEqual((electiva.nombre, electiva.anio, electiva.electiva), ('Entornos Gráficos', 2, True))
        self.assertFalse(Materia.objects.get(id_sysacad='5-2023-101').electiva)
        self.assertEqual(Materia.objects.filter(id_sysacad__startswith='5-2023').count(), 2)

    def test_la_lista_de_materias_es_solo_de_las_carreras_habilitadas(self):
        quimica = Especialidad.objects.create(nombre='Química', codigo_sysacad='QUI')
        Materia.objects.create(nombre='Química General', anio=1, especialidad=quimica)
        self.como(self.alumno)

        nombres = [m['nombre'] for m in self.client.get('/api/materias/').data]

        self.assertNotIn('Química General', nombres)
        self.assertIn('Algoritmos', nombres)

    def test_filtrar_materias_por_anio_y_electiva(self):
        Materia.objects.create(nombre='Entornos Gráficos', anio=2, electiva=True, especialidad=self.especialidad)
        Materia.objects.create(nombre='Física II', anio=2, especialidad=self.especialidad)
        self.como(self.alumno)

        def nombres(query):
            response = self.client.get(f'/api/materias/{query}')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return [m['nombre'] for m in response.data]

        self.assertEqual(nombres('?anio=1'), ['Algoritmos', 'Física'])
        self.assertEqual(nombres('?anio=2&electiva=false'), ['Física II'])
        self.assertEqual(nombres('?electiva=true'), ['Entornos Gráficos'])
        self.assertEqual(nombres('?buscar=gráf'), ['Entornos Gráficos'])  # busca en todos los años
        self.assertEqual(nombres('?buscar=fís'), ['Física', 'Física II'])
        self.assertTrue(self.client.get('/api/materias/?electiva=true').data[0]['electiva'])

    def test_filtros_de_materias_invalidos_son_400(self):
        self.como(self.alumno)

        self.assertEqual(self.client.get('/api/materias/?anio=uno').status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get('/api/materias/?electiva=si').status_code, status.HTTP_400_BAD_REQUEST)


class SincronizarMateriasComandoTests(ApiTestCase):
    PLAN = {"nombre": "Ingeniería en Sistemas de Información", "materias": [
        {"idMateria": "5-2023-101", "nombre": "Análisis Matemático I", "nivel": 1},
        {"idMateria": "5-2023-212", "nombre": "Entornos Gráficos (Elec.)", "nivel": 2},
    ]}

    @patch(PARCHE_SYSACAD)
    def test_importa_el_plan_y_cuenta_las_electivas(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: self.PLAN)
        salida = io.StringIO()

        call_command('sincronizar_materias', stdout=salida)

        self.assertIn('2 materias importadas (1 del plan y 1 electivas)', salida.getvalue())
        self.assertTrue(Materia.objects.filter(id_sysacad='5-2023-212', electiva=True).exists())

    @patch(PARCHE_SYSACAD)
    def test_si_falta_no_consulta_sysacad_si_ya_hay_materias(self, mock_get):
        # El setUp ya creó materias de la especialidad ISI.
        call_command('sincronizar_materias', '--si-falta', stdout=io.StringIO())

        mock_get.assert_not_called()

    @patch(PARCHE_SYSACAD)
    def test_sysacad_caido_es_un_error_del_comando(self, mock_get):
        mock_get.side_effect = requests.ConnectionError('caído')

        with self.assertRaises(CommandError):
            call_command('sincronizar_materias', stdout=io.StringIO())


# ---------------------------------------------------------------- materiales

class MaterialApiTests(ApiTestCase):
    url = '/api/materiales/'

    def subir(self, archivo=None, **cambios):
        datos = {
            'materia_id': self.materia.id, 'titulo': 'Resumen U1', 'tipo': 'resumen', 'comentario': 'Unidad 1',
            'archivo': archivo or SimpleUploadedFile('apunte.pdf', b'%PDF-1.4 contenido', content_type='application/pdf'),
        }
        datos.update(cambios)
        return self.client.post(self.url, datos, format='multipart')

    def test_un_alumno_sube_un_material_que_queda_pendiente_a_su_nombre(self):
        self.como(self.alumno)

        response = self.subir()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['validacion'])
        self.assertEqual(response.data['usuario']['legajo'], self.alumno.legajo)
        self.assertTrue(response.data['archivo'].startswith('http://testserver/media/materiales/'))
        self.assertTrue(response.data['archivo'].endswith('.pdf'))
        material = Material.objects.get()
        self.assertEqual(material.alumno, self.alumno.alumno)
        self.assertTrue(os.path.exists(material.archivo.path))

    def test_no_se_puede_subir_material_a_nombre_de_otro_ni_auto_validarlo(self):
        self.como(self.alumno)

        response = self.subir(usuario_id=self.admin.legajo, usuario=self.admin.legajo, validacion='true')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        material = Material.objects.get()
        self.assertEqual(material.alumno, self.alumno.alumno)
        self.assertEqual(material.estado.nombre, 'pendiente')

    def test_el_archivo_es_obligatorio(self):
        self.como(self.alumno)

        response = self.client.post(
            self.url, {'materia_id': self.materia.id, 'titulo': 'Sin archivo', 'tipo': 'resumen'}, format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('archivo', response.data)
        self.assertEqual(Material.objects.count(), 0)

    def test_extensiones_peligrosas_son_rechazadas(self):
        self.como(self.alumno)

        for nombre in ('malo.html', 'malo.svg', 'malo.js', 'malo.exe', 'sin_extension'):
            response = self.subir(archivo=SimpleUploadedFile(nombre, b'contenido'))
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, nombre)
        self.assertEqual(Material.objects.count(), 0)

    def test_archivo_demasiado_grande(self):
        self.como(self.alumno)
        enorme = SimpleUploadedFile('enorme.pdf', b'0' * (TAMANO_MAXIMO_MB * 1024 * 1024 + 1))

        response = self.subir(archivo=enorme)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('archivo', response.data)

    def test_materia_inexistente_o_tipo_invalido_es_400(self):
        self.como(self.alumno)

        self.assertEqual(self.subir(materia_id=9999).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.subir(tipo='RESUMEN').status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Material.objects.count(), 0)

    def test_cada_uno_ve_los_validados_y_sus_propios_pendientes(self):
        validado = self.crear_material(autor=self.otro_alumno, validado=True, titulo='Validado')
        pendiente_ajeno = self.crear_material(autor=self.otro_alumno, titulo='Pendiente ajeno')
        pendiente_propio = self.crear_material(autor=self.alumno, titulo='Pendiente propio')

        def ids_que_ve(usuario):
            self.como(usuario)
            return {m['id'] for m in self.client.get(self.url).data}

        self.assertEqual(ids_que_ve(self.alumno), {validado.id, pendiente_propio.id})
        self.assertEqual(ids_que_ve(self.otro_alumno), {validado.id, pendiente_ajeno.id})
        self.assertEqual(ids_que_ve(self.admin), {validado.id, pendiente_ajeno.id, pendiente_propio.id})

    def test_un_material_pendiente_ajeno_no_se_puede_ver_por_su_id(self):
        pendiente = self.crear_material(autor=self.otro_alumno)
        self.como(self.alumno)

        self.assertEqual(self.client.get(f'{self.url}{pendiente.id}/').status_code, status.HTTP_404_NOT_FOUND)

    def test_filtro_por_materia(self):
        de_algoritmos = self.crear_material(validado=True, materia=self.materia)
        self.crear_material(validado=True, materia=self.otra_materia)
        self.como(self.alumno)

        response = self.client.get(self.url, {'materia': self.materia.id})

        self.assertEqual([m['id'] for m in response.data], [de_algoritmos.id])
        self.assertEqual(self.client.get(self.url, {'materia': 'abc'}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get(self.url, {'materia': 9999}).data, [])

    def test_las_consultas_a_la_base_no_crecen_con_la_cantidad_de_materiales(self):
        self.como(self.alumno)
        self.crear_material(validado=True)
        with CaptureQueriesContext(connection) as con_uno:
            self.client.get(self.url)

        for numero in range(5):
            material = self.crear_material(validado=True, titulo=f'Otro {numero}')
            Ponderacion.objects.create(material=material, alumno=self.otro_alumno.alumno, valor=4)
        with CaptureQueriesContext(connection) as con_seis:
            respuesta = self.client.get(self.url)

        self.assertEqual(len(respuesta.data), 6)
        self.assertEqual(len(con_seis), len(con_uno))

    def test_el_autor_edita_su_material_mientras_esta_pendiente(self):
        material = self.crear_material(autor=self.alumno)
        self.como(self.alumno)

        response = self.client.patch(f'{self.url}{material.id}/', {'titulo': 'Nuevo título'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        material.refresh_from_db()
        self.assertEqual(material.titulo, 'Nuevo título')

    def test_el_autor_no_puede_autovalidarse_editando(self):
        material = self.crear_material(autor=self.alumno)
        self.como(self.alumno)

        self.client.patch(f'{self.url}{material.id}/', {'validacion': True}, format='json')

        material.refresh_from_db()
        self.assertEqual(material.estado.nombre, 'pendiente')

    def test_un_material_validado_solo_lo_modifica_un_administrador(self):
        material = self.crear_material(autor=self.alumno, validado=True)

        self.como(self.alumno)
        self.assertEqual(self.client.patch(f'{self.url}{material.id}/', {'titulo': 'Cambiado'}, format='json').status_code, 403)

        self.como(self.otro_alumno)
        self.assertEqual(self.client.patch(f'{self.url}{material.id}/', {'titulo': 'Cambiado'}, format='json').status_code, 403)

        self.como(self.admin)
        self.assertEqual(self.client.patch(f'{self.url}{material.id}/', {'titulo': 'Cambiado'}, format='json').status_code, 200)

    def test_solo_el_autor_o_un_administrador_borra(self):
        material = self.crear_material(autor=self.alumno, validado=True)

        self.como(self.otro_alumno)
        self.assertEqual(self.client.delete(f'{self.url}{material.id}/').status_code, 403)

        self.como(self.alumno)
        self.assertEqual(self.client.delete(f'{self.url}{material.id}/').status_code, 204)


class ModeracionTests(ApiTestCase):
    def test_solo_el_administrador_ve_la_cola_de_pendientes(self):
        self.como(self.alumno)
        self.assertEqual(self.client.get('/api/materiales/pendientes/').status_code, status.HTTP_403_FORBIDDEN)
        self.como(self.tutor)
        self.assertEqual(self.client.get('/api/materiales/pendientes/').status_code, status.HTTP_403_FORBIDDEN)

    def test_la_cola_tiene_solo_pendientes_los_mas_viejos_primero(self):
        primero = self.crear_material(titulo='Primero')
        segundo = self.crear_material(titulo='Segundo')
        self.crear_material(titulo='Ya validado', validado=True)
        self.como(self.admin)

        response = self.client.get('/api/materiales/pendientes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([m['id'] for m in response.data], [primero.id, segundo.id])

    def test_aprobar_hace_visible_el_material_para_todos(self):
        material = self.crear_material(autor=self.alumno)
        self.como(self.otro_alumno)
        self.assertEqual(self.client.get(f'/api/materiales/{material.id}/').status_code, 404)

        self.como(self.admin)
        response = self.client.post(f'/api/materiales/{material.id}/moderar/', {'accion': 'aprobar'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['validacion'])
        self.como(self.otro_alumno)
        self.assertEqual(self.client.get(f'/api/materiales/{material.id}/').status_code, 200)

    def test_rechazar_conserva_el_material_y_guarda_el_motivo(self):
        material = self.crear_material(autor=self.alumno)
        ruta = material.archivo.path
        self.como(self.admin)

        response = self.client.post(
            f'/api/materiales/{material.id}/moderar/', {'accion': 'rechazar', 'motivo': 'Ilegible'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        material.refresh_from_db()
        self.assertEqual(material.estado.nombre, 'rechazado')
        self.assertEqual(material.motivo_rechazo, 'Ilegible')
        self.assertTrue(os.path.exists(ruta))
        self.assertFalse(response.data['validacion'])
        self.como(self.otro_alumno)
        self.assertEqual(self.client.get(f'/api/materiales/{material.id}/').status_code, 404)

    def test_al_rechazar_el_alumno_recibe_una_notificacion_con_el_motivo(self):
        material = self.crear_material(autor=self.alumno, titulo='Resumen Unidad 2')
        self.como(self.admin)

        self.client.post(f'/api/materiales/{material.id}/moderar/', {'accion': 'rechazar', 'motivo': 'Ilegible'}, format='json')

        aviso = Notificacion.objects.get()
        self.assertEqual(aviso.alumno_id, self.alumno.legajo)
        self.assertEqual(aviso.tipo, Notificacion.RECHAZO)
        self.assertIsNone(aviso.clase)
        self.assertIn('Resumen Unidad 2', aviso.titulo)
        self.assertIn('Ilegible', aviso.texto)
        self.assertIn('corregirlo', aviso.texto)

        # el alumno la ve en la campanita; los demás no
        self.como(self.alumno)
        lista = self.client.get('/api/notificaciones/').data
        self.assertEqual([n['tipo'] for n in lista], ['rechazo'])
        self.como(self.otro_alumno)
        self.assertEqual(self.client.get('/api/notificaciones/').data, [])

    def test_el_autor_reemplaza_el_archivo_de_un_material_rechazado_y_reenvia(self):
        material = self.crear_material(autor=self.alumno)
        archivo_viejo = material.archivo.path
        self.como(self.admin)
        self.client.post(f'/api/materiales/{material.id}/moderar/', {'accion': 'rechazar', 'motivo': 'Ilegible'}, format='json')

        self.como(self.alumno)
        nuevo = SimpleUploadedFile('corregido.pdf', b'%PDF-1.4 version corregida', content_type='application/pdf')
        response = self.client.patch(f'/api/materiales/{material.id}/', {'titulo': 'Resumen corregido', 'archivo': nuevo}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        material.refresh_from_db()
        self.assertEqual(material.estado.nombre, 'pendiente')
        self.assertIsNone(material.motivo_rechazo)
        self.assertEqual(material.titulo, 'Resumen corregido')
        self.assertTrue(response.data['archivo'])  # la respuesta trae el archivo nuevo
        self.assertTrue(os.path.exists(material.archivo.path))
        self.assertFalse(os.path.exists(archivo_viejo))  # el anterior no queda huérfano en el disco

    def test_editar_sin_cambiar_el_archivo_lo_conserva(self):
        material = self.crear_material(autor=self.alumno)
        ruta = material.archivo.path
        self.como(self.alumno)

        response = self.client.patch(f'/api/materiales/{material.id}/', {'comentario': 'Con ejercicios'}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(os.path.exists(ruta))

    def test_aprobar_o_archivar_no_generan_notificacion_de_rechazo(self):
        pendiente = self.crear_material(autor=self.alumno)
        self.como(self.admin)
        self.client.post(f'/api/materiales/{pendiente.id}/moderar/', {'accion': 'aprobar'}, format='json')
        self.client.post(f'/api/materiales/{pendiente.id}/moderar/', {'accion': 'archivar'}, format='json')

        self.assertEqual(Notificacion.objects.count(), 0)

    def test_el_autor_corrige_un_material_rechazado_y_vuelve_a_pendiente(self):
        material = self.crear_material(autor=self.alumno)
        self.como(self.admin)
        self.client.post(f'/api/materiales/{material.id}/moderar/', {'accion': 'rechazar', 'motivo': 'Ilegible'}, format='json')

        self.como(self.alumno)
        response = self.client.patch(f'/api/materiales/{material.id}/', {'titulo': 'Corregido'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        material.refresh_from_db()
        self.assertEqual(material.estado.nombre, 'pendiente')
        self.assertIsNone(material.motivo_rechazo)

    def test_archivar_solo_desde_aprobado_y_no_se_puede_puntuar(self):
        pendiente = self.crear_material(autor=self.alumno)
        aprobado = self.crear_material(autor=self.alumno, validado=True, titulo='Aprobado')
        self.como(self.admin)

        response = self.client.post(f'/api/materiales/{pendiente.id}/moderar/', {'accion': 'archivar'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        response = self.client.post(f'/api/materiales/{aprobado.id}/moderar/', {'accion': 'archivar'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        aprobado.refresh_from_db()
        self.assertEqual(aprobado.estado.nombre, 'archivado')

        self.como(self.otro_alumno)
        response = self.client.post('/api/ponderaciones/', {'material_id': aprobado.id, 'valor': 4}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_la_media_se_guarda_en_el_material_al_puntuar(self):
        material = self.crear_material(autor=self.alumno, validado=True)
        segundo_alumno = self.crear_usuario('6')
        for usuario, valor in ((self.otro_alumno, 5), (segundo_alumno, 2)):
            self.como(usuario)
            self.client.post('/api/ponderaciones/', {'material_id': material.id, 'valor': valor}, format='json')

        material.refresh_from_db()
        self.assertEqual(material.cantidad_ponderaciones, 2)
        self.assertEqual(float(material.promedio_ponderacion), 3.5)

        self.como(segundo_alumno)
        ponderacion = Ponderacion.objects.get(material=material, alumno=segundo_alumno.alumno)
        self.client.delete(f'/api/ponderaciones/{ponderacion.id}/')
        material.refresh_from_db()
        self.assertEqual(material.cantidad_ponderaciones, 1)
        self.assertEqual(float(material.promedio_ponderacion), 5.0)

    def test_solo_el_administrador_puede_moderar(self):
        material = self.crear_material(autor=self.alumno)

        for usuario in (self.alumno, self.otro_alumno, self.tutor):
            self.como(usuario)
            response = self.client.post(f'/api/materiales/{material.id}/moderar/', {'accion': 'aprobar'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, usuario.rol.nombre)

        material.refresh_from_db()
        self.assertEqual(material.estado.nombre, 'pendiente')

    def test_accion_invalida_o_material_inexistente(self):
        material = self.crear_material()
        self.como(self.admin)

        self.assertEqual(self.client.post(f'/api/materiales/{material.id}/moderar/', {'accion': 'borrar'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(f'/api/materiales/{material.id}/moderar/', {}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/materiales/9999/moderar/', {'accion': 'aprobar'}, format='json').status_code, 404)
        self.assertTrue(Material.objects.filter(pk=material.pk).exists())


# ---------------------------------------------------------------- clases de apoyo

class ClaseApoyoApiTests(ApiTestCase):
    url = '/api/clases-apoyo/'

    def datos(self, **cambios):
        datos = {'materia_id': self.materia.id, 'dia': 1, 'hora_inicio': '14:00', 'hora_fin': '16:00', 'aula': 'L-203'}
        datos.update(cambios)
        return datos

    def crear_clase(self, tutor=None, materia=None):
        return ClaseApoyo.objects.create(
            materia=materia or self.materia, tutor=(tutor or self.tutor).tutor,
            dia=1, hora_inicio=datetime.time(14), hora_fin=datetime.time(16), aula='L-203',
        )

    def test_un_tutor_crea_una_clase_siempre_a_su_nombre(self):
        self.como(self.tutor)

        # aunque intente ponerla a nombre de otro tutor, queda a su nombre
        response = self.client.post(self.url, self.datos(tutor_id=self.otro_tutor.legajo), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['tutor']['legajo'], self.tutor.legajo)
        self.assertEqual(ClaseApoyo.objects.get().tutor.usuario, self.tutor)

    def test_un_alumno_no_puede_crear_clases(self):
        self.como(self.alumno)

        self.assertEqual(self.client.post(self.url, self.datos(), format='json').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ClaseApoyo.objects.count(), 0)

    def test_el_administrador_tiene_que_indicar_un_tutor_valido(self):
        self.como(self.admin)

        self.assertEqual(self.client.post(self.url, self.datos(), format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, self.datos(tutor_id=self.alumno.legajo), format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, self.datos(tutor_id='no-existe'), format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, self.datos(tutor_id=self.tutor.legajo), format='json').status_code, 201)

    def test_materia_inexistente_es_400(self):
        self.como(self.tutor)

        self.assertEqual(self.client.post(self.url, self.datos(materia_id=9999), format='json').status_code, 400)

    def test_todos_los_logueados_ven_las_clases_y_se_filtran_por_materia(self):
        de_algoritmos = self.crear_clase(materia=self.materia)
        self.crear_clase(materia=self.otra_materia)
        self.como(self.alumno)

        self.assertEqual(len(self.client.get(self.url).data), 2)
        self.assertEqual([c['id'] for c in self.client.get(self.url, {'materia': self.materia.id}).data], [de_algoritmos.id])
        self.assertEqual(self.client.get(self.url, {'materia': 'x'}).status_code, 400)

    def test_solo_su_tutor_o_un_administrador_modifica_o_borra(self):
        clase = self.crear_clase(tutor=self.tutor)
        detalle = f'{self.url}{clase.id}/'

        self.como(self.otro_tutor)
        self.assertEqual(self.client.patch(detalle, {'aula': 'X-1'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(detalle).status_code, 403)

        self.como(self.alumno)
        self.assertEqual(self.client.patch(detalle, {'aula': 'X-1'}, format='json').status_code, 403)

        self.como(self.tutor)
        self.assertEqual(self.client.patch(detalle, {'aula': 'X-1'}, format='json').status_code, 200)

        self.como(self.admin)
        self.assertEqual(self.client.delete(detalle).status_code, 204)

    def test_un_tutor_no_puede_regalar_su_clase_a_otro_tutor(self):
        clase = self.crear_clase(tutor=self.tutor)
        self.como(self.tutor)

        self.client.patch(f'{self.url}{clase.id}/', {'tutor_id': self.otro_tutor.legajo}, format='json')

        clase.refresh_from_db()
        self.assertEqual(clase.tutor.usuario, self.tutor)


# ---------------------------------------------------------------- ponderaciones (estrellas)

class PonderacionTests(ApiTestCase):
    """Sistema de estrellas: cada usuario puntúa un material de 1 a 5 y la nota del material es el promedio."""
    url = '/api/ponderaciones/'

    def setUp(self):
        super().setUp()
        self.material = self.crear_material(autor=self.alumno, validado=True)

    def puntuar(self, valor, material=None, **extra):
        return self.client.post(self.url, {'material_id': (material or self.material).id, 'valor': valor, **extra}, format='json')

    def material_actual(self):
        return self.client.get(f'/api/materiales/{self.material.id}/').data

    def test_material_sin_ponderaciones(self):
        self.como(self.otro_alumno)

        datos = self.material_actual()

        self.assertIsNone(datos['promedio_ponderacion'])
        self.assertEqual(datos['cantidad_ponderaciones'], 0)

    def test_puntuar_material(self):
        self.como(self.otro_alumno)

        response = self.puntuar(4)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ponderacion.objects.get().alumno, self.otro_alumno.alumno)

    def test_promedio_de_varias_ponderaciones(self):
        self.como(self.otro_alumno)
        self.puntuar(5)
        self.como(self.crear_usuario('6'))
        self.puntuar(2)

        datos = self.material_actual()

        self.assertEqual(datos['promedio_ponderacion'], 3.5)
        self.assertEqual(datos['cantidad_ponderaciones'], 2)

    def test_puntuar_de_nuevo_actualiza_el_voto_anterior(self):
        self.como(self.otro_alumno)
        self.puntuar(5)
        self.puntuar(1)

        datos = self.material_actual()

        self.assertEqual(Ponderacion.objects.count(), 1)
        self.assertEqual(datos['promedio_ponderacion'], 1.0)
        self.assertEqual(datos['cantidad_ponderaciones'], 1)

    def test_valor_fuera_de_rango_es_rechazado(self):
        self.como(self.otro_alumno)

        for valor in (0, 6, -1):
            self.assertEqual(self.puntuar(valor).status_code, status.HTTP_400_BAD_REQUEST, f"valor={valor}")
        self.assertEqual(Ponderacion.objects.count(), 0)

    def test_material_inexistente(self):
        self.como(self.otro_alumno)

        response = self.client.post(self.url, {'material_id': 9999, 'valor': 3}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('material_id', response.data)

    def test_no_se_puede_puntuar_a_nombre_de_otro_usuario(self):
        self.como(self.otro_alumno)

        self.puntuar(5, usuario_id=self.admin.legajo, usuario=self.admin.legajo)

        self.assertEqual(Ponderacion.objects.get().alumno, self.otro_alumno.alumno)

    def test_no_se_puede_puntuar_el_propio_material(self):
        self.como(self.alumno)  # es el autor

        response = self.puntuar(5)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Ponderacion.objects.count(), 0)

    def test_no_se_puede_puntuar_un_material_pendiente(self):
        pendiente = self.crear_material(autor=self.alumno, validado=False, titulo='Pendiente')
        self.como(self.otro_alumno)

        response = self.puntuar(5, material=pendiente)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cada_usuario_ve_solo_sus_ponderaciones_y_puede_filtrar_por_material(self):
        otro_material = self.crear_material(autor=self.alumno, validado=True, titulo='Otro')
        Ponderacion.objects.create(material=self.material, alumno=self.otro_alumno.alumno, valor=5)
        Ponderacion.objects.create(material=otro_material, alumno=self.otro_alumno.alumno, valor=3)
        Ponderacion.objects.create(material=self.material, alumno=self.crear_usuario('6').alumno, valor=1)

        self.como(self.otro_alumno)
        self.assertEqual(len(self.client.get(self.url).data), 2)
        filtradas = self.client.get(self.url, {'material': self.material.id}).data
        self.assertEqual([p['valor'] for p in filtradas], [5])
        self.assertEqual(self.client.get(self.url, {'material': 'x'}).status_code, 400)

        self.como(self.admin)
        self.assertEqual(len(self.client.get(self.url).data), 3)

    def test_solo_el_dueno_o_un_administrador_toca_una_ponderacion(self):
        ponderacion = Ponderacion.objects.create(material=self.material, alumno=self.otro_alumno.alumno, valor=5)
        detalle = f'{self.url}{ponderacion.id}/'

        self.como(self.tutor)
        self.assertEqual(self.client.get(detalle).status_code, 404)
        self.assertEqual(self.client.patch(detalle, {'valor': 1}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(detalle).status_code, 404)

        self.como(self.otro_alumno)
        self.assertEqual(self.client.patch(detalle, {'valor': 2}, format='json').status_code, 200)
        ponderacion.refresh_from_db()
        self.assertEqual(ponderacion.valor, 2)

        self.como(self.admin)
        self.assertEqual(self.client.delete(detalle).status_code, 204)

    def test_editar_una_ponderacion_solo_cambia_las_estrellas(self):
        otro_material = self.crear_material(autor=self.alumno, validado=True, titulo='Otro')
        ponderacion = Ponderacion.objects.create(material=self.material, alumno=self.otro_alumno.alumno, valor=5)
        self.como(self.otro_alumno)

        response = self.client.put(
            f'{self.url}{ponderacion.id}/', {'material_id': otro_material.id, 'valor': 2, 'usuario_id': self.admin.legajo}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ponderacion.refresh_from_db()
        self.assertEqual((ponderacion.material, ponderacion.alumno, ponderacion.valor), (self.material, self.otro_alumno.alumno, 2))

    def test_la_restriccion_de_la_base_impide_dos_votos_del_mismo_usuario(self):
        from django.db import IntegrityError, transaction

        Ponderacion.objects.create(material=self.material, alumno=self.otro_alumno.alumno, valor=5)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Ponderacion.objects.create(material=self.material, alumno=self.otro_alumno.alumno, valor=1)


# ---------------------------------------------------------------- suscripciones y avisos (patrón Observer)

class SuscripcionYAvisosTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.clase = ClaseApoyo.objects.create(
            materia=self.materia, tutor=self.tutor.tutor, dia=1, hora_inicio=datetime.time(14), hora_fin=datetime.time(16), aula='L-203',
        )
        self.url_clase = f'/api/clases-apoyo/{self.clase.id}/'

    def suscribir(self, usuario):
        self.como(usuario)
        return self.client.post(f'{self.url_clase}suscripcion/')

    def notificaciones(self, usuario):
        return list(Notificacion.objects.filter(alumno_id=usuario.pk))

    def test_un_alumno_se_suscribe_y_la_clase_lo_refleja(self):
        response = self.suscribir(self.alumno)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'suscrito': True, 'cantidad_suscritos': 1})
        clase = self.client.get('/api/clases-apoyo/').data[0]
        self.assertTrue(clase['suscrito'])
        self.assertEqual(clase['cantidad_suscritos'], 1)

        self.como(self.otro_alumno)
        clase = self.client.get('/api/clases-apoyo/').data[0]
        self.assertFalse(clase['suscrito'])  # cada uno ve si ÉL está suscrito
        self.assertEqual(clase['cantidad_suscritos'], 1)

    def test_suscribirse_dos_veces_no_duplica(self):
        self.suscribir(self.alumno)
        response = self.suscribir(self.alumno)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Suscripcion.objects.count(), 1)

    def test_solo_los_alumnos_se_suscriben(self):
        for usuario in (self.tutor, self.otro_tutor, self.admin):
            self.assertEqual(self.suscribir(usuario).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Suscripcion.objects.count(), 0)

    def test_dejar_de_seguir_una_clase(self):
        self.suscribir(self.alumno)

        response = self.client.delete(f'{self.url_clase}suscripcion/')

        self.assertEqual(response.data, {'suscrito': False, 'cantidad_suscritos': 0})
        self.assertEqual(Suscripcion.objects.count(), 0)

    def test_suscribirse_a_una_clase_inexistente_es_404(self):
        self.como(self.alumno)
        self.assertEqual(self.client.post('/api/clases-apoyo/999/suscripcion/').status_code, status.HTTP_404_NOT_FOUND)

    def test_modificar_la_clase_avisa_solo_a_los_suscritos_con_lo_que_cambio(self):
        self.suscribir(self.alumno)
        self.como(self.tutor)

        response = self.client.patch(
            self.url_clase, {'dia': 2, 'hora_inicio': '16:00', 'hora_fin': '18:00', 'aula': 'L-105'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        [aviso] = self.notificaciones(self.alumno)
        self.assertEqual(aviso.tipo, Notificacion.MODIFICACION)
        self.assertEqual(aviso.titulo, 'Cambió la clase de apoyo de Algoritmos')
        self.assertEqual(aviso.texto, 'Día y horario: lunes de 14:00 a 16:00 → martes de 16:00 a 18:00. Aula: L-203 → L-105.')
        self.assertEqual(self.notificaciones(self.otro_alumno), [])

    def test_cambiar_de_materia_tambien_se_avisa(self):
        self.suscribir(self.alumno)
        self.como(self.tutor)

        self.client.patch(self.url_clase, {'materia_id': self.otra_materia.id}, format='json')

        self.assertEqual(self.notificaciones(self.alumno)[0].texto, 'Materia: Algoritmos → Física.')

    def test_guardar_sin_cambios_no_avisa(self):
        self.suscribir(self.alumno)
        self.como(self.tutor)

        self.client.patch(self.url_clase, {'hora_inicio': '14:00'}, format='json')

        self.assertEqual(self.notificaciones(self.alumno), [])

    def test_cancelar_la_clase_avisa_y_el_aviso_queda_aunque_la_clase_se_borre(self):
        self.suscribir(self.alumno)
        self.como(self.tutor)

        self.assertEqual(self.client.delete(self.url_clase).status_code, status.HTTP_204_NO_CONTENT)

        [aviso] = self.notificaciones(self.alumno)
        self.assertEqual(aviso.tipo, Notificacion.CANCELACION)
        self.assertIsNone(aviso.clase)
        self.assertEqual(aviso.texto, 'La clase del lunes de 14:00 a 16:00 en el aula L-203 ya no se dicta.')
        self.assertEqual(Suscripcion.objects.count(), 0)

    def test_el_tutor_manda_un_mensaje_y_les_llega_a_los_suscritos(self):
        self.suscribir(self.alumno)
        self.suscribir(self.otro_alumno)
        self.como(self.tutor)

        response = self.client.post(f'{self.url_clase}mensajes/', {'texto': '  Traigan la guía 3  '}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['texto'], 'Traigan la guía 3')
        self.assertEqual(response.data['autor']['legajo'], self.tutor.legajo)
        for alumno in (self.alumno, self.otro_alumno):
            [aviso] = self.notificaciones(alumno)
            self.assertEqual(aviso.tipo, Notificacion.MENSAJE)
            self.assertEqual(aviso.texto, 'Traigan la guía 3')

    def test_solo_el_tutor_de_la_clase_manda_mensajes(self):
        self.suscribir(self.alumno)
        for usuario in (self.alumno, self.otro_tutor, self.admin):
            self.como(usuario)
            response = self.client.post(f'{self.url_clase}mensajes/', {'texto': 'Hola'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.como(self.tutor)
        response = self.client.post(f'{self.url_clase}mensajes/', {'texto': 'Hola'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['autor']['legajo'], self.tutor.legajo)

    def test_un_mensaje_vacio_es_400(self):
        self.como(self.tutor)
        self.assertEqual(self.client.post(f'{self.url_clase}mensajes/', {'texto': '   '}, format='json').status_code, 400)

    def test_los_mensajes_los_ven_los_suscritos_y_el_tutor_pero_no_los_demas(self):
        MensajeClase.objects.create(clase=self.clase, tutor=self.tutor.tutor, texto='Primero')
        MensajeClase.objects.create(clase=self.clase, tutor=self.tutor.tutor, texto='Segundo')
        url = f'{self.url_clase}mensajes/'

        self.como(self.alumno)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

        self.suscribir(self.alumno)
        self.assertEqual([m['texto'] for m in self.client.get(url).data], ['Segundo', 'Primero'])

        self.como(self.tutor)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

    def test_cada_uno_ve_sus_notificaciones_y_las_marca_como_leidas(self):
        self.suscribir(self.alumno)
        self.como(self.tutor)
        self.client.post(f'{self.url_clase}mensajes/', {'texto': 'Hola'}, format='json')

        self.como(self.otro_alumno)
        self.assertEqual(self.client.get('/api/notificaciones/').data, [])

        self.como(self.alumno)
        [aviso] = self.client.get('/api/notificaciones/').data
        self.assertFalse(aviso['leida'])
        self.assertEqual(aviso['clase'], self.clase.id)

        self.assertEqual(self.client.post('/api/notificaciones/marcar-leidas/').data, {'marcadas': 1})
        self.assertTrue(self.client.get('/api/notificaciones/').data[0]['leida'])

    def test_el_sujeto_avisa_a_cada_observador(self):
        """El patrón en sí, sin pasar por la API: el sujeto llama a actualizar() de cada observador."""
        recibidos = []

        class ObservadorDePrueba(ObservadorClase):
            def __init__(self, nombre):
                self.nombre = nombre

            def actualizar(self, evento):
                recibidos.append((self.nombre, evento.titulo))

        sujeto = SujetoClase(self.clase)
        sujeto.observadores = lambda: [ObservadorDePrueba('a'), ObservadorDePrueba('b')]

        avisados = sujeto.notificar(EventoClase(Notificacion.MENSAJE, self.clase, 'Hola', 'texto'))

        self.assertEqual(avisados, 2)
        self.assertEqual(recibidos, [('a', 'Hola'), ('b', 'Hola')])


# ---------------------------------------------------------------- día y horario de las clases de apoyo

# ---------------------------------------------------------------- alumnos, tutores y administradores

class SubtiposDeUsuarioTests(ApiTestCase):
    """Cada usuario tiene una fila en la tabla de su rol (alumnos, tutores o administradores), con el legajo como clave."""

    def test_cada_usuario_tiene_su_fila_segun_el_rol(self):
        self.assertTrue(Alumno.objects.filter(pk=self.alumno.legajo).exists())
        self.assertTrue(Tutor.objects.filter(pk=self.tutor.legajo).exists())
        self.assertTrue(Administrador.objects.filter(pk=self.admin.legajo).exists())
        # y solo en la suya
        self.assertFalse(Tutor.objects.filter(pk=self.alumno.legajo).exists())
        self.assertFalse(Alumno.objects.filter(pk=self.admin.legajo).exists())
        self.assertFalse(Administrador.objects.filter(pk=self.tutor.legajo).exists())

    def test_el_administrador_da_de_alta_un_tutor_por_la_api_y_queda_en_la_tabla_de_tutores(self):
        self.como(self.admin)
        response = self.client.post('/api/usuarios/', {
            'legajo': '150', 'nombre_y_apellido': 'Tomás Tutor', 'correo': 'tomas@utn.edu.ar', 'rol': 'tutor',
            'contraseña': CONTRASENA,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Tutor.objects.filter(pk='150').exists())
        self.assertFalse(Alumno.objects.filter(pk='150').exists())

    def test_cambiar_el_rol_mueve_la_fila_a_la_otra_tabla(self):
        nuevo = self.crear_usuario('7')
        self.assertTrue(Alumno.objects.filter(pk='7').exists())

        nuevo.rol = Rol.objects.get(nombre='tutor')
        nuevo.save()

        self.assertTrue(Tutor.objects.filter(pk='7').exists())
        self.assertFalse(Alumno.objects.filter(pk='7').exists())

    def test_si_ya_tiene_registros_la_fila_anterior_se_conserva(self):
        material = self.crear_material(autor=self.alumno)

        self.alumno.rol = Rol.objects.get(nombre='tutor')
        self.alumno.save()

        self.assertTrue(Tutor.objects.filter(pk=self.alumno.legajo).exists())
        self.assertTrue(Alumno.objects.filter(pk=self.alumno.legajo).exists())  # tiene un material: no se pierde
        material.refresh_from_db()

    def test_la_clase_solo_puede_ser_de_un_tutor(self):
        self.como(self.admin)
        response = self.client.post('/api/clases-apoyo/', {
            'materia_id': self.materia.id, 'dia': 1, 'hora_inicio': '14:00', 'hora_fin': '16:00', 'aula': 'L-1',
            'tutor_id': self.alumno.legajo,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tutor_id', response.data)

    def test_solo_los_alumnos_suben_materiales(self):
        for usuario in (self.tutor, self.admin):
            self.como(usuario)
            response = self.client.post('/api/materiales/', {
                'materia_id': self.materia.id, 'titulo': 'X', 'tipo': 'resumen',
                'archivo': SimpleUploadedFile('a.pdf', b'%PDF-1.4 x', content_type='application/pdf'),
            }, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, usuario.rol.nombre)
        self.assertEqual(Material.objects.count(), 0)

    def test_solo_los_alumnos_puntuan(self):
        material = self.crear_material(autor=self.alumno, validado=True)
        for usuario in (self.tutor, self.admin):
            self.como(usuario)
            response = self.client.post('/api/ponderaciones/', {'material_id': material.id, 'valor': 4}, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, usuario.rol.nombre)

        self.como(self.otro_alumno)
        response = self.client.post('/api/ponderaciones/', {'material_id': material.id, 'valor': 4}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class HorarioClaseApoyoTests(ApiTestCase):
    url = '/api/clases-apoyo/'

    def datos(self, **cambios):
        datos = {'materia_id': self.materia.id, 'dia': 1, 'hora_inicio': '14:00', 'hora_fin': '16:00', 'aula': 'L-203'}
        datos.update(cambios)
        return {clave: valor for clave, valor in datos.items() if valor is not None}

    def publicar(self, usuario=None, **cambios):
        self.como(usuario or self.tutor)
        return self.client.post(self.url, self.datos(**cambios), format='json')

    def test_se_guarda_dia_y_horas_y_se_devuelve_tambien_el_texto(self):
        response = self.publicar()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            {campo: response.data[campo] for campo in ('dia', 'hora_inicio', 'hora_fin', 'horario')},
            {'dia': 1, 'hora_inicio': '14:00', 'hora_fin': '16:00', 'horario': 'lunes de 14:00 a 16:00'},
        )
        clase = ClaseApoyo.objects.get()
        self.assertEqual((clase.dia, clase.hora_inicio, clase.hora_fin), (1, datetime.time(14), datetime.time(16)))

    def test_dia_y_horas_son_obligatorios(self):
        response = self.publicar(dia=None, hora_inicio=None, hora_fin=None)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {'dia', 'hora_inicio', 'hora_fin'})

    def test_formatos_invalidos(self):
        casos = [
            ({'hora_inicio': '2pm'}, 'hora_inicio', 'Usá el formato HH:MM (por ejemplo 14:00).'),
            ({'hora_fin': 'por la tarde'}, 'hora_fin', 'Usá el formato HH:MM (por ejemplo 16:00).'),
            ({'dia': 7}, 'dia', 'Elegí un día de lunes a sábado.'),
            ({'dia': 'lunes'}, 'dia', 'Elegí un día de lunes a sábado.'),
        ]
        for cambios, campo, mensaje in casos:
            with self.subTest(cambios=cambios):
                response = self.publicar(**cambios)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(str(response.data[campo][0]), mensaje)
        self.assertEqual(ClaseApoyo.objects.count(), 0)

    def test_el_fin_tiene_que_ser_despues_del_inicio_y_durar_al_menos_media_hora(self):
        antes = self.publicar(hora_inicio='16:00', hora_fin='14:00')
        corta = self.publicar(hora_inicio='14:00', hora_fin='14:15')

        self.assertEqual(str(antes.data['hora_fin'][0]), 'Tiene que ser posterior a la hora de inicio.')
        self.assertEqual(str(corta.data['hora_fin'][0]), 'La clase tiene que durar al menos 30 minutos.')

    def test_tiene_que_estar_en_el_horario_de_la_facultad(self):
        response = self.publicar(hora_inicio='06:00', hora_fin='08:00')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data['hora_inicio'][0]), 'Tiene que estar entre las 09:00 y 23:30.')

    def test_un_tutor_no_puede_tener_dos_clases_superpuestas(self):
        self.publicar()

        superpuesta = self.publicar(hora_inicio='15:00', hora_fin='17:00')
        a_continuacion = self.publicar(hora_inicio='16:00', hora_fin='18:00')
        otro_dia = self.publicar(dia=2)
        otro_tutor = self.publicar(self.otro_tutor)

        self.assertEqual(superpuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Se superpone con otra clase del mismo tutor: Algoritmos, lunes de 14:00 a 16:00.', str(superpuesta.data['hora_inicio'][0]))
        for response in (a_continuacion, otro_dia, otro_tutor):
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_modificar_una_clase_no_choca_consigo_misma(self):
        clase_id = self.publicar().data['id']

        response = self.client.patch(f'{self.url}{clase_id}/', {'hora_fin': '17:00'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['horario'], 'lunes de 14:00 a 17:00')

    def test_una_clase_vieja_sin_horario_queda_a_confirmar_y_hay_que_completarlo_al_modificarla(self):
        clase = ClaseApoyo.objects.create(materia=self.materia, tutor=self.tutor.tutor, aula='L-203')
        self.como(self.tutor)

        self.assertEqual(self.client.get(self.url).data[0]['horario'], 'a confirmar')
        solo_aula = self.client.patch(f'{self.url}{clase.id}/', {'aula': 'L-105'}, format='json')
        completa = self.client.patch(f'{self.url}{clase.id}/', {'dia': 3, 'hora_inicio': '18:00', 'hora_fin': '20:00'}, format='json')

        self.assertEqual(solo_aula.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(solo_aula.data), {'dia', 'hora_inicio', 'hora_fin'})
        self.assertEqual(completa.data['horario'], 'miércoles de 18:00 a 20:00')

    def test_el_cronograma_viene_ordenado_por_dia_y_hora(self):
        self.publicar(dia=3, hora_inicio='10:00', hora_fin='12:00')
        self.publicar(dia=1, hora_inicio='18:00', hora_fin='20:00')
        self.publicar(dia=1, hora_inicio='09:00', hora_fin='11:00')

        horarios = [c['horario'] for c in self.client.get(self.url).data]

        self.assertEqual(horarios, ['lunes de 09:00 a 11:00', 'lunes de 18:00 a 20:00', 'miércoles de 10:00 a 12:00'])


class MigracionHorarioTests(TestCase):
    """La conversión de los horarios viejos (texto libre) que hace la migración 0008."""

    def test_interpreta_los_formatos_habituales_y_deja_a_confirmar_el_resto(self):
        interpretar = import_module('core.migrations.0008_clase_apoyo_dia_y_horas').interpretar
        t = datetime.time
        casos = {
            'Lun 14:00-16:00': (1, t(14), t(16)),
            'Miércoles 18 a 20hs': (3, t(18), t(20)),
            'mie 9.30-11': (3, t(9, 30), t(11)),
            'SÁB 10hs - 12hs': (6, t(10), t(12)),
            'Lunes 14hs': (1, t(14), None),
            'por la tarde': (None, None, None),
            'Vie 16-14': (5, t(16), None),
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(interpretar(texto), esperado)
