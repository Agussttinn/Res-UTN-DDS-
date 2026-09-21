import datetime
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
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APITestCase

from . import sysacad_client
from .admin import UsuarioAdmin
from .archivos import TAMANO_MAXIMO_MB
from .auth import crear_token
from .models import ClaseApoyo, Especialidad, Materia, Material, Ponderacion, Usuario

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
            contraseña=make_password(contrasena), rol=rol,
        )

    def como(self, usuario):
        """Los próximos requests los hace `usuario` (equivale a mandar su token)."""
        self.client.force_authenticate(user=usuario)

    def crear_material(self, autor=None, validado=False, materia=None, titulo='Resumen U1'):
        return Material.objects.create(
            materia=materia or self.materia, usuario=autor or self.alumno, titulo=titulo,
            tipo='resumen', validacion=validado,
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
        self.assertEqual(usuario.rol, "alumno")
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

        Usuario.objects.filter(pk=self.admin.pk).update(rol='alumno')  # le sacan el rol de administrador

        self.assertEqual(self.client.get('/api/usuarios/', HTTP_AUTHORIZATION=f'Bearer {token}').status_code, 403)


# ---------------------------------------------------------------- usuarios, especialidades, materias

class PermisosGeneralesTests(ApiTestCase):
    def test_ningun_recurso_es_publico_salvo_login_y_registro(self):
        rutas = [
            '/api/usuarios/', '/api/usuarios/4/', '/api/especialidades/', '/api/materias/',
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
        self.assertEqual(tutor.rol, 'tutor')
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
        self.assertEqual(self.alumno.rol, 'alumno')

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
        usuario = Usuario(legajo='88', nombre_y_apellido='A', correo='a88@mail.com', rol='administrador', contraseña='texto-plano')

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
        self.assertEqual(self.client.post('/api/materias/sincronizar/XXX/').status_code, status.HTTP_404_NOT_FOUND)


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
        self.assertEqual(material.usuario, self.alumno)
        self.assertTrue(os.path.exists(material.archivo.path))

    def test_no_se_puede_subir_material_a_nombre_de_otro_ni_auto_validarlo(self):
        self.como(self.alumno)

        response = self.subir(usuario_id=self.admin.legajo, usuario=self.admin.legajo, validacion='true')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        material = Material.objects.get()
        self.assertEqual(material.usuario, self.alumno)
        self.assertFalse(material.validacion)

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
            Ponderacion.objects.create(material=material, usuario=self.otro_alumno, valor=4)
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
        self.assertFalse(material.validacion)

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

    def test_rechazar_elimina_el_material_y_su_archivo(self):
        material = self.crear_material(autor=self.alumno)
        ruta = material.archivo.path
        self.assertTrue(os.path.exists(ruta))
        self.como(self.admin)

        response = self.client.post(f'/api/materiales/{material.id}/moderar/', {'accion': 'rechazar'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Material.objects.filter(pk=material.pk).exists())
        self.assertFalse(os.path.exists(ruta))

    def test_solo_el_administrador_puede_moderar(self):
        material = self.crear_material(autor=self.alumno)

        for usuario in (self.alumno, self.otro_alumno, self.tutor):
            self.como(usuario)
            response = self.client.post(f'/api/materiales/{material.id}/moderar/', {'accion': 'aprobar'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, usuario.rol)

        material.refresh_from_db()
        self.assertFalse(material.validacion)

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
        datos = {'materia_id': self.materia.id, 'horario': 'Lunes 14hs', 'aula': 'L-203'}
        datos.update(cambios)
        return datos

    def crear_clase(self, tutor=None, materia=None):
        return ClaseApoyo.objects.create(materia=materia or self.materia, tutor=tutor or self.tutor, horario='Lunes 14hs', aula='L-203')

    def test_un_tutor_crea_una_clase_siempre_a_su_nombre(self):
        self.como(self.tutor)

        # aunque intente ponerla a nombre de otro tutor, queda a su nombre
        response = self.client.post(self.url, self.datos(tutor_id=self.otro_tutor.legajo), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['tutor']['legajo'], self.tutor.legajo)
        self.assertEqual(ClaseApoyo.objects.get().tutor, self.tutor)

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
        self.assertEqual(clase.tutor, self.tutor)


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
        self.assertEqual(Ponderacion.objects.get().usuario, self.otro_alumno)

    def test_promedio_de_varias_ponderaciones(self):
        self.como(self.otro_alumno)
        self.puntuar(5)
        self.como(self.tutor)
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

        self.assertEqual(Ponderacion.objects.get().usuario, self.otro_alumno)

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
        Ponderacion.objects.create(material=self.material, usuario=self.otro_alumno, valor=5)
        Ponderacion.objects.create(material=otro_material, usuario=self.otro_alumno, valor=3)
        Ponderacion.objects.create(material=self.material, usuario=self.tutor, valor=1)

        self.como(self.otro_alumno)
        self.assertEqual(len(self.client.get(self.url).data), 2)
        filtradas = self.client.get(self.url, {'material': self.material.id}).data
        self.assertEqual([p['valor'] for p in filtradas], [5])
        self.assertEqual(self.client.get(self.url, {'material': 'x'}).status_code, 400)

        self.como(self.admin)
        self.assertEqual(len(self.client.get(self.url).data), 3)

    def test_solo_el_dueno_o_un_administrador_toca_una_ponderacion(self):
        ponderacion = Ponderacion.objects.create(material=self.material, usuario=self.otro_alumno, valor=5)
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
        ponderacion = Ponderacion.objects.create(material=self.material, usuario=self.otro_alumno, valor=5)
        self.como(self.otro_alumno)

        response = self.client.put(
            f'{self.url}{ponderacion.id}/', {'material_id': otro_material.id, 'valor': 2, 'usuario_id': self.admin.legajo}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ponderacion.refresh_from_db()
        self.assertEqual((ponderacion.material, ponderacion.usuario, ponderacion.valor), (self.material, self.otro_alumno, 2))

    def test_la_restriccion_de_la_base_impide_dos_votos_del_mismo_usuario(self):
        from django.db import IntegrityError, transaction

        Ponderacion.objects.create(material=self.material, usuario=self.otro_alumno, valor=5)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Ponderacion.objects.create(material=self.material, usuario=self.otro_alumno, valor=1)
