import { HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { ALUMNA, API_URL, proveedoresDePrueba, tokenDe } from '../../testing/pruebas';
import { RegistroComponent } from './registro';

describe('RegistroComponent', () => {
  let http: HttpTestingController;
  let fixture: ComponentFixture<RegistroComponent>;
  let navegar: ReturnType<typeof vi.spyOn>;

  beforeEach(async () => {
    localStorage.clear();
    TestBed.configureTestingModule({ imports: [RegistroComponent], providers: proveedoresDePrueba() });
    http = TestBed.inject(HttpTestingController);
    navegar = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    fixture = TestBed.createComponent(RegistroComponent);
    await fixture.whenStable();
  });

  afterEach(() => http.verify());

  const escribir = (selector: string, valor: string) => {
    const campo = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>(selector)!;
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
  };
  const enviar = (legajo: string, contrasena: string, repetir: string) => {
    escribir('#legajo', legajo);
    escribir('#contrasena', contrasena);
    escribir('#repetir', repetir);
    (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('button[type=submit]')!.click();
  };
  const alerta = () => (fixture.nativeElement as HTMLElement).querySelector('[role=alert]')?.textContent?.trim() ?? null;

  it('pide completar legajo y contraseña', async () => {
    enviar('', '', '');
    await fixture.whenStable();

    expect(alerta()).toBe('Completá tu legajo y elegí una contraseña.');
    http.expectNone(`${API_URL}/registro/`);
  });

  it('rechaza una contraseña de menos de 8 caracteres sin ir al servidor', async () => {
    enviar('48293', 'corta1', 'corta1');
    await fixture.whenStable();

    expect(alerta()).toBe('La contraseña tiene que tener al menos 8 caracteres.');
    http.expectNone(`${API_URL}/registro/`);
  });

  it('avisa si las dos contraseñas no coinciden, sin ir al servidor', async () => {
    enviar('48293', 'miclave123', 'otraclave999');
    await fixture.whenStable();

    expect(alerta()).toBe('Las contraseñas no coinciden.');
    http.expectNone(`${API_URL}/registro/`);
  });

  it('registra la cuenta y después inicia sesión sola (sin volver a pedir los datos) y entra a la app', async () => {
    enviar(' 48293 ', 'miclave123', 'miclave123');

    const registro = http.expectOne(`${API_URL}/registro/`);
    expect(registro.request.body).toEqual({ legajo: '48293', contraseña: 'miclave123' });
    registro.flush({ legajo: '48293', nombre_y_apellido: 'Sofía Martínez' }, { status: 201, statusText: 'Created' });

    const login = http.expectOne(`${API_URL}/login/`);
    expect(login.request.body).toEqual({ legajo: '48293', contraseña: 'miclave123' });
    login.flush({ access: tokenDe('48293'), usuario: { ...ALUMNA, legajo: '48293', nombre_y_apellido: 'Sofía Martínez' } });

    expect(navegar).toHaveBeenCalledWith('/materias');
  });

  it('muestra el motivo si SySACAD no reconoce el legajo, y no intenta iniciar sesión', async () => {
    enviar('99999', 'miclave123', 'miclave123');

    http.expectOne(`${API_URL}/registro/`).flush({ error: 'No existe ese legajo en SysAcad' }, { status: 400, statusText: 'Bad Request' });
    await fixture.whenStable();

    expect(alerta()).toBe('No existe ese legajo en SysAcad');
    http.expectNone(`${API_URL}/login/`);
    expect(navegar).not.toHaveBeenCalled();
  });

  it('muestra los mensajes de la contraseña que rechaza el backend', async () => {
    enviar('48293', '12345678', '12345678');

    http.expectOne(`${API_URL}/registro/`).flush(
      { error: 'La contraseña tiene un valor demasiado común. La contraseña está formada completamente por dígitos.' },
      { status: 400, statusText: 'Bad Request' },
    );
    await fixture.whenStable();

    expect(alerta()).toContain('demasiado común');
  });

  it('si la cuenta se creó pero falla el inicio de sesión automático, lo explica', async () => {
    enviar('48293', 'miclave123', 'miclave123');
    http.expectOne(`${API_URL}/registro/`).flush({}, { status: 201, statusText: 'Created' });
    http.expectOne(`${API_URL}/login/`).flush({}, { status: 500, statusText: 'Error' });
    await fixture.whenStable();

    expect(alerta()).toContain('Tu cuenta se creó');
    expect(navegar).not.toHaveBeenCalled();
  });
});
