import { ComponentFixture, TestBed } from '@angular/core/testing';

import { proveedoresDePrueba, unaMateria } from '../../testing/pruebas';
import { BuscadorMateriaComponent } from './buscador-materia.component';

describe('BuscadorMateriaComponent', () => {
  const MATERIAS = [
    unaMateria({ id: 1, nombre: 'Física II', anio: 2 }),
    unaMateria({ id: 2, nombre: 'Álgebra y Geometría Analítica', anio: 1 }),
    unaMateria({ id: 3, nombre: 'Análisis Matemático I', anio: 1 }),
  ];

  beforeEach(() => TestBed.configureTestingModule({ imports: [BuscadorMateriaComponent], providers: proveedoresDePrueba() }));

  async function montar(entradas: Record<string, unknown> = {}): Promise<ComponentFixture<BuscadorMateriaComponent>> {
    const fixture = TestBed.createComponent(BuscadorMateriaComponent);
    fixture.componentRef.setInput('idCampo', 'materia');
    fixture.componentRef.setInput('materias', MATERIAS);
    for (const [nombre, valor] of Object.entries(entradas)) {
      fixture.componentRef.setInput(nombre, valor);
    }
    await fixture.whenStable();
    return fixture;
  }

  const elemento = (f: ComponentFixture<unknown>) => f.nativeElement as HTMLElement;
  const campo = (f: ComponentFixture<unknown>) => elemento(f).querySelector<HTMLInputElement>('#materia')!;
  const opciones = (f: ComponentFixture<unknown>) =>
    Array.from(elemento(f).querySelectorAll('[role="option"]')).map((o) => o.querySelector('span')!.textContent!.trim());
  const tecla = async (f: ComponentFixture<unknown>, key: string) => {
    campo(f).dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));
    await f.whenStable();
  };
  const escribir = async (f: ComponentFixture<unknown>, texto: string) => {
    campo(f).value = texto;
    campo(f).dispatchEvent(new Event('input'));
    await f.whenStable();
  };
  const valor = (f: ComponentFixture<BuscadorMateriaComponent>) => f.componentInstance.valor();

  it('al hacer click muestra todas las materias, ordenadas por nombre', async () => {
    const fixture = await montar();
    expect(campo(fixture).getAttribute('aria-expanded')).toBe('false');

    campo(fixture).click();
    await fixture.whenStable();

    expect(campo(fixture).getAttribute('aria-expanded')).toBe('true');
    expect(opciones(fixture)).toEqual(['Álgebra y Geometría Analítica', 'Análisis Matemático I', 'Física II']);
    expect(elemento(fixture).querySelector('[role="option"]')!.getAttribute('aria-selected')).toBe('false');
  });

  it('escribir filtra sin importar mayúsculas ni acentos; Enter elige la primera y cierra la lista', async () => {
    const fixture = await montar();

    await escribir(fixture, 'ANALISIS');
    expect(opciones(fixture)).toEqual(['Análisis Matemático I']);

    await tecla(fixture, 'Enter');
    expect(valor(fixture)).toBe(3);
    expect(campo(fixture).value).toBe('Análisis Matemático I');
    expect(elemento(fixture).querySelector('[role="listbox"]')).toBeNull();
  });

  it('si nada coincide lo dice', async () => {
    const fixture = await montar();
    await escribir(fixture, 'química');

    expect(opciones(fixture)).toEqual([]);
    expect(elemento(fixture).textContent).toContain('No hay materias que coincidan con "química"');
  });

  it('se maneja con flechas y Escape cierra solo la lista', async () => {
    const fixture = await montar();

    await tecla(fixture, 'ArrowDown'); // abre y resalta la primera
    await tecla(fixture, 'ArrowDown');
    expect(campo(fixture).getAttribute('aria-activedescendant')).toBe('materia-opcion-3'); // Análisis, 2° por nombre

    const escape = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
    const propagacion = vi.spyOn(escape, 'stopPropagation');
    campo(fixture).dispatchEvent(escape);
    await fixture.whenStable();
    expect(propagacion).toHaveBeenCalled();
    expect(elemento(fixture).querySelector('[role="listbox"]')).toBeNull();
    expect(valor(fixture)).toBeNull();
  });

  it('editar el texto de una materia elegida la deselecciona', async () => {
    const fixture = await montar({ valor: 1 });
    expect(campo(fixture).value).toBe('Física II');

    await escribir(fixture, 'Física');

    expect(valor(fixture)).toBeNull();
    expect(campo(fixture).value).toBe('Física');
  });

  it('al salir del campo, si el texto es justo el nombre de una materia, queda elegida', async () => {
    const fixture = await montar();
    await escribir(fixture, 'fisica ii');

    campo(fixture).dispatchEvent(new Event('blur'));
    await fixture.whenStable();

    expect(valor(fixture)).toBe(1);
    expect(campo(fixture).value).toBe('Física II');
  });

  it('si la materia elegida ya no está entre las opciones, se borra', async () => {
    const fixture = await montar({ valor: 1 });

    fixture.componentRef.setInput('materias', MATERIAS.slice(1));
    await fixture.whenStable();

    expect(valor(fixture)).toBeNull();
    expect(campo(fixture).value).toBe('');
  });

  it('marca el error para lectores de pantalla y puede deshabilitarse', async () => {
    const fixture = await montar({ invalido: true, descripcionId: 'error-materia', deshabilitado: true });

    expect(campo(fixture).getAttribute('aria-invalid')).toBe('true');
    expect(campo(fixture).getAttribute('aria-describedby')).toBe('error-materia');
    expect(campo(fixture).disabled).toBe(true);
    expect(campo(fixture).placeholder).toBe('No hay materias para elegir');
  });
});

describe('BuscadorMateriaComponent con "todas"', () => {
  const PRIMERO = [unaMateria({ id: 1, nombre: 'Física I', anio: 1 })];
  const TODAS = [
    ...PRIMERO,
    unaMateria({ id: 2, nombre: 'Física II', anio: 2 }),
    unaMateria({ id: 3, nombre: 'Entornos Gráficos', anio: 2, electiva: true }),
  ];

  beforeEach(() => TestBed.configureTestingModule({ imports: [BuscadorMateriaComponent], providers: proveedoresDePrueba() }));

  async function montar(valor: number | null = null): Promise<ComponentFixture<BuscadorMateriaComponent>> {
    const fixture = TestBed.createComponent(BuscadorMateriaComponent);
    fixture.componentRef.setInput('idCampo', 'materia');
    fixture.componentRef.setInput('materias', PRIMERO);
    fixture.componentRef.setInput('todas', TODAS);
    fixture.componentRef.setInput('valor', valor);
    await fixture.whenStable();
    return fixture;
  }

  const campo = (f: ComponentFixture<unknown>) => (f.nativeElement as HTMLElement).querySelector<HTMLInputElement>('#materia')!;
  const filas = (f: ComponentFixture<unknown>) =>
    Array.from((f.nativeElement as HTMLElement).querySelectorAll('[role="option"]')).map((o) => o.textContent!.replace(/\s+/g, ' ').trim());

  it('al abrir la lista ofrece solo `materias`', async () => {
    const fixture = await montar();
    campo(fixture).click();
    await fixture.whenStable();

    expect(filas(fixture)).toEqual(['Física I']);
  });

  it('lo que se escribe se busca en todas, mostrando el año de cada una', async () => {
    const fixture = await montar();
    campo(fixture).value = 'fisica';
    campo(fixture).dispatchEvent(new Event('input'));
    await fixture.whenStable();

    expect(filas(fixture)).toEqual(['Física I 1° año', 'Física II 2° año']);

    campo(fixture).value = 'graf';
    campo(fixture).dispatchEvent(new Event('input'));
    await fixture.whenStable();
    expect(filas(fixture)).toEqual(['Entornos Gráficos Electiva']);
  });

  it('una materia elegida de otro año se muestra aunque no esté en `materias`', async () => {
    const fixture = await montar(3);

    expect(campo(fixture).value).toBe('Entornos Gráficos');
    expect(fixture.componentInstance.valor()).toBe(3);
  });
});
