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

  it('mientras carga muestra "Cargando", y cuando llegan los datos la pantalla SE ACTUALIZA', async () => {
    const fixture = crearComponente(MateriasComponent);
    expect(textoDe(fixture)).toContain('Cargando asignaturas');

    http.expectOne(`${API_URL}/materias/`).flush([
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
    http.expectOne(`${API_URL}/materias/`).flush([unaMateria({ id: 5 })]);
    await estabilizar(fixture);

    const enlace = (fixture.nativeElement as HTMLElement).querySelector<HTMLAnchorElement>('a[href]');
    expect(enlace?.getAttribute('href')).toBe('/materiales/5');
  });

  it('sin materias explica cómo cargarlas', async () => {
    const fixture = crearComponente(MateriasComponent);
    http.expectOne(`${API_URL}/materias/`).flush([]);
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('No hay materias registradas');
  });

  it('si falla, muestra el motivo y permite reintentar', async () => {
    const fixture = crearComponente(MateriasComponent);
    http.expectOne(`${API_URL}/materias/`).flush({}, { status: 500, statusText: 'Error' });
    await estabilizar(fixture);
    expect(textoDe(fixture)).toContain('No se pudieron cargar las materias.');

    const reintentar = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find((b) => b.textContent?.includes('Reintentar'));
    reintentar?.click();
    http.expectOne(`${API_URL}/materias/`).flush([unaMateria()]);
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Algoritmos y Estructuras de Datos');
    expect(textoDe(fixture)).not.toContain('No se pudieron cargar');
  });
});
