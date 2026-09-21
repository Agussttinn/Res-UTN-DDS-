import { HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ADMINISTRADORA, API_URL, crearComponente, estabilizar, iniciarSesionComo, proveedoresDePrueba, textoDe, unMaterial } from '../../testing/pruebas';
import { AdminPanelComponent } from './admin-panel';

describe('AdminPanelComponent', () => {
  let http: HttpTestingController;

  const pendiente = (id: number, titulo: string) =>
    unMaterial({ id, titulo, validacion: false, usuario: { legajo: '200', nombre_y_apellido: 'Ana Alumna', rol: 'alumno' }, comentario: 'Con ejercicios resueltos' });

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

  async function abrir(pendientes: ReturnType<typeof pendiente>[]): Promise<ComponentFixture<AdminPanelComponent>> {
    const fixture = crearComponente(AdminPanelComponent);
    http.expectOne(`${API_URL}/materiales/pendientes/`).flush(pendientes);
    await estabilizar(fixture);
    return fixture;
  }

  const boton = (fixture: ComponentFixture<unknown>, texto: string) =>
    Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find((b) => b.textContent?.trim() === texto)!;

  it('muestra la cola de pendientes cuando llegan los datos, con autora, legajo y fecha', async () => {
    const fixture = crearComponente(AdminPanelComponent);
    expect(textoDe(fixture)).toContain('Consultando documentos pendientes');

    http.expectOne(`${API_URL}/materiales/pendientes/`).flush([pendiente(7, 'Resumen Unidad 1')]);
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
    await estabilizar(fixture);

    const texto = textoDe(fixture);
    expect(texto).toContain('"Resumen Unidad 1" fue aprobado');
    expect(texto).toContain('Parcial 2024'); // el otro sigue en la cola
    expect(fixture.nativeElement.querySelectorAll('h3')).toHaveLength(1);
  });

  it('rechazar pide confirmación: si se cancela no pasa nada', async () => {
    const fixture = await abrir([pendiente(7, 'Resumen Unidad 1')]);
    const confirmar = vi.spyOn(window, 'confirm').mockReturnValue(false);

    boton(fixture, 'Rechazar').click();

    expect(confirmar).toHaveBeenCalledWith(expect.stringContaining('Resumen Unidad 1'));
    http.expectNone(`${API_URL}/materiales/7/moderar/`);
  });

  it('rechazar confirmado manda la acción y saca el apunte', async () => {
    const fixture = await abrir([pendiente(7, 'Resumen Unidad 1')]);
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    boton(fixture, 'Rechazar').click();
    const peticion = http.expectOne(`${API_URL}/materiales/7/moderar/`);
    expect(peticion.request.body).toEqual({ accion: 'rechazar' });
    peticion.flush({ detalle: 'Material rechazado y eliminado.' });
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('fue rechazado y eliminado');
    expect(textoDe(fixture)).toContain('No hay documentos pendientes');
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
    await estabilizar(fixture);

    expect(textoDe(fixture)).toContain('Esta acción es solo para administradores.');
    expect(boton(fixture, 'Reintentar')).toBeTruthy();
  });
});
