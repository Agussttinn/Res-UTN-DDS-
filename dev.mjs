#!/usr/bin/env node
/**
 * Levanta backend (Django), mock de SySACAD (Node) y frontend (Angular) en simultáneo,
 * con un solo comando y la salida de cada uno con su prefijo de color.
 *
 *   node dev.mjs        (Windows, macOS y Linux)
 *   ./dev.sh            (atajo para macOS y Linux)
 *
 * Ctrl+C detiene los tres juntos. Solo usa Node (que Angular ya exige tener instalado): no hay nada que instalar.
 */
import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

/** Ruta al Python del entorno virtual. En Windows está en Scripts\python.exe; en macOS/Linux, en bin/python. */
export function rutaPython(raiz, plataforma = process.platform) {
  const ruta = plataforma === 'win32' ? path.win32 : path.posix;
  const venv = ruta.join(raiz, 'backend', 'DSWenv');
  return plataforma === 'win32' ? ruta.join(venv, 'Scripts', 'python.exe') : ruta.join(venv, 'bin', 'python');
}

/** Cómo crear el entorno virtual e instalar las dependencias del backend, según el sistema. */
export function comandosEntornoVirtual(plataforma = process.platform) {
  return plataforma === 'win32'
    ? 'cd backend && python -m venv DSWenv && DSWenv\\Scripts\\pip install -r requirements.txt'
    : 'cd backend && python3 -m venv DSWenv && DSWenv/bin/pip install -r requirements.txt';
}

/** Comando para copiar la plantilla de variables de entorno, según el sistema. */
export function comandoCopiarEnv(plataforma = process.platform) {
  return plataforma === 'win32' ? 'copy backend\\.env.example backend\\.env' : 'cp backend/.env.example backend/.env';
}

/** ¿Hay algo escuchando en ese puerto? (Se prueba conectando: funciona igual en todos los sistemas.) */
export function puertoOcupado(puerto) {
  return new Promise((resolve) => {
    const conexion = net.connect({ port: puerto, host: '127.0.0.1' });
    conexion.setTimeout(800);
    conexion.once('connect', () => { conexion.destroy(); resolve(true); });
    conexion.once('timeout', () => { conexion.destroy(); resolve(false); });
    conexion.once('error', () => resolve(false)); // ECONNREFUSED: nadie escucha, el puerto está libre
  });
}

/** Arma la lista de servicios a levantar. */
export function armarServicios(raiz, plataforma = process.platform, entorno = process.env) {
  const ruta = plataforma === 'win32' ? path.win32 : path.posix;
  const puertoMock = Number(entorno.MOCK_SYSACAD_PORT) || 4000;
  return [
    {
      nombre: 'BACKEND', color: 34, puerto: 8000, url: 'http://127.0.0.1:8000',
      comando: rutaPython(raiz, plataforma), args: ['manage.py', 'runserver'],
      cwd: ruta.join(raiz, 'backend'),
      // Sin esto Python guarda su salida en un buffer al no estar en una terminal, y los logs aparecen tarde o nunca.
      // PYTHONUTF8: en Windows Python usa por defecto la codificación de la región (cp1252) al escribir a un pipe.
      env: { PYTHONUNBUFFERED: '1', PYTHONUTF8: '1' },
    },
    {
      nombre: 'MOCK', color: 33, puerto: puertoMock, url: `http://localhost:${puertoMock}`,
      comando: 'npm', args: ['run', 'start'],
      cwd: ruta.join(raiz, 'backend', 'core', 'mock-sysacad'),
    },
    {
      nombre: 'FRONTEND', color: 32, puerto: 4200, url: 'http://localhost:4200',
      comando: 'npm', args: ['start'],
      cwd: ruta.join(raiz, 'frontend'),
    },
  ];
}

/** Revisa todo lo que tiene que existir antes de arrancar. Devuelve la lista de problemas (vacía si está todo bien). */
export async function diagnosticar(raiz, servicios, plataforma = process.platform) {
  const problemas = [];
  if (!existsSync(rutaPython(raiz, plataforma))) {
    problemas.push(`No encontré el entorno virtual de Python (backend/DSWenv). Creálo con:\n      ${comandosEntornoVirtual(plataforma)}`);
  }
  if (!existsSync(path.join(raiz, 'backend', '.env'))) {
    problemas.push(`Falta backend/.env (credenciales de la base de datos). Copiá la plantilla y completá tus datos:\n      ${comandoCopiarEnv(plataforma)}`);
  }
  for (const [nombre, carpeta] of [['mock de SySACAD', servicios[1].cwd], ['frontend', servicios[2].cwd]]) {
    if (!existsSync(path.join(carpeta, 'node_modules'))) {
      problemas.push(`Faltan las dependencias del ${nombre}. Instalálas con:\n      cd ${path.relative(raiz, carpeta)} && npm install`);
    }
  }
  for (const servicio of servicios) {
    if (await puertoOcupado(servicio.puerto)) {
      problemas.push(`El puerto ${servicio.puerto} (${servicio.nombre}) ya está en uso. ¿Ya tenés esto corriendo en otra terminal?`);
    }
  }
  return problemas;
}

const esWindows = process.platform === 'win32';
const conColor = process.stdout.isTTY && !process.env.NO_COLOR;
const pintar = (color, texto) => (conColor ? `\x1b[${color}m${texto}\x1b[0m` : texto);

/**
 * Lanza los servicios, muestra lo que imprime cada uno con su prefijo y se encarga de cerrarlos a todos
 * (con todo lo que hayan lanzado) al hacer Ctrl+C. Termina el proceso cuando ya no queda ninguno.
 */
export function lanzar(servicios) {
  console.log('\nLevantando RES-UTN (Ctrl+C para detener todo):');
  servicios.forEach((s) => console.log(`  ${pintar(s.color, s.nombre.padEnd(8))} ${s.url}`));
  console.log('');

  const hijos = [];
  let deteniendo = false;

  const imprimirLinea = (servicio, linea) => console.log(`${pintar(servicio.color, `[${servicio.nombre}]`)} ${linea}`);

  /** Muestra lo que imprime un servicio línea por línea, con su prefijo (un dato puede llegar cortado a la mitad). */
  const prefijar = (servicio, flujo) => {
    let resto = '';
    flujo.setEncoding('utf8');
    flujo.on('data', (fragmento) => {
      const lineas = (resto + fragmento).split(/\r?\n/);
      resto = lineas.pop() ?? '';
      lineas.forEach((linea) => imprimirLinea(servicio, linea));
    });
    flujo.on('end', () => { if (resto) imprimirLinea(servicio, resto); });
  };

  /** Detiene un servicio con todo lo que lanzó (el runserver de Django y ng serve crean procesos hijos). */
  const matar = (hijo, senal = 'SIGTERM') => {
    if (hijo.exitCode !== null || hijo.pid === undefined) return;
    try {
      if (esWindows) {
        spawnSync('taskkill', ['/pid', String(hijo.pid), '/T', '/F'], { stdio: 'ignore' });
      } else {
        process.kill(-hijo.pid, senal); // el grupo de procesos completo (los lanzamos con detached)
      }
    } catch {
      // ya había terminado
    }
  };

  const detener = (codigo = 0) => {
    if (deteniendo) return;
    deteniendo = true;
    console.log('\nDeteniendo backend, mock-sysacad y frontend...');
    hijos.forEach((h) => matar(h));
    // Si alguno no cerró a tiempo, se fuerza.
    setTimeout(() => { hijos.forEach((h) => matar(h, 'SIGKILL')); process.exit(codigo); }, 4000).unref();
    const revisar = setInterval(() => {
      if (hijos.every((h) => h.exitCode !== null || h.signalCode !== null)) { clearInterval(revisar); process.exit(codigo); }
    }, 100);
  };

  for (const servicio of servicios) {
    const hijo = spawn(servicio.comando, servicio.args, {
      cwd: servicio.cwd,
      env: { ...process.env, ...servicio.env },
      stdio: ['ignore', 'pipe', 'pipe'],
      // En Windows "npm" es npm.cmd: hay que pasar por el intérprete de comandos para poder ejecutarlo.
      shell: esWindows && servicio.comando === 'npm',
      // En macOS/Linux cada servicio va en su propio grupo de procesos, para poder cerrarlo entero.
      detached: !esWindows,
      windowsHide: true,
    });
    hijos.push(hijo);
    prefijar(servicio, hijo.stdout);
    prefijar(servicio, hijo.stderr);
    hijo.on('error', (error) => imprimirLinea(servicio, pintar(31, `No se pudo iniciar: ${error.message}`)));
    hijo.on('exit', (codigo, senal) => {
      // Se espera un instante antes de avisar: en Windows, Ctrl+C llega a todos los procesos a la vez y un servicio puede
      // cerrarse un poco antes de que este script se entere de que se pidió detener todo (no es una caída inesperada).
      setTimeout(() => {
        if (deteniendo) return;
        imprimirLinea(servicio, pintar(31, `se detuvo inesperadamente (${senal ?? `código ${codigo}`}). Los demás siguen corriendo; Ctrl+C para cortar todo.`));
        if (hijos.every((h) => h.exitCode !== null || h.signalCode !== null)) process.exit(1);
      }, 400);
    });
  }

  process.on('SIGINT', () => detener());
  process.on('SIGTERM', () => detener());
  process.on('SIGHUP', () => detener()); // se cerró la terminal
  process.on('SIGBREAK', () => detener()); // Ctrl+Break en Windows
  // Último recurso: si el proceso termina por cualquier otro motivo, que no queden servicios huérfanos.
  process.on('exit', () => hijos.forEach((h) => matar(h, 'SIGKILL')));
}


async function principal() {
  const raiz = path.dirname(fileURLToPath(import.meta.url));
  const servicios = armarServicios(raiz);
  const problemas = await diagnosticar(raiz, servicios);
  if (problemas.length > 0) {
    console.error(pintar(31, '\nNo se puede arrancar todavía:\n'));
    problemas.forEach((problema, i) => console.error(`  ${i + 1}. ${problema}\n`));
    process.exit(1);
  }
  lanzar(servicios);
}

// Solo arranca cuando se lo ejecuta directamente (así las funciones de arriba se pueden importar para probarlas).
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  principal();
}
