/** Apoyo para los tests: configuración común y datos de ejemplo con la forma real de la API. */
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { EnvironmentProviders, Provider, Type, provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { API_URL } from '../api.config';
import { authInterceptor } from '../interceptors/auth-interceptor';
import { ClaseApoyo, Materia, Material, Usuario } from '../models/api.models';

export { API_URL };

/** Igual que la app real: sin zonas (los datos comunes no refrescan la vista, solo los signals), con el interceptor. */
export function proveedoresDePrueba(...extra: (Provider | EnvironmentProviders)[]): (Provider | EnvironmentProviders)[] {
  return [
    provideZonelessChangeDetection(),
    provideRouter([]),
    provideHttpClient(withInterceptors([authInterceptor])),
    provideHttpClientTesting(),
    ...extra,
  ];
}

/**
 * Crea el componente y corre su primer ciclo (ngOnInit incluido, que suele disparar peticiones HTTP).
 * NO espera a que se estabilice: en modo sin zonas, whenStable() espera a las peticiones pendientes, así que
 * primero hay que responderlas con HttpTestingController y recién después llamar a `estabilizar`.
 */
export function crearComponente<T>(tipo: Type<T>): ComponentFixture<T> {
  const fixture = TestBed.createComponent(tipo);
  fixture.detectChanges();
  return fixture;
}

/** Espera a que Angular termine de pintar los cambios pendientes. */
export async function estabilizar(fixture: ComponentFixture<unknown>): Promise<void> {
  await fixture.whenStable();
}

export function textoDe(fixture: ComponentFixture<unknown>): string {
  return (fixture.nativeElement as HTMLElement).textContent?.replace(/\s+/g, ' ').trim() ?? '';
}

/** Un token con la forma de los del backend (header.payload.firma); solo importa que el payload tenga "exp". */
export function tokenDe(legajo: string, venceEnSegundos = 3600): string {
  const codificar = (objeto: unknown) => btoa(JSON.stringify(objeto)).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
  const exp = Math.floor(Date.now() / 1000) + venceEnSegundos;
  return `${codificar({ alg: 'HS256', typ: 'JWT' })}.${codificar({ sub: legajo, exp })}.firma`;
}

/** Deja una sesión guardada, como si la persona ya hubiera iniciado sesión. Hay que llamarlo ANTES de crear el AuthService. */
export function iniciarSesionComo(usuario: Usuario): string {
  const token = tokenDe(usuario.legajo);
  localStorage.setItem('auth_token', token);
  localStorage.setItem('auth_user', JSON.stringify(usuario));
  return token;
}

export const ADMINISTRADORA: Usuario = { legajo: '100', nombre_y_apellido: 'Ada Administradora', correo: 'ada@utn.edu.ar', rol: 'administrador' };
export const TUTOR: Usuario = { legajo: '150', nombre_y_apellido: 'Tomás Tutor', correo: 'tomas@utn.edu.ar', rol: 'tutor' };
export const ALUMNA: Usuario = { legajo: '200', nombre_y_apellido: 'Ana Alumna', correo: 'ana@utn.edu.ar', rol: 'alumno' };

export function unaMateria(cambios: Partial<Materia> = {}): Materia {
  return {
    id: 1,
    nombre: 'Algoritmos y Estructuras de Datos',
    anio: 1,
    especialidad: { id: 1, nombre: 'Ingeniería en Sistemas' },
    ...cambios,
  };
}

export function unMaterial(cambios: Partial<Material> = {}): Material {
  return {
    id: 7,
    materia: unaMateria(),
    usuario: { legajo: '300', nombre_y_apellido: 'Beto Alumno', rol: 'alumno' },
    titulo: 'Resumen Unidad 1',
    fecha_de_carga: '2026-09-21T15:00:00-03:00',
    tipo: 'resumen',
    validacion: true,
    comentario: null,
    archivo: 'http://127.0.0.1:8000/media/materiales/abc.pdf',
    promedio_ponderacion: null,
    cantidad_ponderaciones: 0,
    ...cambios,
  };
}

export function unaClase(cambios: Partial<ClaseApoyo> = {}): ClaseApoyo {
  return {
    id: 3,
    materia: unaMateria(),
    tutor: { legajo: TUTOR.legajo, nombre_y_apellido: TUTOR.nombre_y_apellido, rol: 'tutor' },
    horario: 'Lun 14:00-16:00',
    aula: 'L-203',
    ...cambios,
  };
}
