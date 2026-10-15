import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ALUMNA, API_URL, crearComponente, estabilizar, iniciarSesionComo, proveedoresDePrueba, textoDe, unaMateria } from '../../testing/pruebas';
import { MateriasComponent } from './materias';

describe('MateriasComponent', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    iniciarSesionComo(ALUMNA);
    TestBed.configureTestingModule({ imports: [MateriasComponent], providers: proveedoresDePrueba() });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  const pedidoDeMaterias = () => http.expectOne((r) => r.url === `${API_URL}/materias/`);
  const boton = (fixture: { nativeElement: unknown }, texto: string) =>
    Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find((b) => b.textContent?.trim() === texto)!;

  it('mientras carga muestra "Cargando", y cuando llegan los datos la pantalla SE ACTUALIZA', async () => {
    const fixture = crearComponente(MateriasComponent);
    expect(textoDe(fixture)).toContain('Cargando asignaturas');

    pedidoDeMaterias().flush([
      unaMateria(),
      unaMateria({ id: 2, nombre: 'Álgebra y Geometría Analítica', anio: 1 }),
    ]);
    await estabilizar(fixture);

    const texto = textoDe(fixture);
    expect(texto).not.toContain('Cargando asignaturas');
    expect(texto).toContain('Algoritmos y Estructuras de Datos');
    expect(texto).toContain('Álgebra y Geometría Analítica');
    expect(texto).toContain('1° año');
    expect(texto).toContain('Ingeniería en Sistemas'); // sale de materia.especialidad.nombre
  });

  it('cada materia lleva a los apuntes de esa materia', async () => {
    const fixture = crearComponente(MateriasComponent);
    pedidoDeMaterias().flush([unaMateria({ id: 5 })]);
    await estabilizar(fixture);

    const enlace = (fixture.nativeElement as HTMLElement).querySelector<HTMLAnchorElement>('a[href]');
    expect(enlace?.getAttribute('href')).toBe('/materiales/5');
  });

  it('sin materias explica cómo cargarlas', async () => {
    const fixture = crearComponente(MateriasComponent);
    pedidoDeMaterias().flush([]);
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('No hay materias registradas');
  });

  it('si falla, muestra el motivo y permite reintentar', async () => {
    const fixture = crearComponente(MateriasComponent);
    pedidoDeMaterias().flush({}, { status: 500, statusText: 'Error' });
    await estabilizar(fixture);
    expect(textoDe(fixture)).toContain('No se pudieron cargar las materias.');

    const reintentar = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find((b) => b.textContent?.includes('Reintentar'));
    reintentar?.click();
    pedidoDeMaterias().flush([unaMateria()]);
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Algoritmos y Estructuras de Datos');
    expect(textoDe(fixture)).not.toContain('No se pudieron cargar');
  });

  it('arranca en 1° año: le pide al backend las materias de ese año, sin electivas', async () => {
    const fixture = crearComponente(MateriasComponent);
    const pedido = pedidoDeMaterias();
    expect(pedido.request.params.get('anio')).toBe('1');
    expect(pedido.request.params.get('electiva')).toBe('false');
    pedido.flush([]);
    await estabilizar(fixture);

    expect(boton(fixture, '1° año').getAttribute('aria-pressed')).toBe('true');
  });

  it('al elegir otro año o las electivas vuelve a pedir las materias con ese filtro', async () => {
    const fixture = crearComponente(MateriasComponent);
    pedidoDeMaterias().flush([unaMateria()]);
    await estabilizar(fixture);

    boton(fixture, '3° año').click();
    expect(pedidoDeMaterias().request.params.get('anio')).toBe('3');

    boton(fixture, 'Electivas').click();
    const pedido = pedidoDeMaterias();
    expect(pedido.request.params.get('electiva')).toBe('true');
    pedido.flush([unaMateria({ id: 9, nombre: 'Entornos Gráficos', anio: 2, electiva: true })]);
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Entornos Gráficos');
    expect(textoDe(fixture)).toContain('Electiva');
  });

  describe('búsqueda por nombre', () => {
    const esperar = () => new Promise((resolve) => setTimeout(resolve));

    async function buscar(fixture: ReturnType<typeof crearComponente<MateriasComponent>>, texto: string) {
      const buscador = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>('#buscar-materia')!;
      buscador.value = texto;
      buscador.dispatchEvent(new Event('input'));
      await esperar(); // la demora entre teclas (en los tests es 0)
    }

    it('busca en todos los años: pide al backend por nombre, sin filtro de año', async () => {
      const fixture = crearComponente(MateriasComponent);
      fixture.componentInstance.demoraBusquedaMs = 0;
      pedidoDeMaterias().flush([unaMateria()]);
      await estabilizar(fixture);

      await buscar(fixture, 'sistemas');
      const pedido = pedidoDeMaterias();
      expect(pedido.request.params.get('buscar')).toBe('sistemas');
      expect(pedido.request.params.has('anio')).toBe(false);
      expect(pedido.request.params.has('electiva')).toBe(false);
      pedido.flush([
        unaMateria({ id: 3, nombre: 'Sistemas Operativos', anio: 2 }),
        unaMateria({ id: 9, nombre: 'Sistemas de Información Geográfica', anio: 2, electiva: true }),
      ]);
      await estabilizar(fixture);

      const texto = textoDe(fixture);
      expect(texto).toContain('Resultados de "sistemas" en todos los años');
      expect(texto).toContain('Sistemas Operativos');
      expect(texto).toContain('2° año');
      expect(texto).toContain('Electiva');
      expect(boton(fixture, '1° año').getAttribute('aria-pressed')).toBe('false');
    });

    it('sin resultados lo dice, y elegir un año sale de la búsqueda', async () => {
      const fixture = crearComponente(MateriasComponent);
      fixture.componentInstance.demoraBusquedaMs = 0;
      pedidoDeMaterias().flush([unaMateria()]);
      await estabilizar(fixture);

      await buscar(fixture, 'zzz');
      pedidoDeMaterias().flush([]);
      await estabilizar(fixture);
      expect(textoDe(fixture)).toContain('Ninguna materia coincide con "zzz"');

      boton(fixture, '2° año').click();
      expect(pedidoDeMaterias().request.params.get('anio')).toBe('2');
      await estabilizar(fixture);
      expect((fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>('#buscar-materia')!.value).toBe('');
    });

    it('al seguir escribiendo espera y hace una sola consulta', async () => {
      const fixture = crearComponente(MateriasComponent);
      fixture.componentInstance.demoraBusquedaMs = 20;
      pedidoDeMaterias().flush([]);
      await estabilizar(fixture);

      const buscador = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>('#buscar-materia')!;
      for (const texto of ['a', 'al', 'alg']) {
        buscador.value = texto;
        buscador.dispatchEvent(new Event('input'));
      }
      http.expectNone((r) => r.url === `${API_URL}/materias/`);
      await new Promise((resolve) => setTimeout(resolve, 40));

      const pedido = pedidoDeMaterias();
      expect(pedido.request.params.get('buscar')).toBe('alg');
      pedido.flush([]);
    });
  });
});
