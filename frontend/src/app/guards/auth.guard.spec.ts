import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, RouterStateSnapshot, UrlTree } from '@angular/router';

import { ADMINISTRADORA, ALUMNA, TUTOR, iniciarSesionComo, proveedoresDePrueba } from '../testing/pruebas';
import { authGuard, rolGuard } from './auth.guard';
import { Usuario } from '../models/api.models';

describe('guardas de ruta', () => {
  const ruta = {} as ActivatedRouteSnapshot;
  const estado = { url: '/materiales/3' } as RouterStateSnapshot;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: proveedoresDePrueba() });
  });

  const evaluar = (guarda: typeof authGuard, usuario: Usuario | null) => {
    if (usuario) {
      iniciarSesionComo(usuario);
    }
    return TestBed.runInInjectionContext(() => guarda(ruta, estado));
  };

  describe('authGuard', () => {
    it('deja pasar a quien inició sesión', () => {
      expect(evaluar(authGuard, ALUMNA)).toBe(true);
    });

    it('manda al login a quien no, recordando a qué página quería entrar', () => {
      const resultado = evaluar(authGuard, null);

      expect(resultado).toBeInstanceOf(UrlTree);
      expect((resultado as UrlTree).toString()).toBe('/login?returnUrl=%2Fmateriales%2F3');
    });
  });

  describe('rolGuard', () => {
    const soloAdmin = rolGuard('administrador');

    it('deja pasar a un usuario con el rol pedido', () => {
      expect(evaluar(soloAdmin, ADMINISTRADORA)).toBe(true);
    });

    it('acepta más de un rol', () => {
      expect(evaluar(rolGuard('tutor', 'administrador'), TUTOR)).toBe(true);
    });

    it('manda a /materias a quien tiene sesión pero otro rol', () => {
      const resultado = evaluar(soloAdmin, ALUMNA);

      expect((resultado as UrlTree).toString()).toBe('/materias');
    });

    it('manda al login a quien no inició sesión', () => {
      const resultado = evaluar(soloAdmin, null);

      expect((resultado as UrlTree).toString()).toBe('/login?returnUrl=%2Fmateriales%2F3');
    });
  });
});
