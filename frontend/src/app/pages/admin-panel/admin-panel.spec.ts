import { HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ADMINISTRADORA, API_URL, crearComponente, estabilizar, iniciarSesionComo, proveedoresDePrueba, textoDe, unMaterial } from '../../testing/pruebas';
import { AdminPanelComponent } from './admin-panel';

describe('AdminPanelComponent', () => {
  let http: HttpTestingController;

  const pendiente = (id: number, titulo: string) =>
    unMaterial({ id, titulo, estado: 'pendiente', validacion: false, usuario: { legajo: '200', nombre_y_apellido: 'Ana Alumna', rol: 'alumno' }, comentario: 'Con ejercicios resueltos' });

  beforeEach(() => {
    localStorage.clear();
    iniciarSesionComo(ADMINISTRADORA);
    TestBed.configureTestingModule({ imports: [AdminPanelComponent], providers: proveedoresDePrueba() });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    http.verify();
  });

  async function abrir(
    pendientes: ReturnType<typeof pendiente>[],
    todos: ReturnType<typeof unMaterial>[] = []
  ): Promise<ComponentFixture<AdminPanelComponent>> {
    const fixture = crearComponente(AdminPanelComponent);
    http.expectOne(`${API_URL}/materiales/pendientes/`).flush(pendientes);
    http.expectOne(`${API_URL}/materiales/`).flush(todos);
    await estabilizar(fixture);
    return fixture;
  }

  const boton = (fixture: ComponentFixture<unknown>, texto: string) =>
    Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find((b) => b.textContent?.trim() === texto)!;

  it('muestra la cola de pendientes cuando llegan los datos, con autora, legajo y fecha', async () => {
    const fixture = crearComponente(AdminPanelComponent);
    expect(textoDe(fixture)).toContain('Consultando documentos pendientes');

    http.expectOne(`${API_URL}/materiales/pendientes/`).flush([pendiente(7, 'Resumen Unidad 1')]);
    http.expectOne(`${API_URL}/materiales/`).flush([]);
    await estabilizar(fixture);

    const texto = textoDe(fixture);
    expect(texto).toContain('Resumen Unidad 1');
    expect(texto).toContain('Con ejercicios resueltos');
    expect(texto).toContain('Enviado por Ana Alumna (legajo 200) el 21/09/2026');
    expect(texto).toContain('Previsualizar');
  });

  it('sin pendientes lo dice', async () => {
    expect(textoDe(await abrir([]))).toContain('No hay documentos pendientes de revisión');
  });

  it('aprobar: manda la acción, saca el apunte de la cola y avisa', async () => {
    const fixture = await abrir([pendiente(7, 'Resumen Unidad 1'), pendiente(8, 'Parcial 2024')]);

    boton(fixture, 'Aprobar').click();
    const peticion = http.expectOne(`${API_URL}/materiales/7/moderar/`);
    expect(peticion.request.body).toEqual({ accion: 'aprobar' });
    peticion.flush(unMaterial({ id: 7 }));
    http.expectOne(`${API_URL}/materiales/`).flush([]); // recarga la lista de aprobados
    await estabilizar(fixture);

    const texto = textoDe(fixture);
    expect(texto).toContain('"Resumen Unidad 1" fue aprobado');
    expect(texto).toContain('Parcial 2024'); // el otro sigue en la cola
    expect(fixture.nativeElement.querySelectorAll('h3')).toHaveLength(1);
  });

  const campoMotivo = (fixture: ComponentFixture<unknown>) =>
    (fixture.nativeElement as HTMLElement).querySelector<HTMLTextAreaElement>('#motivo-rechazo');
  const escribirMotivo = async (fixture: ComponentFixture<unknown>, texto: string) => {
    const campo = campoMotivo(fixture)!;
    campo.value = texto;
    campo.dispatchEvent(new Event('input'));
    await estabilizar(fixture);
  };

  it('rechazar abre una ventana para escribir el motivo (no usa el cuadro del navegador)', async () => {
    const fixture = await abrir([pendiente(7, 'Resumen Unidad 1')]);
    const pedir = vi.spyOn(window, 'prompt');

    boton(fixture, 'Rechazar').click();
    await estabilizar(fixture);

    expect(pedir).not.toHaveBeenCalled();
    expect(campoMotivo(fixture)).toBeTruthy();
    expect(textoDe(fixture)).toContain('Rechazar apunte');
    http.expectNone(`${API_URL}/materiales/7/moderar/`);
  });

  it('si se cancela la ventana no pasa nada', async () => {
    const fixture = await abrir([pendiente(7, 'Resumen Unidad 1')]);

    boton(fixture, 'Rechazar').click();
    await estabilizar(fixture);
    boton(fixture, 'Cancelar').click();
    await estabilizar(fixture);

    expect(campoMotivo(fixture)).toBeNull();
    http.expectNone(`${API_URL}/materiales/7/moderar/`);
  });

  it('rechazar manda el motivo, saca el apunte de la cola y avisa que el autor puede reenviarlo', async () => {
    const fixture = await abrir([pendiente(7, 'Resumen Unidad 1')]);

    boton(fixture, 'Rechazar').click();
    await estabilizar(fixture);
    await escribirMotivo(fixture, '  Ilegible  ');
    boton(fixture, 'Rechazar apunte').click();
    const peticion = http.expectOne(`${API_URL}/materiales/7/moderar/`);
    expect(peticion.request.body).toEqual({ accion: 'rechazar', motivo: 'Ilegible' });
    peticion.flush(unMaterial({ id: 7, estado: 'rechazado', validacion: false, motivo_rechazo: 'Ilegible' }));
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('fue rechazado');
    expect(textoDe(fixture)).toContain('puede corregirlo y reenviarlo');
    expect(textoDe(fixture)).toContain('No hay documentos pendientes');
    expect(campoMotivo(fixture)).toBeNull();
  });

  it('el motivo es opcional: se puede rechazar sin escribirlo', async () => {
    const fixture = await abrir([pendiente(7, 'Resumen Unidad 1')]);

    boton(fixture, 'Rechazar').click();
    await estabilizar(fixture);
    boton(fixture, 'Rechazar apunte').click();

    const peticion = http.expectOne(`${API_URL}/materiales/7/moderar/`);
    expect(peticion.request.body).toEqual({ accion: 'rechazar' });
    peticion.flush(unMaterial({ id: 7, estado: 'rechazado', validacion: false }));
  });

  it('archivar: lista los aprobados, pide confirmación y manda la acción', async () => {
    const fixture = await abrir([], [unMaterial({ id: 9, titulo: 'Final 2023' }), unMaterial({ id: 10, titulo: 'Ya archivado', estado: 'archivado' })]);
    expect(textoDe(fixture)).toContain('Final 2023');
    expect(textoDe(fixture)).not.toContain('Ya archivado');

    vi.spyOn(window, 'confirm').mockReturnValue(true);
    boton(fixture, 'Archivar').click();
    const peticion = http.expectOne(`${API_URL}/materiales/9/moderar/`);
    expect(peticion.request.body).toEqual({ accion: 'archivar' });
    peticion.flush(unMaterial({ id: 9, estado: 'archivado' }));
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('"Final 2023" fue archivado');
    expect(fixture.nativeElement.querySelectorAll('h3')).toHaveLength(0);
  });

  it('volver a pendiente: deshace una aprobación hecha sin querer y el apunte reaparece en la cola', async () => {
    const fixture = await abrir([], [unMaterial({ id: 9, titulo: 'Final 2023' })]);

    boton(fixture, 'Volver a pendiente').click();
    const peticion = http.expectOne(`${API_URL}/materiales/9/moderar/`);
    expect(peticion.request.body).toEqual({ accion: 'desaprobar' });
    peticion.flush(unMaterial({ id: 9, titulo: 'Final 2023', estado: 'pendiente', validacion: false }));
    http.expectOne(`${API_URL}/materiales/pendientes/`).flush([pendiente(9, 'Final 2023')]);
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('volvió a pendiente');
    expect(boton(fixture, 'Aprobar')).toBeTruthy();
    expect(boton(fixture, 'Volver a pendiente')).toBeUndefined();
  });

  it('un aprobado también se puede rechazar con motivo', async () => {
    const fixture = await abrir([], [unMaterial({ id: 9, titulo: 'Final 2023' })]);

    boton(fixture, 'Rechazar').click();
    await estabilizar(fixture);
    boton(fixture, 'Rechazar apunte').click();

    const peticion = http.expectOne(`${API_URL}/materiales/9/moderar/`);
    expect(peticion.request.body).toEqual({ accion: 'rechazar' });
    peticion.flush(unMaterial({ id: 9, estado: 'rechazado', validacion: false }));
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('"Final 2023" fue rechazado');
    expect(fixture.nativeElement.querySelectorAll('h3')).toHaveLength(0);
  });

  describe('filtro por antigüedad', () => {
    const haceDias = (dias: number) => new Date(Date.now() - dias * 24 * 60 * 60 * 1000).toISOString();
    const titulos = (fixture: ComponentFixture<unknown>) =>
      Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('h3')).map((h) => h.textContent?.trim());
    const elegir = async (fixture: ComponentFixture<unknown>, id: string, valor: string) => {
      const select = (fixture.nativeElement as HTMLElement).querySelector<HTMLSelectElement>(id)!;
      select.value = valor;
      select.dispatchEvent(new Event('change'));
      await estabilizar(fixture);
    };
    const cola = () => [
      { ...pendiente(1, 'Reciente'), fecha_de_carga: haceDias(2) },
      { ...pendiente(2, 'Del mes'), fecha_de_carga: haceDias(20) },
      { ...pendiente(3, 'Viejo'), fecha_de_carga: haceDias(90) },
      { ...pendiente(4, 'Muy viejo'), fecha_de_carga: haceDias(300) }
    ];

    it('por defecto muestra todo, con los más antiguos primero', async () => {
      const fixture = await abrir(cola());
      expect(titulos(fixture)).toEqual(['Muy viejo', 'Viejo', 'Del mes', 'Reciente']);
    });

    it('se puede ordenar con los más recientes primero', async () => {
      const fixture = await abrir(cola());

      await elegir(fixture, '#orden-apuntes', 'recientes');

      expect(titulos(fixture)).toEqual(['Reciente', 'Del mes', 'Viejo', 'Muy viejo']);
    });

    it('filtra por los últimos 7 días, los últimos 30, más de 30 y más de 6 meses', async () => {
      const fixture = await abrir(cola());

      await elegir(fixture, '#filtro-antiguedad', 'semana');
      expect(titulos(fixture)).toEqual(['Reciente']);
      await elegir(fixture, '#filtro-antiguedad', 'mes');
      expect(titulos(fixture)).toEqual(['Del mes', 'Reciente']);
      await elegir(fixture, '#filtro-antiguedad', 'mas-mes');
      expect(titulos(fixture)).toEqual(['Muy viejo', 'Viejo']);
      await elegir(fixture, '#filtro-antiguedad', 'mas-6-meses');
      expect(titulos(fixture)).toEqual(['Muy viejo']);
      await elegir(fixture, '#filtro-antiguedad', 'todas');
      expect(titulos(fixture)).toHaveLength(4);
    });

    it('si ninguno coincide con el filtro lo dice, sin confundirlo con "no hay pendientes"', async () => {
      const fixture = await abrir([{ ...pendiente(1, 'Reciente'), fecha_de_carga: haceDias(2) }]);

      await elegir(fixture, '#filtro-antiguedad', 'mas-6-meses');

      expect(textoDe(fixture)).toContain('Ningún apunte pendiente coincide con ese filtro de antigüedad');
      expect(textoDe(fixture)).not.toContain('No hay documentos pendientes de revisión');
    });

    it('el mismo filtro vale para la lista de aprobados (para archivar los viejos) y muestra su fecha', async () => {
      const aprobados = [
        unMaterial({ id: 10, titulo: 'Aprobado nuevo', estado: 'aprobado', fecha_de_carga: haceDias(3) }),
        unMaterial({ id: 11, titulo: 'Aprobado viejo', estado: 'aprobado', fecha_de_carga: haceDias(400) })
      ];
      const fixture = await abrir([], aprobados);
      expect(textoDe(fixture)).toContain('subido el');

      await elegir(fixture, '#filtro-antiguedad', 'mas-6-meses');

      expect(titulos(fixture)).toEqual(['Aprobado viejo']);
    });
  });

  it('mientras procesa un apunte sus botones se deshabilitan (evita el doble clic)', async () => {
    const fixture = await abrir([pendiente(7, 'Resumen Unidad 1')]);

    boton(fixture, 'Aprobar').click();
    fixture.detectChanges();

    expect(boton(fixture, 'Aprobar').disabled).toBe(true);
    expect(boton(fixture, 'Rechazar').disabled).toBe(true);
    http.expectOne(`${API_URL}/materiales/7/moderar/`).flush({}, { status: 500, statusText: 'Error' });
  });

  it('si la API rechaza la acción muestra el motivo y deja el apunte en la cola', async () => {
    const fixture = await abrir([pendiente(7, 'Resumen Unidad 1')]);

    boton(fixture, 'Aprobar').click();
    http.expectOne(`${API_URL}/materiales/7/moderar/`).flush({ detail: 'Esta acción es solo para administradores.' }, { status: 403, statusText: 'Forbidden' });
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Esta acción es solo para administradores.');
  });

  it('si no puede cargar la cola muestra el error y permite reintentar', async () => {
    const fixture = crearComponente(AdminPanelComponent);
    http.expectOne(`${API_URL}/materiales/pendientes/`).flush({ detail: 'Esta acción es solo para administradores.' }, { status: 403, statusText: 'Forbidden' });
    http.expectOne(`${API_URL}/materiales/`).flush({}, { status: 403, statusText: 'Forbidden' });
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Esta acción es solo para administradores.');
    expect(boton(fixture, 'Reintentar')).toBeTruthy();
  });
});
