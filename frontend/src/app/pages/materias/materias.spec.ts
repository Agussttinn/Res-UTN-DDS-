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
    expect(texto).toContain('1° Año');
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

  it('la búsqueda filtra por nombre sin importar acentos', async () => {
    const fixture = crearComponente(MateriasComponent);
    pedidoDeMaterias().flush([unaMateria(), unaMateria({ id: 2, nombre: 'Álgebra y Geometría Analítica' })]);
    await estabilizar(fixture);

    const buscador = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>('input[type="search"]')!;
    buscador.value = 'algebra';
    buscador.dispatchEvent(new Event('input'));
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Álgebra y Geometría Analítica');
    expect(textoDe(fixture)).not.toContain('Algoritmos y Estructuras de Datos');

    buscador.value = 'zzz';
    buscador.dispatchEvent(new Event('input'));
    await estabilizar(fixture);
    expect(textoDe(fixture)).toContain('Ninguna materia coincide con "zzz"');
  });
});
