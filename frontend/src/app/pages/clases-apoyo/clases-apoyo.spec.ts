import { HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Usuario } from '../../models/api.models';
import {
  ADMINISTRADORA, ALUMNA, API_URL, TUTOR, crearComponente, estabilizar, iniciarSesionComo, proveedoresDePrueba, textoDe, unaClase, unaMateria,
} from '../../testing/pruebas';
import { ClasesApoyoComponent } from './clases-apoyo';

describe('ClasesApoyoComponent', () => {
  let http: HttpTestingController;

  afterEach(() => {
    vi.restoreAllMocks();
    http.verify();
  });

  const OTRO_TUTOR = { legajo: '151', nombre_y_apellido: 'Otra Tutora', rol: 'tutor' as const };

  async function abrir(usuario: Usuario, clases = [unaClase()]): Promise<ComponentFixture<ClasesApoyoComponent>> {
    localStorage.clear();
    iniciarSesionComo(usuario);
    TestBed.configureTestingModule({ imports: [ClasesApoyoComponent], providers: proveedoresDePrueba() });
    http = TestBed.inject(HttpTestingController);
    const fixture = crearComponente(ClasesApoyoComponent);
    http.expectOne(`${API_URL}/clases-apoyo/`).flush(clases);
    http.expectOne(`${API_URL}/materias/`).flush([unaMateria(), unaMateria({ id: 2, nombre: 'Álgebra' })]);
    await estabilizar(fixture);
    return fixture;
  }

  const boton = (fixture: ComponentFixture<unknown>, texto: string) =>
    Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find((b) => b.textContent?.includes(texto));
  const escribir = (fixture: ComponentFixture<unknown>, selector: string, valor: string) => {
    const campo = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>(selector)!;
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
  };

  it('muestra materia, tutor, horario y aula cuando llegan los datos', async () => {
    const fixture = await abrir(ALUMNA);

    const texto = textoDe(fixture);
    expect(texto).toContain('Algoritmos y Estructuras de Datos');
    expect(texto).toContain('Dictada por: Tomás Tutor');
    expect(texto).toContain('Lun 14:00-16:00');
    expect(texto).toContain('L-203');
  });

  it('sin clases lo dice', async () => {
    expect(textoDe(await abrir(ALUMNA, []))).toContain('No hay clases de apoyo programadas');
  });

  it('una alumna las ve pero no puede publicar, modificar ni cancelar', async () => {
    const fixture = await abrir(ALUMNA);

    expect(boton(fixture, 'Publicar clase')).toBeUndefined();
    expect(boton(fixture, 'Modificar')).toBeUndefined();
    expect(boton(fixture, 'Cancelar clase')).toBeUndefined();
  });

  it('un tutor puede publicar, y modificar/cancelar SOLO sus clases', async () => {
    const fixture = await abrir(TUTOR, [unaClase({ id: 1 }), unaClase({ id: 2, tutor: OTRO_TUTOR })]);

    expect(boton(fixture, 'Publicar clase')).toBeTruthy();
    expect(fixture.nativeElement.querySelectorAll('button.bg-rose-50')).toHaveLength(1); // "Cancelar clase" solo en la propia
  });

  it('un administrador puede modificar/cancelar todas, pero no publicar (necesitaría indicar un tutor)', async () => {
    const fixture = await abrir(ADMINISTRADORA, [unaClase({ id: 1 }), unaClase({ id: 2, tutor: OTRO_TUTOR })]);

    expect(boton(fixture, 'Publicar clase')).toBeUndefined();
    expect(fixture.nativeElement.querySelectorAll('button.bg-rose-50')).toHaveLength(2);
  });

  it('publicar: manda materia, horario y aula (sin tutor, lo pone el backend) y vuelve a cargar sin parpadear', async () => {
    const fixture = await abrir(TUTOR, []);

    boton(fixture, 'Publicar clase')!.click();
    fixture.detectChanges();
    const materia = (fixture.nativeElement as HTMLElement).querySelector<HTMLSelectElement>('#clase-materia')!;
    materia.value = materia.options[1].value; // la primera materia real (la 0 es "Seleccionar...")
    materia.dispatchEvent(new Event('change'));
    escribir(fixture, '#clase-horario', ' Lun 14:00-16:00 ');
    escribir(fixture, '#clase-aula', 'L-203');
    boton(fixture, 'Guardar')!.click();

    const peticion = http.expectOne(`${API_URL}/clases-apoyo/`);
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({ materia_id: 1, horario: 'Lun 14:00-16:00', aula: 'L-203' });
    peticion.flush(unaClase(), { status: 201, statusText: 'Created' });

    const recarga = http.expectOne(`${API_URL}/clases-apoyo/`); // recarga la lista
    expect(textoDe(fixture)).not.toContain('Buscando clases'); // sin taparla con el spinner
    recarga.flush([unaClase()]);
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Clase publicada.');
    expect(textoDe(fixture)).toContain('Lun 14:00-16:00');
  });

  it('publicar con campos vacíos avisa y no llama a la API', async () => {
    const fixture = await abrir(TUTOR, []);

    boton(fixture, 'Publicar clase')!.click();
    fixture.detectChanges();
    boton(fixture, 'Guardar')!.click();
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Completá la materia, el horario y el aula.');
    http.expectNone(`${API_URL}/clases-apoyo/`);
  });

  it('modificar abre el formulario con los datos actuales y manda un PATCH', async () => {
    const fixture = await abrir(TUTOR, [unaClase({ id: 3 })]);

    boton(fixture, 'Modificar')!.click();
    await estabilizar(fixture); // ngModel escribe el valor en el campo un instante después de dibujarlo
    expect((fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>('#clase-aula')!.value).toBe('L-203');
    escribir(fixture, '#clase-aula', 'B-101');
    boton(fixture, 'Guardar')!.click();

    const peticion = http.expectOne(`${API_URL}/clases-apoyo/3/`);
    expect(peticion.request.method).toBe('PATCH');
    expect(peticion.request.body).toEqual({ materia_id: 1, horario: 'Lun 14:00-16:00', aula: 'B-101' });
    peticion.flush(unaClase({ id: 3, aula: 'B-101' }));
    http.expectOne(`${API_URL}/clases-apoyo/`).flush([unaClase({ id: 3, aula: 'B-101' })]);
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Clase actualizada.');
    expect(textoDe(fixture)).toContain('B-101');
  });

  it('el backend puede rechazar el formulario y se muestra el motivo dentro del formulario', async () => {
    const fixture = await abrir(TUTOR, []);
    boton(fixture, 'Publicar clase')!.click();
    fixture.detectChanges();
    const materia = (fixture.nativeElement as HTMLElement).querySelector<HTMLSelectElement>('#clase-materia')!;
    materia.value = materia.options[1].value;
    materia.dispatchEvent(new Event('change'));
    escribir(fixture, '#clase-horario', 'Lunes por la tarde muy tarde');
    escribir(fixture, '#clase-aula', 'L-203');
    boton(fixture, 'Guardar')!.click();

    http.expectOne(`${API_URL}/clases-apoyo/`).flush({ horario: ['Asegúrese de que este valor tenga como máximo 20 caracteres.'] }, { status: 400, statusText: 'Bad Request' });
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Horario: Asegúrese de que este valor tenga como máximo 20 caracteres.');
    expect(boton(fixture, 'Guardar')).toBeTruthy(); // el formulario sigue abierto para corregir
  });

  it('cancelar una clase pide confirmación y la saca de la lista', async () => {
    const fixture = await abrir(TUTOR, [unaClase({ id: 3 })]);
    const confirmar = vi.spyOn(window, 'confirm').mockReturnValue(true);

    boton(fixture, 'Cancelar clase')!.click();
    const peticion = http.expectOne(`${API_URL}/clases-apoyo/3/`);
    expect(peticion.request.method).toBe('DELETE');
    peticion.flush(null, { status: 204, statusText: 'No Content' });
    await estabilizar(fixture);

    expect(confirmar).toHaveBeenCalled();
    expect(textoDe(fixture)).toContain('Clase cancelada.');
    expect(textoDe(fixture)).toContain('No hay clases de apoyo programadas');
  });

  it('si no confirma, la clase no se cancela', async () => {
    const fixture = await abrir(TUTOR, [unaClase({ id: 3 })]);
    vi.spyOn(window, 'confirm').mockReturnValue(false);

    boton(fixture, 'Cancelar clase')!.click();

    http.expectNone(`${API_URL}/clases-apoyo/3/`);
  });

  it('filtrar por materia vuelve a pedir las clases de esa materia', async () => {
    const fixture = await abrir(ALUMNA);

    const filtro = (fixture.nativeElement as HTMLElement).querySelector<HTMLSelectElement>('#filtro-materia')!;
    filtro.value = filtro.options[2].value; // la segunda materia
    filtro.dispatchEvent(new Event('change'));

    const peticion = http.expectOne((r) => r.url === `${API_URL}/clases-apoyo/`);
    expect(peticion.request.params.get('materia')).toBe('2');
    peticion.flush([]);
    await estabilizar(fixture);
    expect(textoDe(fixture)).toContain('No hay clases de apoyo programadas');
  });
});
