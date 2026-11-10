import { HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { API_URL, proveedoresDePrueba } from '../../testing/pruebas';
import { RecuperarComponent } from './recuperar';

describe('RecuperarComponent', () => {
  let http: HttpTestingController;

  async function montar(): Promise<ComponentFixture<RecuperarComponent>> {
    localStorage.clear();
    TestBed.configureTestingModule({ imports: [RecuperarComponent], providers: proveedoresDePrueba() });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(RecuperarComponent);
    await fixture.whenStable();
    return fixture;
  }

  const el = (fixture: ComponentFixture<unknown>) => fixture.nativeElement as HTMLElement;
  const enviar = (fixture: ComponentFixture<unknown>, legajo: string) => {
    const campo = el(fixture).querySelector<HTMLInputElement>('#legajo')!;
    campo.value = legajo;
    campo.dispatchEvent(new Event('input'));
    el(fixture).querySelector<HTMLButtonElement>('button[type=submit]')!.click();
  };

  it('sin legajo no llama a la API', async () => {
    const fixture = await montar();

    enviar(fixture, '  ');
    await fixture.whenStable();

    http.expectNone(`${API_URL}/recuperar-contrasena/`);
    expect(el(fixture).querySelector('[role=alert]')?.textContent).toContain('Ingresá tu legajo');
  });

  it('pide el mail y muestra el aviso genérico', async () => {
    const fixture = await montar();

    enviar(fixture, '48293');
    const pedido = http.expectOne(`${API_URL}/recuperar-contrasena/`);
    expect(pedido.request.body).toEqual({ legajo: '48293' });
    pedido.flush({ mensaje: 'ok' });
    await fixture.whenStable();

    expect(el(fixture).querySelector('[role=status]')?.textContent).toContain('te enviamos un mail');
    expect(el(fixture).querySelector('form')).toBeNull();
  });
});
