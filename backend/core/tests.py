from unittest.mock import Mock, patch

from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Usuario


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
