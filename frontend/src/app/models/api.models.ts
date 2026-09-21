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
  anio: number;
  especialidad: Especialidad;
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
