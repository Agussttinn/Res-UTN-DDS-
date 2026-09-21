import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { Usuario } from '../../models/api.models';
import { AuthService } from '../../services/auth.service';
import { ADMINISTRADORA, ALUMNA, TUTOR, iniciarSesionComo, proveedoresDePrueba, textoDe } from '../../testing/pruebas';
import { NavbarComponent } from './navbar.component';

describe('NavbarComponent', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ imports: [NavbarComponent], providers: proveedoresDePrueba() });
  });

  async function montar(usuario: Usuario | null): Promise<ComponentFixture<NavbarComponent>> {
    if (usuario) {
      iniciarSesionComo(usuario);
    }
    const fixture = TestBed.createComponent(NavbarComponent);
    await fixture.whenStable();
    return fixture;
  }

  it('sin sesión ofrece iniciar sesión y registrarse, y no muestra los links de la app', async () => {
    const texto = textoDe(await montar(null));

    expect(texto).toContain('Iniciar Sesión');
    expect(texto).toContain('Registrarme');
    for (const oculto of ['Materias', 'Apuntes', 'Clases de Apoyo', 'Moderación', 'Cerrar Sesión']) {
      expect(texto).not.toContain(oculto);
    }
  });

  it('una alumna ve los links de la app, su nombre y su rol, pero no "Moderación"', async () => {
    const texto = textoDe(await montar(ALUMNA));

    expect(texto).toContain('Ana Alumna');
    expect(texto).toContain('Alumno · Legajo 200');
    for (const visible of ['Materias', 'Apuntes', 'Clases de Apoyo', 'Cerrar Sesión']) {
      expect(texto).toContain(visible);
    }
    expect(texto).not.toContain('Moderación');
    expect(texto).not.toContain('Iniciar Sesión');
  });

  it('un tutor tampoco ve "Moderación"', async () => {
    expect(textoDe(await montar(TUTOR))).not.toContain('Moderación');
  });

  it('un administrador sí ve "Moderación"', async () => {
    const texto = textoDe(await montar(ADMINISTRADORA));

    expect(texto).toContain('Moderación');
    expect(texto).toContain('Administrador · Legajo 100');
  });

  it('"Cerrar Sesión" cierra la sesión, lleva al login y la barra vuelve a mostrar "Iniciar Sesión"', async () => {
    const fixture = await montar(ALUMNA);
    const navegar = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const boton = (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('header button');

    boton?.click();
    await fixture.whenStable();

    expect(TestBed.inject(AuthService).estaLogueado()).toBe(false);
    expect(navegar).toHaveBeenCalledWith(['/login']);
    expect(textoDe(fixture)).toContain('Iniciar Sesión');
  });
});
