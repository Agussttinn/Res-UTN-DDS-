import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { ALUMNA, API_URL, ADMINISTRADORA, TUTOR, iniciarSesionComo, proveedoresDePrueba, tokenDe } from '../testing/pruebas';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: proveedoresDePrueba() });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  const crear = () => TestBed.inject(AuthService);

  describe('al abrir la página', () => {
    it('sin nada guardado no hay sesión', () => {
      const auth = crear();

      expect(auth.estaLogueado()).toBe(false);
      expect(auth.usuario()).toBeNull();
      expect(auth.token()).toBeNull();
    });

    it('recupera la sesión guardada si el token sigue vigente', () => {
      const token = iniciarSesionComo(ALUMNA);

      const auth = crear();

      expect(auth.estaLogueado()).toBe(true);
      expect(auth.usuario()).toEqual(ALUMNA);
      expect(auth.token()).toBe(token);
    });

    it('descarta un token vencido y borra lo guardado', () => {
      localStorage.setItem('auth_token', tokenDe('200', -60));
      localStorage.setItem('auth_user', JSON.stringify(ALUMNA));

      const auth = crear();

      expect(auth.estaLogueado()).toBe(false);
      expect(localStorage.getItem('auth_token')).toBeNull();
      expect(localStorage.getItem('auth_user')).toBeNull();
    });

    it('descarta lo guardado si está corrupto (token que no es un JWT, usuario que no es JSON)', () => {
      localStorage.setItem('auth_token', 'no-es-un-token');
      localStorage.setItem('auth_user', JSON.stringify(ALUMNA));
      expect(crear().estaLogueado()).toBe(false);
    });

    it('descarta la sesión si falta el usuario o no se puede leer', () => {
      localStorage.setItem('auth_token', tokenDe('200'));
      localStorage.setItem('auth_user', '{esto no es json');

      expect(crear().estaLogueado()).toBe(false);
      expect(localStorage.getItem('auth_token')).toBeNull();
    });
  });

  describe('roles', () => {
    it('expone el rol y los atajos esAdministrador / esTutor', () => {
      iniciarSesionComo(ADMINISTRADORA);
      let auth = crear();
      expect([auth.rol(), auth.esAdministrador(), auth.esTutor()]).toEqual(['administrador', true, false]);

      localStorage.clear();
      TestBed.resetTestingModule();
      TestBed.configureTestingModule({ providers: proveedoresDePrueba() });
      iniciarSesionComo(TUTOR);
      auth = crear();
      expect([auth.rol(), auth.esAdministrador(), auth.esTutor()]).toEqual(['tutor', false, true]);
    });
  });

  describe('login', () => {
    it('manda legajo y contraseña a /login/, y guarda token y usuario (en memoria y en localStorage)', () => {
      const auth = crear();
      let recibido = null as unknown;

      auth.login('200', 'miClave123').subscribe((usuario) => (recibido = usuario));

      const peticion = http.expectOne(`${API_URL}/login/`);
      expect(peticion.request.method).toBe('POST');
      expect(peticion.request.body).toEqual({ legajo: '200', contraseña: 'miClave123' });
      const token = tokenDe('200');
      peticion.flush({ access: token, usuario: ALUMNA });

      expect(recibido).toEqual(ALUMNA);
      expect(auth.estaLogueado()).toBe(true);
      expect(auth.token()).toBe(token);
      expect(localStorage.getItem('auth_token')).toBe(token);
      expect(JSON.parse(localStorage.getItem('auth_user') ?? 'null')).toEqual(ALUMNA);
    });

    it('si las credenciales son incorrectas no queda ninguna sesión', () => {
      const auth = crear();
      let fallo = false;

      auth.login('200', 'mal').subscribe({ error: () => (fallo = true) });
      http.expectOne(`${API_URL}/login/`).flush({ error: 'Legajo o contraseña incorrectos' }, { status: 401, statusText: 'Unauthorized' });

      expect(fallo).toBe(true);
      expect(auth.estaLogueado()).toBe(false);
      expect(localStorage.getItem('auth_token')).toBeNull();
    });
  });

  describe('registro', () => {
    it('manda legajo y contraseña a /registro/ y NO inicia sesión', () => {
      const auth = crear();

      auth.registrar('48293', 'miClave123').subscribe();

      const peticion = http.expectOne(`${API_URL}/registro/`);
      expect(peticion.request.body).toEqual({ legajo: '48293', contraseña: 'miClave123' });
      peticion.flush({ legajo: '48293', nombre_y_apellido: 'Sofía Martínez' }, { status: 201, statusText: 'Created' });
      expect(auth.estaLogueado()).toBe(false);
    });
  });

  describe('cerrar sesión', () => {
    it('limpia todo y lleva al login', () => {
      iniciarSesionComo(ALUMNA);
      const auth = crear();
      const navegar = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);

      auth.cerrarSesion();

      expect(auth.estaLogueado()).toBe(false);
      expect(localStorage.getItem('auth_token')).toBeNull();
      expect(navegar).toHaveBeenCalledWith(['/login']);
    });

    it('por vencimiento: limpia y lleva al login avisando que venció', () => {
      iniciarSesionComo(ALUMNA);
      const auth = crear();
      const navegar = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);

      auth.cerrarSesionPorVencimiento();

      expect(auth.estaLogueado()).toBe(false);
      expect(navegar).toHaveBeenCalledWith(['/login'], { queryParams: { vencida: 1 } });
    });

    it('por vencimiento, si ya estaba cerrada (varios requests fallando a la vez) no navega dos veces', () => {
      const auth = crear(); // sin sesión
      const navegar = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);

      auth.cerrarSesionPorVencimiento();

      expect(navegar).not.toHaveBeenCalled();
    });
  });
});
