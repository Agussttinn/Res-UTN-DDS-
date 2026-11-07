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

/** Días en los que se dan clases de apoyo (mismo número que usa el backend: 1 = lunes). */
export const DIAS_SEMANA: { valor: number; nombre: string }[] = [
  { valor: 1, nombre: 'Lunes' },
  { valor: 2, nombre: 'Martes' },
  { valor: 3, nombre: 'Miércoles' },
  { valor: 4, nombre: 'Jueves' },
  { valor: 5, nombre: 'Viernes' },
  { valor: 6, nombre: 'Sábado' },
];

/** Franja horaria permitida para una clase de apoyo y su duración mínima (las mismas reglas valida el backend). */
export const HORA_MINIMA_CLASE = '09:00';
export const HORA_MAXIMA_CLASE = '23:30';
export const DURACION_MINIMA_CLASE_MIN = 30;

export function nombreDia(dia: number | null): string {
  return DIAS_SEMANA.find((d) => d.valor === dia)?.nombre ?? '';
}

/** Si a la clase le falta el día o las horas (clases viejas, de antes de que el horario fuera obligatorio). */
export function horarioAConfirmar(clase: ClaseApoyo): boolean {
  return clase.dia === null || !clase.hora_inicio || !clase.hora_fin;
}

/** "Lunes 14:00 a 16:00", o "Horario a confirmar". */
export function textoHorario(clase: ClaseApoyo): string {
  return horarioAConfirmar(clase) ? 'Horario a confirmar' : `${nombreDia(clase.dia)} ${clase.hora_inicio} a ${clase.hora_fin}`;
}

/** "2° año" o "Electiva". */
export function etiquetaAnio(materia: Materia): string {
  return materia.electiva ? 'Electiva' : `${materia.anio}° año`;
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
  /** 1 = lunes ... 6 = sábado. Null (igual que las horas) solo en clases viejas con el horario "a confirmar". */
  dia: number | null;
  /** "HH:MM" */
  hora_inicio: string | null;
  hora_fin: string | null;
  /** Texto armado por el backend: "lunes de 14:00 a 16:00" o "a confirmar". */
  horario: string;
  aula: string;
  /** Si el usuario logueado sigue esta clase (recibe avisos de cambios y mensajes). */
  suscrito: boolean;
  cantidad_suscritos: number;
}

export interface EstadoSuscripcion {
  suscrito: boolean;
  cantidad_suscritos: number;
}

/** Mensaje del tutor de una clase a sus suscritos. */
export interface MensajeClase {
  id: number;
  autor: UsuarioPublico;
  texto: string;
  fecha: string;
}

export type TipoNotificacion = 'modificacion' | 'cancelacion' | 'mensaje';

export interface Notificacion {
  id: number;
  tipo: TipoNotificacion;
  titulo: string;
  texto: string;
  fecha: string;
  leida: boolean;
  /** Id de la clase, o null si la clase ya se canceló. */
  clase: number | null;
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
