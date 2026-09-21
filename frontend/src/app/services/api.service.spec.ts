import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { API_URL, proveedoresDePrueba } from '../testing/pruebas';
import { ApiService } from './api.service';

describe('ApiService', () => {
  let api: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: proveedoresDePrueba() });
    api = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  /** Hace la petición y devuelve lo que salió por la red (método, url, parámetros y cuerpo). */
  const pedir = (peticion: { subscribe: () => unknown }, url: string) => {
    peticion.subscribe();
    return http.expectOne((r) => r.url === `${API_URL}${url}`).request;
  };

  it('materias y materiales', () => {
    expect(pedir(api.getMaterias(), '/materias/').method).toBe('GET');

    const todos = pedir(api.getMateriales(), '/materiales/');
    expect(todos.params.has('materia')).toBe(false);

    const deUna = pedir(api.getMateriales(3), '/materiales/');
    expect(deUna.params.get('materia')).toBe('3');

    expect(pedir(api.getMaterial(7), '/materiales/7/').method).toBe('GET');
  });

  it('subir un material manda el FormData tal cual', () => {
    const datos = new FormData();
    datos.append('titulo', 'x');
    api.subirMaterial(datos).subscribe();

    const peticion = http.expectOne(`${API_URL}/materiales/`);
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toBe(datos);
  });

  it('moderación', () => {
    expect(pedir(api.getMaterialesPendientes(), '/materiales/pendientes/').method).toBe('GET');

    const peticion = pedir(api.moderarMaterial(7, 'rechazar'), '/materiales/7/moderar/');
    expect(peticion.method).toBe('POST');
    expect(peticion.body).toEqual({ accion: 'rechazar' });
  });

  it('estrellas: pedir las propias y puntuar (sin mandar usuario)', () => {
    expect(pedir(api.getMisPonderaciones(), '/ponderaciones/').method).toBe('GET');

    const peticion = pedir(api.ponderar(7, 4), '/ponderaciones/');
    expect(peticion.method).toBe('POST');
    expect(peticion.body).toEqual({ material_id: 7, valor: 4 });
  });

  it('clases de apoyo: listar (con filtro), crear, modificar y eliminar', () => {
    expect(pedir(api.getClasesApoyo(2), '/clases-apoyo/').params.get('materia')).toBe('2');

    const datos = { materia_id: 1, horario: 'Lun 14hs', aula: 'L-1' };
    const alta = pedir(api.crearClaseApoyo(datos), '/clases-apoyo/');
    expect([alta.method, alta.body]).toEqual(['POST', datos]);

    const cambio = pedir(api.actualizarClaseApoyo(3, datos), '/clases-apoyo/3/');
    expect([cambio.method, cambio.body]).toEqual(['PATCH', datos]);

    expect(pedir(api.eliminarClaseApoyo(3), '/clases-apoyo/3/').method).toBe('DELETE');
  });
});
