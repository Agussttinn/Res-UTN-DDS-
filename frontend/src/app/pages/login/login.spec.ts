import { HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';

import { ALUMNA, API_URL, iniciarSesionComo, proveedoresDePrueba, textoDe, tokenDe } from '../../testing/pruebas';
import { LoginComponent } from './login';

describe('LoginComponent', () => {
  let http: HttpTestingController;
  let navegar: ReturnType<typeof vi.spyOn>;

  async function montar(parametros: Record<string, string> = {}, conSesion = false): Promise<ComponentFixture<LoginComponent>> {
    localStorage.clear();
    if (conSesion) {
      iniciarSesionComo(ALUMNA);
    }
    TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: proveedoresDePrueba({ provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(parametros) } } }),
    });
    http = TestBed.inject(HttpTestingController);
    navegar = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const fixture = TestBed.createComponent(LoginComponent);
    await fixture.whenStable();
    return fixture;
  }

  const escribir = (fixture: ComponentFixture<unknown>, selector: string, valor: string) => {
    const campo = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>(selector)!;
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
  };
  const enviar = (fixture: ComponentFixture<unknown>, legajo: string, contrasena: string) => {
    escribir(fixture, '#legajo', legajo);
    escribir(fixture, '#contrasena', contrasena);
    (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('button[type=submit]')!.click();
  };
  const alerta = (fixture: ComponentFixture<unknown>) =>
    (fixture.nativeElement as HTMLElement).querySelector('[role=alert]')?.textContent?.trim() ?? null;

  afterEach(() => http.verify());

  it('con los campos vacíos avisa y no llama a la API', async () => {
    const fixture = await montar();

    enviar(fixture, '  ', '');
    await fixture.whenStable();

    expect(alerta(fixture)).toBe('Ingresá tu legajo y tu contraseña.');
    http.expectNone(`${API_URL}/login/`);
  });

  it('con credenciales correctas inicia sesión y va a /materias', async () => {
    const fixture = await montar();

    enviar(fixture, ' 200 ', 'claveAlumno123'); // el legajo se limpia de espacios
    const peticion = http.expectOne(`${API_URL}/login/`);
    expect(peticion.request.body).toEqual({ legajo: '200', contraseña: 'claveAlumno123' });
    peticion.flush({ access: tokenDe('200'), usuario: ALUMNA });
    await fixture.whenStable();

    expect(navegar).toHaveBeenCalledWith('/materias');
  });

  it('muestra el motivo real cuando las credenciales son incorrectas y no navega', async () => {
    const fixture = await montar();

    enviar(fixture, '200', 'mal');
    http.expectOne(`${API_URL}/login/`).flush({ error: 'Legajo o contraseña incorrectos' }, { status: 401, statusText: 'Unauthorized' });
    await fixture.whenStable();

    expect(alerta(fixture)).toBe('Legajo o contraseña incorrectos');
    expect(navegar).not.toHaveBeenCalled();
  });

  it('el botón se deshabilita mientras espera la respuesta', async () => {
    const fixture = await montar();
    const boton = (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('button[type=submit]')!;

    enviar(fixture, '200', 'clave');
    await Promise.resolve();
    fixture.detectChanges();
    expect(boton.disabled).toBe(true);
    expect(boton.textContent).toContain('Iniciando sesión');

    http.expectOne(`${API_URL}/login/`).flush({}, { status: 500, statusText: 'Error' });
  });

  it('vuelve a la página que la persona quería abrir antes de que la mandaran al login', async () => {
    const fixture = await montar({ returnUrl: '/materiales/3' });

    enviar(fixture, '200', 'clave');
    http.expectOne(`${API_URL}/login/`).flush({ access: tokenDe('200'), usuario: ALUMNA });

    expect(navegar).toHaveBeenCalledWith('/materiales/3');
  });

  it('ignora un returnUrl que apunta afuera de la app', async () => {
    const fixture = await montar({ returnUrl: '//sitio-malicioso.com' });

    enviar(fixture, '200', 'clave');
    http.expectOne(`${API_URL}/login/`).flush({ access: tokenDe('200'), usuario: ALUMNA });

    expect(navegar).toHaveBeenCalledWith('/materias');
  });

  it('avisa cuando la sesión venció', async () => {
    const fixture = await montar({ vencida: '1' });

    expect(textoDe(fixture)).toContain('Tu sesión venció');
  });

  it('sin el aviso de vencida no lo muestra', async () => {
    expect(textoDe(await montar())).not.toContain('Tu sesión venció');
  });

  it('si ya tiene sesión, no muestra el login y sigue a la app', async () => {
    await montar({}, true);

    expect(navegar).toHaveBeenCalledWith('/materias');
  });
});
