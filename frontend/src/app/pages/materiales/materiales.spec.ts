import { HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';

import { Ponderacion, Usuario } from '../../models/api.models';
import {
  ALUMNA, API_URL, crearComponente, estabilizar, iniciarSesionComo, proveedoresDePrueba, textoDe, unMaterial, unaMateria,
} from '../../testing/pruebas';
import { MaterialesComponent } from './materiales';

describe('MaterialesComponent', () => {
  let http: HttpTestingController;

  afterEach(() => {
    vi.restoreAllMocks();
    http.verify();
  });

  const AUTORA_ALUMNA = { legajo: ALUMNA.legajo, nombre_y_apellido: ALUMNA.nombre_y_apellido, rol: 'alumno' as const };

  interface Opciones {
    usuario?: Usuario;
    /** Id de materia en la URL (/materiales/:materiaId). Vacío = todas las materias. */
    materiaId?: string;
    materiales?: ReturnType<typeof unMaterial>[];
    votos?: Ponderacion[];
  }

  async function abrir({ usuario = ALUMNA, materiaId = '1', materiales = [], votos = [] }: Opciones = {}): Promise<ComponentFixture<MaterialesComponent>> {
    localStorage.clear();
    iniciarSesionComo(usuario);
    TestBed.configureTestingModule({
      imports: [MaterialesComponent],
      providers: proveedoresDePrueba({
        provide: ActivatedRoute,
        useValue: { paramMap: of(convertToParamMap(materiaId ? { materiaId } : {})) },
      }),
    });
    http = TestBed.inject(HttpTestingController);

    const fixture = crearComponente(MaterialesComponent);
    http.expectOne(`${API_URL}/materias/`).flush([unaMateria(), unaMateria({ id: 2, nombre: 'Álgebra y Geometría Analítica' })]);
    http.expectOne(`${API_URL}/ponderaciones/`).flush(votos);
    http.expectOne((r) => r.url === `${API_URL}/materiales/`).flush(materiales);
    await estabilizar(fixture);
    return fixture;
  }

  const elemento = (fixture: ComponentFixture<unknown>) => fixture.nativeElement as HTMLElement;
  const boton = (fixture: ComponentFixture<unknown>, texto: string) =>
    Array.from(elemento(fixture).querySelectorAll('button')).find((b) => b.textContent?.trim().includes(texto));
  const estrellas = (fixture: ComponentFixture<unknown>) => Array.from(elemento(fixture).querySelectorAll<HTMLButtonElement>('app-estrellas button'));
  const escribir = (fixture: ComponentFixture<unknown>, selector: string, valor: string) => {
    const campo = elemento(fixture).querySelector<HTMLInputElement>(selector)!;
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
  };
  const elegirArchivo = (fixture: ComponentFixture<unknown>, archivo: File) => {
    const campo = elemento(fixture).querySelector<HTMLInputElement>('#nuevo-archivo')!;
    Object.defineProperty(campo, 'files', { value: [archivo], configurable: true });
    campo.dispatchEvent(new Event('change'));
  };
  const voto = (materialId: number, valor: number): Ponderacion => ({
    material: unMaterial({ id: materialId }),
    usuario: AUTORA_ALUMNA,
    valor,
    fecha: '2026-09-21T15:00:00-03:00',
  });

  describe('lista', () => {
    it('cuando llegan los datos la pantalla SE ACTUALIZA con todos los campos del apunte', async () => {
      localStorage.clear();
      iniciarSesionComo(ALUMNA);
      TestBed.configureTestingModule({
        imports: [MaterialesComponent],
        providers: proveedoresDePrueba({ provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({})) } }),
      });
      http = TestBed.inject(HttpTestingController);
      const fixture = crearComponente(MaterialesComponent);
      expect(textoDe(fixture)).toContain('Buscando recursos');

      http.expectOne(`${API_URL}/materias/`).flush([]);
      http.expectOne(`${API_URL}/ponderaciones/`).flush([]);
      http.expectOne((r) => r.url === `${API_URL}/materiales/`).flush([
        unMaterial({ comentario: 'Con ejercicios resueltos', promedio_ponderacion: 3.5, cantidad_ponderaciones: 2 }),
      ]);
      await estabilizar(fixture);

      const texto = textoDe(fixture);
      expect(texto).not.toContain('Buscando recursos');
      expect(texto).toContain('Resumen Unidad 1');
      expect(texto).toContain('Con ejercicios resueltos');
      expect(texto).toContain('Algoritmos y Estructuras de Datos');
      expect(texto).toContain('Subido por: Beto Alumno');
      expect(texto).toContain('21/09/2026');
      expect(texto).toContain('3.5 (2 votos)');
      expect(elemento(fixture).querySelector('a[href="http://127.0.0.1:8000/media/materiales/abc.pdf"]')).toBeTruthy();
    });

    it('con una materia en la URL pide solo los apuntes de esa materia y la nombra en el título', async () => {
      localStorage.clear();
      iniciarSesionComo(ALUMNA);
      TestBed.configureTestingModule({
        imports: [MaterialesComponent],
        providers: proveedoresDePrueba({ provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ materiaId: '2' })) } }),
      });
      http = TestBed.inject(HttpTestingController);
      const fixture = crearComponente(MaterialesComponent);

      http.expectOne(`${API_URL}/materias/`).flush([unaMateria(), unaMateria({ id: 2, nombre: 'Álgebra y Geometría Analítica' })]);
      http.expectOne(`${API_URL}/ponderaciones/`).flush([]);
      const peticion = http.expectOne((r) => r.url === `${API_URL}/materiales/`);
      expect(peticion.request.params.get('materia')).toBe('2');
      peticion.flush([]);
      await estabilizar(fixture);

      expect(textoDe(fixture)).toContain('Apuntes de Álgebra y Geometría Analítica');
    });

    it('sin apuntes invita a compartir el primero', async () => {
      expect(textoDe(await abrir())).toContain('¡Sé el primero en compartir uno!');
    });

    it('filtra por tipo y los botones dicen los plurales en español', async () => {
      const fixture = await abrir({
        materiales: [unMaterial({ id: 1, titulo: 'Mi resumen', tipo: 'resumen' }), unMaterial({ id: 2, titulo: 'Mi parcial', tipo: 'parcial' })],
      });
      const textos = Array.from(elemento(fixture).querySelectorAll('button')).map((b) => b.textContent?.trim());
      expect(textos).toEqual(expect.arrayContaining(['Todos', 'Resúmenes', 'Parciales', 'Finales']));

      boton(fixture, 'Parciales')!.click();
      await estabilizar(fixture);
      expect(textoDe(fixture)).toContain('Mi parcial');
      expect(textoDe(fixture)).not.toContain('Mi resumen');

      boton(fixture, 'Todos')!.click();
      await estabilizar(fixture);
      expect(textoDe(fixture)).toContain('Mi resumen');
    });

    it('un apunte propio pendiente lleva la etiqueta y sus estrellas están deshabilitadas', async () => {
      const fixture = await abrir({ materiales: [unMaterial({ validacion: false, usuario: AUTORA_ALUMNA })] });

      expect(textoDe(fixture)).toContain('Pendiente de revisión');
      expect(estrellas(fixture)).toHaveLength(5);
      expect(estrellas(fixture).every((e) => e.disabled)).toBe(true);
    });

    it('no se puede puntuar el propio apunte, aunque ya esté validado', async () => {
      const fixture = await abrir({ materiales: [unMaterial({ validacion: true, usuario: AUTORA_ALUMNA })] });

      expect(estrellas(fixture).every((e) => e.disabled)).toBe(true);
      expect(textoDe(fixture)).toContain('No podés puntuar tu propio apunte.');
    });

    it('si falla la carga muestra el motivo y permite reintentar', async () => {
      localStorage.clear();
      iniciarSesionComo(ALUMNA);
      TestBed.configureTestingModule({
        imports: [MaterialesComponent],
        providers: proveedoresDePrueba({ provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({})) } }),
      });
      http = TestBed.inject(HttpTestingController);
      const fixture = crearComponente(MaterialesComponent);
      http.expectOne(`${API_URL}/materias/`).flush([]);
      http.expectOne(`${API_URL}/ponderaciones/`).flush([]);
      http.expectOne((r) => r.url === `${API_URL}/materiales/`).flush({}, { status: 500, statusText: 'Error' });
      await estabilizar(fixture);

      expect(textoDe(fixture)).toContain('No se pudieron cargar los apuntes.');
      boton(fixture, 'Reintentar')!.click();
      http.expectOne((r) => r.url === `${API_URL}/materiales/`).flush([unMaterial()]);
      await estabilizar(fixture);
      expect(textoDe(fixture)).toContain('Resumen Unidad 1');
    });
  });

  describe('estrellas', () => {
    it('resalta el voto que ya dio el usuario (lo trae el backend)', async () => {
      const fixture = await abrir({ materiales: [unMaterial({ id: 7 })], votos: [voto(7, 5)] });

      expect(textoDe(fixture)).toContain('Tu voto: 5');
    });

    it('puntuar: guarda el voto, vuelve a pedir el apunte y muestra el promedio nuevo y "Tu voto"', async () => {
      const fixture = await abrir({ materiales: [unMaterial({ id: 7 })] });

      estrellas(fixture)[3].click(); // 4 estrellas
      const guardado = http.expectOne(`${API_URL}/ponderaciones/`);
      expect(guardado.request.method).toBe('POST');
      expect(guardado.request.body).toEqual({ material_id: 7, valor: 4 }); // sin usuario: lo pone el backend
      guardado.flush(voto(7, 4), { status: 201, statusText: 'Created' });
      http.expectOne(`${API_URL}/materiales/7/`).flush(unMaterial({ id: 7, promedio_ponderacion: 4, cantidad_ponderaciones: 1 }));
      await estabilizar(fixture);

      const texto = textoDe(fixture);
      expect(texto).toContain('4 (1 voto)');
      expect(texto).toContain('Tu voto: 4');
    });

    it('si el backend rechaza el voto muestra el motivo y no cambia nada', async () => {
      const fixture = await abrir({ materiales: [unMaterial({ id: 7 })] });

      estrellas(fixture)[1].click();
      http.expectOne(`${API_URL}/ponderaciones/`).flush({ material_id: ['Solo se pueden puntuar materiales ya validados.'] }, { status: 400, statusText: 'Bad Request' });
      await estabilizar(fixture);

      expect(textoDe(fixture)).toContain('Apunte: Solo se pueden puntuar materiales ya validados.');
      expect(textoDe(fixture)).not.toContain('Tu voto');
    });
  });

  describe('subir un apunte', () => {
    const abrirModal = async (fixture: ComponentFixture<MaterialesComponent>) => {
      boton(fixture, 'Compartir Apunte')!.click();
      await estabilizar(fixture);
    };

    it('el formulario viene con la materia de la página preseleccionada', async () => {
      const fixture = await abrir({ materiaId: '2' });

      await abrirModal(fixture);

      const select = elemento(fixture).querySelector<HTMLSelectElement>('#nueva-materia')!;
      expect(select.options[select.selectedIndex].text).toBe('Álgebra y Geometría Analítica');
    });

    it('rechaza en el navegador un formato no permitido, sin subir nada', async () => {
      const fixture = await abrir();
      await abrirModal(fixture);

      elegirArchivo(fixture, new File(['x'], 'virus.exe'));
      await estabilizar(fixture);

      expect(textoDe(fixture)).toContain('Formato no permitido');
    });

    it('rechaza un archivo de más de 10 MB', async () => {
      const fixture = await abrir();
      await abrirModal(fixture);
      const enorme = new File(['x'], 'enorme.pdf');
      Object.defineProperty(enorme, 'size', { value: 10 * 1024 * 1024 + 1 });

      elegirArchivo(fixture, enorme);
      await estabilizar(fixture);

      expect(textoDe(fixture)).toContain('no puede pesar más de 10 MB');
    });

    it('sin título o sin archivo avisa y no llama a la API', async () => {
      const fixture = await abrir();
      await abrirModal(fixture);

      boton(fixture, 'Enviar a Revisión')!.click();
      await estabilizar(fixture);

      expect(textoDe(fixture)).toContain('Completá el título, seleccioná la materia y adjuntá el archivo.');
      http.expectNone((r) => r.method === 'POST');
    });

    it('envía multipart con materia_id, tipo en minúscula y el archivo (sin usuario) y recarga la lista sin parpadear', async () => {
      const fixture = await abrir({ materiaId: '1' });
      await abrirModal(fixture);
      escribir(fixture, '#nuevo-titulo', '  Resumen U1  ');
      escribir(fixture, '#nuevo-comentario', 'Con ejercicios');
      const pdf = new File(['%PDF-1.4'], 'apunte.pdf', { type: 'application/pdf' });
      elegirArchivo(fixture, pdf);

      boton(fixture, 'Enviar a Revisión')!.click();
      const peticion = http.expectOne((r) => r.method === 'POST' && r.url === `${API_URL}/materiales/`);
      const datos = peticion.request.body as FormData;
      expect(datos.get('titulo')).toBe('Resumen U1');
      expect(datos.get('tipo')).toBe('resumen');
      expect(datos.get('materia_id')).toBe('1');
      expect(datos.get('comentario')).toBe('Con ejercicios');
      expect(datos.get('archivo')).toBe(pdf);
      expect(datos.has('usuario')).toBe(false);
      expect(datos.has('usuario_id')).toBe(false);
      peticion.flush(unMaterial({ validacion: false }), { status: 201, statusText: 'Created' });

      const recarga = http.expectOne((r) => r.method === 'GET' && r.url === `${API_URL}/materiales/`);
      expect(textoDe(fixture)).not.toContain('Buscando recursos');
      recarga.flush([unMaterial({ validacion: false, usuario: AUTORA_ALUMNA })]);
      await estabilizar(fixture);

      const texto = textoDe(fixture);
      expect(texto).toContain('¡Apunte enviado!');
      expect(texto).toContain('Pendiente de revisión');
      expect(elemento(fixture).querySelector('#nuevo-titulo')).toBeNull(); // el formulario se cerró
    });

    it('si el backend rechaza el archivo muestra el motivo dentro del formulario', async () => {
      const fixture = await abrir();
      await abrirModal(fixture);
      escribir(fixture, '#nuevo-titulo', 'Resumen U1');
      elegirArchivo(fixture, new File(['x'], 'apunte.pdf'));

      boton(fixture, 'Enviar a Revisión')!.click();
      http.expectOne((r) => r.method === 'POST').flush({ archivo: ['El archivo no puede pesar más de 10 MB.'] }, { status: 400, statusText: 'Bad Request' });
      await estabilizar(fixture);

      expect(textoDe(fixture)).toContain('Archivo: El archivo no puede pesar más de 10 MB.');
      expect(elemento(fixture).querySelector('#nuevo-titulo')).toBeTruthy(); // sigue abierto para reintentar
    });
  });
});
