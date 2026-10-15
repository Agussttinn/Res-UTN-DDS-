import { HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { Usuario } from '../../models/api.models';
import { AuthService } from '../../services/auth.service';
import { ADMINISTRADORA, ALUMNA, API_URL, TUTOR, iniciarSesionComo, proveedoresDePrueba, textoDe, unaNotificacion } from '../../testing/pruebas';
import { NavbarComponent } from './navbar.component';

describe('NavbarComponent', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ imports: [NavbarComponent], providers: proveedoresDePrueba() });
  });

  async function montar(usuario: Usuario | null, avisos = [unaNotificacion({ leida: true })]): Promise<ComponentFixture<NavbarComponent>> {
    if (usuario) {
      iniciarSesionComo(usuario);
    }
    const fixture = TestBed.createComponent(NavbarComponent);
    fixture.detectChanges();
    if (usuario) {
      // La campanita pide los avisos del usuario apenas aparece.
      TestBed.inject(HttpTestingController).expectOne(`${API_URL}/notificaciones/`).flush(avisos);
    }
    await fixture.whenStable();
    return fixture;
  }

  it('sin sesión ofrece iniciar sesión y registrarse, y no muestra los links de la app', async () => {
    const texto = textoDe(await montar(null));

    expect(texto).toContain('Iniciar Sesión');
    expect(texto).toContain('Registrarme');
    for (const oculto of ['Materias', 'Apuntes', 'Clases de Apoyo', 'Moderación', 'Salir']) {
      expect(texto).not.toContain(oculto);
    }
  });

  it('una alumna ve los links de la app, su nombre y su rol, pero no "Moderación"', async () => {
    const texto = textoDe(await montar(ALUMNA));

    expect(texto).toContain('Ana Alumna');
    expect(texto).toContain('Alumno'); // el badge de rol, en el pill del usuario
    for (const visible of ['Materias', 'Apuntes', 'Clases de Apoyo', 'Salir']) {
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
    expect(texto).toContain('Ada Administradora');
    expect(texto).toContain('Administrador'); // el badge de rol
  });

  it('"Cerrar Sesión" cierra la sesión, lleva al login y la barra vuelve a mostrar "Iniciar Sesión"', async () => {
    const fixture = await montar(ALUMNA);
    const navegar = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const boton = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('header button')).find((b) => b.textContent?.includes('Salir'));

    boton?.click();
    await fixture.whenStable();

    expect(TestBed.inject(AuthService).estaLogueado()).toBe(false);
    expect(navegar).toHaveBeenCalledWith(['/login']);
    expect(textoDe(fixture)).toContain('Iniciar Sesión');
  });

  describe('notificaciones', () => {
    const campanita = (fixture: ComponentFixture<unknown>) =>
      (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('app-notificaciones button')!;

    it('sin sesión no hay campanita', async () => {
      expect((await montar(null)).nativeElement.querySelector('app-notificaciones')).toBeNull();
    });

    it('muestra cuántos avisos sin leer hay', async () => {
      const fixture = await montar(ALUMNA, [unaNotificacion({ id: 1 }), unaNotificacion({ id: 2 }), unaNotificacion({ id: 3, leida: true })]);

      expect(campanita(fixture).getAttribute('aria-label')).toBe('Notificaciones: 2 sin leer');
      expect(campanita(fixture).textContent).toContain('2');
    });

    it('al abrirla vuelve a consultar y lista los avisos; "Marcar todas como leídas" avisa al backend', async () => {
      const fixture = await montar(ALUMNA, [unaNotificacion()]);
      const http = TestBed.inject(HttpTestingController);

      campanita(fixture).click();
      http.expectOne(`${API_URL}/notificaciones/`).flush([unaNotificacion({ texto: 'Traigan la guía 3' })]);
      await fixture.whenStable();
      expect(textoDe(fixture)).toContain('Traigan la guía 3');

      const marcar = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find((b) => b.textContent?.includes('Marcar todas'))!;
      marcar.click();
      http.expectOne(`${API_URL}/notificaciones/marcar-leidas/`).flush({ marcadas: 1 });
      await fixture.whenStable();

      expect(campanita(fixture).getAttribute('aria-label')).toBe('Notificaciones');
    });

    it('sin avisos invita a suscribirse a una clase', async () => {
      const fixture = await montar(ALUMNA, []);
      campanita(fixture).click();
      TestBed.inject(HttpTestingController).expectOne(`${API_URL}/notificaciones/`).flush([]);
      await fixture.whenStable();

      expect(textoDe(fixture)).toContain('Suscribite a una clase de apoyo');
    });
  });
});
