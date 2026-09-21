import { HttpErrorResponse } from '@angular/common/http';

import { mensajeDeError } from './errores';

const error = (status: number, cuerpo: unknown) => new HttpErrorResponse({ status, error: cuerpo });

describe('mensajeDeError', () => {
  it('usa el campo "error" de las vistas propias de la API', () => {
    expect(mensajeDeError(error(401, { error: 'Legajo o contraseña incorrectos' }))).toBe('Legajo o contraseña incorrectos');
  });

  it('usa el campo "detail" (permisos, token inválido)', () => {
    expect(mensajeDeError(error(403, { detail: 'Esta acción es solo para administradores.' }))).toBe(
      'Esta acción es solo para administradores.',
    );
  });

  it('junta los errores de validación por campo, con el nombre del campo en español', () => {
    const err = error(400, { archivo: ['El archivo no puede pesar más de 10 MB.'], tipo: ['Elección no válida.'] });
    expect(mensajeDeError(err)).toBe('Archivo: El archivo no puede pesar más de 10 MB. Tipo: Elección no válida.');
  });

  it('acepta un mensaje suelto (no lista) en un campo, y campos que no conoce', () => {
    expect(mensajeDeError(error(400, { campo_raro: 'Algo salió mal.' }))).toBe('Algo salió mal.');
  });

  it('sin conexión con el servidor', () => {
    expect(mensajeDeError(error(0, null))).toContain('No se pudo conectar con el servidor');
  });

  it('límite de intentos (429): no muestra el texto en inglés de la API', () => {
    const mensaje = mensajeDeError(error(429, { detail: 'Request was throttled. Expected available in 45 seconds.' }));
    expect(mensaje).toContain('demasiados intentos');
    expect(mensaje).not.toContain('throttled');
  });

  it('errores del servidor (500) y cuerpos que no son objetos usan el mensaje por defecto', () => {
    expect(mensajeDeError(error(500, '<html>Traceback...</html>'), 'No se pudo guardar.')).toBe('No se pudo guardar.');
    expect(mensajeDeError(error(400, '<html>'), 'Por defecto')).toBe('Por defecto');
    expect(mensajeDeError(error(400, null), 'Por defecto')).toBe('Por defecto');
    expect(mensajeDeError(error(400, ['lista']), 'Por defecto')).toBe('Por defecto');
    expect(mensajeDeError(error(400, {}), 'Por defecto')).toBe('Por defecto');
  });

  it('cualquier cosa que no sea un error HTTP usa el mensaje por defecto', () => {
    expect(mensajeDeError(new Error('boom'), 'Por defecto')).toBe('Por defecto');
    expect(mensajeDeError(undefined)).toContain('error inesperado');
  });
});
