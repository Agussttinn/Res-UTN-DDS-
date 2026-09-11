export interface Materia {
  idMateria: string;
  nombre: string;
  nivel: number;
  // Correlativas: materias que el alumno debe tener cursadas/aprobadas para inscribirse.
  cursadas: string[];
  aprobadas: string[];
}

export interface PlanDeEstudio {
  nombre: string;
  materias: Materia[];
}

export interface Alumno {
  legajo: string;
  nombre: string;
  correo: string;
  carrera: string;
  // idMateria de las materias que el alumno tiene cursadas (regularizadas) y aprobadas (final rendido).
  cursadas: string[];
  aprobadas: string[];
}

export type EstadoMateria = 'aprobada' | 'cursada' | 'no_cursada';
