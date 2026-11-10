import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DialogoConfirmacionComponent } from './dialogo-confirmacion.component';

describe('DialogoConfirmacionComponent', () => {
  async function montar(peligro = false): Promise<ComponentFixture<DialogoConfirmacionComponent>> {
    TestBed.configureTestingModule({ imports: [DialogoConfirmacionComponent] });
    const fixture = TestBed.createComponent(DialogoConfirmacionComponent);
    fixture.componentRef.setInput('titulo', 'Cancelar clase');
    fixture.componentRef.setInput('mensaje', '¿Seguro?');
    fixture.componentRef.setInput('textoConfirmar', 'Sí, cancelar');
    fixture.componentRef.setInput('peligro', peligro);
    await fixture.whenStable();
    return fixture;
  }

  const el = (f: ComponentFixture<unknown>) => f.nativeElement as HTMLElement;

  it('muestra el título, el mensaje y los dos botones', async () => {
    const fixture = await montar();

    expect(el(fixture).textContent).toContain('Cancelar clase');
    expect(el(fixture).textContent).toContain('¿Seguro?');
    expect(el(fixture).textContent).toContain('Volver');
    expect(el(fixture).textContent).toContain('Sí, cancelar');
  });

  it('el foco arranca en "Volver" para no confirmar sin querer con Enter', async () => {
    TestBed.configureTestingModule({ imports: [DialogoConfirmacionComponent] });
    const fixture = TestBed.createComponent(DialogoConfirmacionComponent);
    fixture.componentRef.setInput('titulo', 'x');
    fixture.componentRef.setInput('mensaje', 'y');
    document.body.appendChild(fixture.nativeElement);
    await fixture.whenStable();

    expect(document.activeElement?.textContent?.trim()).toBe('Volver');
    fixture.nativeElement.remove();
  });

  it('emite confirmado y cancelado según el botón', async () => {
    const fixture = await montar();
    const confirmado = vi.fn();
    const cancelado = vi.fn();
    fixture.componentInstance.confirmado.subscribe(confirmado);
    fixture.componentInstance.cancelado.subscribe(cancelado);
    const [volver, confirmar] = Array.from(el(fixture).querySelectorAll('button'));

    confirmar.click();
    expect(confirmado).toHaveBeenCalledTimes(1);
    volver.click();
    expect(cancelado).toHaveBeenCalledTimes(1);
  });

  it('Escape y el clic fuera de la ventana cancelan; el clic adentro no', async () => {
    const fixture = await montar();
    const cancelado = vi.fn();
    fixture.componentInstance.cancelado.subscribe(cancelado);

    el(fixture).querySelector('[role=alertdialog]')!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(cancelado).toHaveBeenCalledTimes(1);

    el(fixture).querySelector<HTMLElement>('[role=alertdialog]')!.click();
    expect(cancelado).toHaveBeenCalledTimes(1);

    el(fixture).querySelector<HTMLElement>('.fixed')!.click();
    expect(cancelado).toHaveBeenCalledTimes(2);
  });

  it('la acción destructiva pinta el botón de confirmar en rojo', async () => {
    const fixture = await montar(true);

    const confirmar = Array.from(el(fixture).querySelectorAll('button'))[1];
    expect(confirmar.className).toContain('bg-rose-600');
  });
});
