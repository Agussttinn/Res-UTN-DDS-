/** Formas de los datos que devuelve la API de Django (backend/core/serializer.py). */

export type Rol = 'alumno' | 'tutor' | 'administrador';
export type TipoMaterial = 'resumen' | 'parcial' | 'final';

export interface Usuario {
  legajo: string;
  nombre_y_apellido: string;
  correo: string;
  rol: Rol;
}

/** Lo mínimo de un usuario cuando viene dentro de otro recurso (autor de un apunte, tutor de una clase). */
export type UsuarioPublico = Pick<Usuario, 'legajo' | 'nombre_y_apellido' | 'rol'>;

export interface Especialidad {
  id: number;
  nombre: string;
}

export interface Materia {
  id: number;
  nombre: string;
  /** Año (nivel) del plan de estudio. En las electivas, el nivel desde el que se pueden cursar. */
  anio: number;
  electiva: boolean;
  especialidad: Especialidad;
}

/** Cómo se agrupan las materias para elegirlas: por año (1 a 5) o las electivas, aparte. */
export type FiltroAnio = number | 'electivas';

export const FILTROS_ANIO: { valor: FiltroAnio; etiqueta: string; corta: string }[] = [
  { valor: 1, etiqueta: '1° año', corta: '1°' },
  { valor: 2, etiqueta: '2° año', corta: '2°' },
  { valor: 3, etiqueta: '3° año', corta: '3°' },
  { valor: 4, etiqueta: '4° año', corta: '4°' },
  { valor: 5, etiqueta: '5° año', corta: '5°' },
  { valor: 'electivas', etiqueta: 'Electivas', corta: 'Electivas' },
];

/** El grupo al que pertenece una materia. */
export function filtroAnioDe(materia: Materia): FiltroAnio {
  return materia.electiva ? 'electivas' : materia.anio;
}

export function esDelFiltro(materia: Materia, filtro: FiltroAnio): boolean {
  return filtroAnioDe(materia) === filtro;
}

export interface Material {
  id: number;
  materia: Materia;
  usuario: UsuarioPublico;
  titulo: string;
  fecha_de_carga: string;
  tipo: TipoMaterial;
  /** false = pendiente de revisión: solo lo ven su autor y los administradores. */
  validacion: boolean;
  comentario: string | null;
  /** URL completa del archivo, o null en materiales viejos sin archivo. */
  archivo: string | null;
  /** Promedio de estrellas (1 a 5) con un decimal, o null si nadie lo puntuó todavía. */
  promedio_ponderacion: number | null;
  cantidad_ponderaciones: number;
}

export interface ClaseApoyo {
  id: number;
  materia: Materia;
  tutor: UsuarioPublico;
  horario: string;
  aula: string;
}

export interface Ponderacion {
  material: Material;
  usuario: UsuarioPublico;
  /** Estrellas, de 1 a 5. */
  valor: number;
  fecha: string;
}

export interface RespuestaLogin {
  access: string;
  usuario: Usuario;
}

export type AccionModeracion = 'aprobar' | 'rechazar';

export const ETIQUETA_TIPO: Record<TipoMaterial, string> = {
  resumen: 'Resumen',
  parcial: 'Parcial',
  final: 'Final',
};

export const ETIQUETA_TIPO_PLURAL: Record<TipoMaterial, string> = {
  resumen: 'Resúmenes',
  parcial: 'Parciales',
  final: 'Finales',
};

export const ETIQUETA_ROL: Record<Rol, string> = {
  alumno: 'Alumno',
  tutor: 'Tutor',
  administrador: 'Administrador',
};
