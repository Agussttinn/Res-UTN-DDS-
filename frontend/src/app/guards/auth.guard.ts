import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { Rol } from '../models/api.models';
import { AuthService } from '../services/auth.service';

/** Solo entra quien inició sesión; si no, va al login y después vuelve a la página que quería. */
export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.estaLogueado()
    ? true
    : router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};

/** Solo entra quien inició sesión Y tiene alguno de esos roles (la API igual lo vuelve a verificar). */
export const rolGuard = (...roles: Rol[]): CanActivateFn => {
  return (_route, state) => {
    const auth = inject(AuthService);
    const router = inject(Router);
    if (!auth.estaLogueado()) {
      return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
    }
    const rol = auth.rol();
    return rol !== null && roles.includes(rol) ? true : router.createUrlTree(['/materias']);
  };
};
