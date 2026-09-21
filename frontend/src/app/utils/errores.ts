import { HttpErrorResponse } from '@angular/common/http';

/** Cómo se le muestra al usuario el nombre de cada campo cuando la API rechaza un formulario. */
const ETIQUETA_CAMPO: Record<string, string> = {
  archivo: 'Archivo',
  titulo: 'Título',
  tipo: 'Tipo',
  materia_id: 'Materia',
  comentario: 'Comentario',
  valor: 'Estrellas',
  material_id: 'Apunte',
  horario: 'Horario',
  aula: 'Aula',
  legajo: 'Legajo',
  contraseña: 'Contraseña',
};

const POR_DEFECTO = 'Ocurrió un error inesperado. Intentá de nuevo en unos minutos.';

/**
 * Convierte un error HTTP de la API en un mensaje legible en español.
 * La API responde de tres formas: {"error": "..."} (vistas propias), {"detail": "..."} (permisos, límite de
 * intentos) y {"campo": ["..."]} (validación de formularios).
 */
export function mensajeDeError(err: unknown, porDefecto: string = POR_DEFECTO): string {
  if (!(err instanceof HttpErrorResponse)) {
    return porDefecto;
  }
  if (err.status === 0) {
    return 'No se pudo conectar con el servidor. Verificá que el backend esté corriendo.';
  }
  if (err.status === 429) {
    return 'Hiciste demasiados intentos seguidos. Esperá un minuto y probá de nuevo.';
  }
  if (err.status >= 500) {
    return porDefecto;
  }

  const cuerpo: unknown = err.error;
  if (cuerpo === null || typeof cuerpo !== 'object' || Array.isArray(cuerpo)) {
    return porDefecto;
  }
  const datos = cuerpo as Record<string, unknown>;

  for (const clave of ['error', 'detail']) {
    const valor = datos[clave];
    if (typeof valor === 'string' && valor) {
      return valor;
    }
  }

  // Errores de validación por campo: { archivo: ["..."], tipo: ["..."] }
  const mensajes: string[] = [];
  for (const [campo, detalle] of Object.entries(datos)) {
    const textos = (Array.isArray(detalle) ? detalle : [detalle]).filter(
      (t): t is string => typeof t === 'string',
    );
    for (const texto of textos) {
      const etiqueta = ETIQUETA_CAMPO[campo];
      mensajes.push(etiqueta ? `${etiqueta}: ${texto}` : texto);
    }
  }
  return mensajes.length > 0 ? mensajes.join(' ') : porDefecto;
}
