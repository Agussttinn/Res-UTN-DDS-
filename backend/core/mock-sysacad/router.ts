import { Router, Request, Response } from 'express';
import planISI from './data/plan-isi.json';
import planQuimica from './data/plan-quimica.json';
import planElectrica from './data/plan-electrica.json';
import planMecanica from './data/plan-mecanica.json';
import alumnosData from './data/alumnos.json';
import { Alumno, EstadoMateria, PlanDeEstudio } from './types';

//planesDeEstudio es de tipo Record<string, PlanDeEstudio> y contiene los planes de estudio de las carreras ISI, Química, Eléctrica y Mecánica. 
//cada plan de estudio se importa desde un archivo JSON correspondiente y se asigna a la clave del código de la carrera en el objeto planesDeEstudio.
const planesDeEstudio: Record<string, PlanDeEstudio> = {
  ISI: planISI as PlanDeEstudio,
  QUI: planQuimica as PlanDeEstudio,
  ELE: planElectrica as PlanDeEstudio,
  MEC: planMecanica as PlanDeEstudio,
};

const alumnos: Alumno[] = alumnosData as Alumno[];

export const router = Router();

router.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok' });
});



// PLANES DE ESTUDIO

//Devuelve las carreras disponibles en el mock de SySACAD con su codigo y nombre
router.get('/planes-de-estudio', (_req: Request, res: Response) => {
  const carreras = Object.entries(planesDeEstudio).map(([codigo, plan]) => ({
    codigo,
    nombre: plan.nombre,
  }));
  res.json(carreras);
});

//Devuelve el plan de estudio de una carrera especifica
router.get('/planes-de-estudio/:carrera', (req: Request, res: Response) => {
  const carrera = req.params.carrera.toUpperCase();
  const plan = planesDeEstudio[carrera];
  if (!plan) {
    res.status(404).json({ error: `No existe un plan de estudio para la carrera "${req.params.carrera}"` });
    return;
  }
  res.json(plan);
});

//Devuelve una materia especifica de un plan de estudio
router.get('/planes-de-estudio/:carrera/materias/:idMateria', (req: Request, res: Response) => {
  const plan = planesDeEstudio[req.params.carrera.toUpperCase()];
  if (!plan) {
    res.status(404).json({ error: `No existe un plan de estudio para la carrera "${req.params.carrera}"` });
    return;
  }
  const materia = plan.materias.find((m) => m.idMateria === req.params.idMateria);
  if (!materia) {
    res.status(404).json({
      error: `No existe la materia "${req.params.idMateria}" en el plan "${req.params.carrera}"`,
    });
    return;
  }
  res.json(materia);
});

// --- Alumnos ---

router.get('/alumnos', (_req: Request, res: Response) => {
  res.json(alumnos.map(({ legajo, nombre, correo, carrera }) => ({ legajo, nombre, correo, carrera })));
});

router.get('/alumnos/:legajo', (req: Request, res: Response) => {
  const alumno = alumnos.find((a) => a.legajo === req.params.legajo);
  if (!alumno) {
    res.status(404).json({ error: `No existe un alumno con legajo "${req.params.legajo}"` });
    return;
  }
  res.json(alumno);
});

// Chequeo puntual del estado de un alumno en una materia, pensado para que
// RES-UTN valide (ej. antes de aceptar un Material o una inscripción a
// ClaseApoyo) si un legajo está cursada/aprobada en una materia dada.
router.get('/alumnos/:legajo/materias/:idMateria', (req: Request, res: Response) => {
  const alumno = alumnos.find((a) => a.legajo === req.params.legajo);
  if (!alumno) {
    res.status(404).json({ error: `No existe un alumno con legajo "${req.params.legajo}"` });
    return;
  }

  const { idMateria } = req.params;
  let estado: EstadoMateria = 'no_cursada';
  if (alumno.aprobadas.includes(idMateria)) {
    estado = 'aprobada';
  } else if (alumno.cursadas.includes(idMateria)) {
    estado = 'cursada';
  }

  res.json({ legajo: alumno.legajo, idMateria, estado });
});
