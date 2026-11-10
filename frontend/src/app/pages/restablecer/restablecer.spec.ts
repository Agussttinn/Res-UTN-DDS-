import { HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';

import { API_URL, proveedoresDePrueba } from '../../testing/pruebas';
import { RestablecerComponent } from './restablecer';

describe('RestablecerComponent', () => {
  let http: HttpTestingController;

  async function montar(parametros: Record<string, string>): Promise<ComponentFixture<RestablecerComponent>> {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [RestablecerComponent],
      providers: proveedoresDePrueba({ provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(parametros) } } }),
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(RestablecerComponent);
    await fixture.whenStable();
    return fixture;
  }

  const el = (fixture: ComponentFixture<unknown>) => fixture.nativeElement as HTMLElement;
  const escribir = (fixture: ComponentFixture<unknown>, selector: string, valor: string) => {
    const campo = el(fixture).querySelector<HTMLInputElement>(selector)!;
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
  };
  const enviar = (fixture: ComponentFixture<unknown>, clave: string, repetir: string) => {
    escribir(fixture, '#contrasena', clave);
    escribir(fixture, '#repetir', repetir);
    el(fixture).querySelector<HTMLButtonElement>('button[type=submit]')!.click();
  };

  it('sin token en el link avisa que no es válido', async () => {
    const fixture = await montar({});

    expect(el(fixture).querySelector('form')).toBeNull();
    expect(el(fixture).querySelector('[role=alert]')?.textContent).toContain('no es válido');
  });

  it('valida el largo y que las contraseñas coincidan', async () => {
    const fixture = await montar({ token: 'abc' });

    enviar(fixture, 'corta', 'corta');
    await fixture.whenStable();
    expect(el(fixture).querySelector('[role=alert]')?.textContent).toContain('al menos 8');

    enviar(fixture, 'clavelarga99', 'otraclave99');
    await fixture.whenStable();
    expect(el(fixture).querySelector('[role=alert]')?.textContent).toContain('no coinciden');
    http.expectNone(`${API_URL}/restablecer-contrasena/`);
  });

  it('manda el token y la contraseña nueva y muestra la confirmación', async () => {
    const fixture = await montar({ token: '48293~firma' });

    enviar(fixture, 'clavelarga99', 'clavelarga99');
    const pedido = http.expectOne(`${API_URL}/restablecer-contrasena/`);
    expect(pedido.request.body).toEqual({ token: '48293~firma', contraseña: 'clavelarga99' });
    pedido.flush({ mensaje: 'ok' });
    await fixture.whenStable();

    expect(el(fixture).querySelector('[role=status]')?.textContent).toContain('Contraseña actualizada');
  });

  it('si el link venció muestra el error de la API', async () => {
    const fixture = await montar({ token: 'viejo' });

    enviar(fixture, 'clavelarga99', 'clavelarga99');
    http.expectOne(`${API_URL}/restablecer-contrasena/`)
      .flush({ error: 'El link no es válido o venció. Pedí uno nuevo.' }, { status: 400, statusText: 'Bad Request' });
    await fixture.whenStable();

    expect(el(fixture).querySelector('[role=alert]')?.textContent).toContain('venció');
  });
});
