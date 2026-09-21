from unittest.mock import Mock, patch

from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Especialidad, Materia, Material, Ponderacion, Usuario


class RegistroAlumnoTests(APITestCase):
    url = '/api/registro/'

    @staticmethod
    def _sysacad_ok(legajo="48293", nombre="Sofía Martínez", correo="smartinez@frd.utn.edu.ar"):
        """Simula la respuesta 200 de GET /alumnos/{legajo} en el mock-sysacad."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "legajo": legajo,
            "nombre": nombre,
            "correo": correo,
            "carrera": "ISI",
        }
        return mock_response

    @staticmethod
    def _sysacad_404():
        """Simula que el legajo no existe en SysAcad."""
        mock_response = Mock()
        mock_response.status_code = 404
        return mock_response

    @patch('core.views.requests.get')
    def test_registro_exitoso(self, mock_get):
        mock_get.return_value = self._sysacad_ok()

        response = self.client.post(
            self.url, {"legajo": "48293", "contraseña": "miclave123"}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['legajo'], "48293")
        self.assertEqual(response.data['nombre_y_apellido'], "Sofía Martínez")

        usuario = Usuario.objects.get(legajo="48293")
        self.assertEqual(usuario.correo, "smartinez@frd.utn.edu.ar")
        self.assertEqual(usuario.rol, "alumno")
        # la contraseña nunca se guarda en texto plano
        self.assertNotEqual(usuario.contraseña, "miclave123")
        self.assertTrue(check_password("miclave123", usuario.contraseña))

        mock_get.assert_called_once_with("http://localhost:4000/alumnos/48293")

    @patch('core.views.requests.get')
    def test_legajo_ya_registrado(self, mock_get):
        Usuario.objects.create(
            legajo="48293",
            nombre_y_apellido="Ya Existente",
            correo="existente@mail.com",
            contraseña="hash-lo-que-sea",
            rol="alumno",
        )

        response = self.client.post(
            self.url, {"legajo": "48293", "contraseña": "otraclave"}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        # si ya existe localmente, ni hace falta preguntarle a SysAcad
        mock_get.assert_not_called()
        self.assertEqual(Usuario.objects.filter(legajo="48293").count(), 1)

    @patch('core.views.requests.get')
    def test_legajo_inexistente_en_sysacad(self, mock_get):
        mock_get.return_value = self._sysacad_404()

        response = self.client.post(
            self.url, {"legajo": "99999", "contraseña": "miclave123"}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(Usuario.objects.count(), 0)

    def test_faltan_campos(self):
        response = self.client.post(
            self.url, {"legajo": "48293"}, format='json'  # sin contraseña
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(Usuario.objects.count(), 0)


class PonderacionTests(APITestCase):
    """Sistema de estrellas: cada usuario puntúa un material de 1 a 5 y la nota del material es el promedio."""
    url = '/api/ponderaciones/'

    def setUp(self):
        especialidad = Especialidad.objects.create(nombre="Sistemas")
        materia = Materia.objects.create(nombre="Algoritmos", anio=1, especialidad=especialidad)
        self.autor = Usuario.objects.create(
            legajo="1", nombre_y_apellido="Autor", correo="autor@mail.com", contraseña="x", rol="alumno"
        )
        self.usuario_a = Usuario.objects.create(
            legajo="2", nombre_y_apellido="Ana", correo="ana@mail.com", contraseña="x", rol="alumno"
        )
        self.usuario_b = Usuario.objects.create(
            legajo="3", nombre_y_apellido="Beto", correo="beto@mail.com", contraseña="x", rol="alumno"
        )
        self.material = Material.objects.create(
            materia=materia, usuario=self.autor, titulo="Resumen U1", tipo="resumen"
        )

    def _puntuar(self, usuario, valor, material_id=None):
        return self.client.post(
            self.url,
            {
                "material_id": material_id if material_id is not None else self.material.id,
                "usuario_id": usuario.legajo,
                "valor": valor,
            },
            format='json',
        )

    def _material(self):
        return self.client.get(f'/api/materiales/{self.material.id}/').data

    def test_material_sin_ponderaciones(self):
        datos = self._material()
        self.assertIsNone(datos['promedio_ponderacion'])
        self.assertEqual(datos['cantidad_ponderaciones'], 0)

    def test_puntuar_material(self):
        response = self._puntuar(self.usuario_a, 4)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ponderacion.objects.count(), 1)

    def test_promedio_de_varias_ponderaciones(self):
        self._puntuar(self.usuario_a, 5)
        self._puntuar(self.usuario_b, 2)

        datos = self._material()
        self.assertEqual(datos['promedio_ponderacion'], 3.5)
        self.assertEqual(datos['cantidad_ponderaciones'], 2)

    def test_puntuar_de_nuevo_actualiza_el_voto_anterior(self):
        self._puntuar(self.usuario_a, 5)
        self._puntuar(self.usuario_a, 1)

        self.assertEqual(Ponderacion.objects.count(), 1)
        datos = self._material()
        self.assertEqual(datos['promedio_ponderacion'], 1.0)
        self.assertEqual(datos['cantidad_ponderaciones'], 1)

    def test_valor_fuera_de_rango_es_rechazado(self):
        for valor in (0, 6, -1):
            response = self._puntuar(self.usuario_a, valor)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, f"valor={valor}")
        self.assertEqual(Ponderacion.objects.count(), 0)

    def test_material_inexistente(self):
        response = self._puntuar(self.usuario_a, 3, material_id=9999)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('material_id', response.data)

    def test_usuario_inexistente(self):
        usuario_fantasma = Usuario(legajo="no-existe")
        response = self._puntuar(usuario_fantasma, 3)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('usuario_id', response.data)
