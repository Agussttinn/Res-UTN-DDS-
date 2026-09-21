import { HttpClient } from '@angular/common/http';
import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { AuthService } from '../services/auth.service';
import { ALUMNA, API_URL, iniciarSesionComo, proveedoresDePrueba } from '../testing/pruebas';

describe('authInterceptor', () => {
  let http: HttpClient;
  let controlador: HttpTestingController;
  let navegar: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: proveedoresDePrueba() });
    navegar = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
  });

  const preparar = (conSesion: boolean) => {
    const token = conSesion ? iniciarSesionComo(ALUMNA) : null;
    http = TestBed.inject(HttpClient);
    controlador = TestBed.inject(HttpTestingController);
    return token;
  };

  afterEach(() => controlador.verify());

  it('agrega "Authorization: Bearer <token>" a los requests a la API', () => {
    const token = preparar(true);

    http.get(`${API_URL}/materias/`).subscribe();

    expect(controlador.expectOne(`${API_URL}/materias/`).request.headers.get('Authorization')).toBe(`Bearer ${token}`);
  });

  it('no agrega el header si no hay sesión', () => {
    preparar(false);

    http.get(`${API_URL}/materias/`).subscribe();

    expect(controlador.expectOne(`${API_URL}/materias/`).request.headers.has('Authorization')).toBe(false);
  });

  it('nunca le manda el token a otro dominio', () => {
    preparar(true);

    http.get('https://otro-sitio.com/api/materias/').subscribe();

    expect(controlador.expectOne('https://otro-sitio.com/api/materias/').request.headers.has('Authorization')).toBe(false);
  });

  it('un 401 en la API (token vencido) cierra la sesión y lleva al login avisando', () => {
    preparar(true);
    const auth = TestBed.inject(AuthService);
    let fallo = false;

    http.get(`${API_URL}/materias/`).subscribe({ error: () => (fallo = true) });
    controlador.expectOne(`${API_URL}/materias/`).flush({ detail: 'El token expiró' }, { status: 401, statusText: 'Unauthorized' });

    expect(fallo).toBe(true); // el error igual le llega a quien hizo el request
    expect(auth.estaLogueado()).toBe(false);
    expect(navegar).toHaveBeenCalledWith(['/login'], { queryParams: { vencida: 1 } });
  });

  it('varios 401 seguidos navegan una sola vez', () => {
    preparar(true);

    http.get(`${API_URL}/materias/`).subscribe({ error: () => undefined });
    http.get(`${API_URL}/materiales/`).subscribe({ error: () => undefined });
    controlador.expectOne(`${API_URL}/materias/`).flush({}, { status: 401, statusText: 'Unauthorized' });
    controlador.expectOne(`${API_URL}/materiales/`).flush({}, { status: 401, statusText: 'Unauthorized' });

    expect(navegar).toHaveBeenCalledTimes(1);
  });

  it('un 401 al iniciar sesión es "clave incorrecta", NO una sesión vencida', () => {
    preparar(true); // ya había una sesión abierta
    const auth = TestBed.inject(AuthService);

    http.post(`${API_URL}/login/`, {}).subscribe({ error: () => undefined });
    controlador.expectOne(`${API_URL}/login/`).flush({ error: 'mal' }, { status: 401, statusText: 'Unauthorized' });

    expect(auth.estaLogueado()).toBe(true);
    expect(navegar).not.toHaveBeenCalled();
  });

  it('otros errores (400, 403, 500) no cierran la sesión', () => {
    preparar(true);
    const auth = TestBed.inject(AuthService);

    for (const status of [400, 403, 500]) {
      http.get(`${API_URL}/materias/`).subscribe({ error: () => undefined });
      controlador.expectOne(`${API_URL}/materias/`).flush({}, { status, statusText: 'Error' });
    }

    expect(auth.estaLogueado()).toBe(true);
    expect(navegar).not.toHaveBeenCalled();
  });
});
