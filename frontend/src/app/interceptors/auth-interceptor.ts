import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { API_URL } from '../api.config';
import { AuthService } from '../services/auth.service';

/** En estas rutas un 401/400 significa "datos incorrectos", no "sesión vencida". */
const RUTAS_PUBLICAS = [`${API_URL}/login/`, `${API_URL}/registro/`];

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // El token es solo para nuestra API: nunca se lo mandamos a otro dominio.
  if (!req.url.startsWith(API_URL)) {
    return next(req);
  }

  const auth = inject(AuthService);
  const token = auth.token();
  const conToken = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

  return next(conToken).pipe(
    catchError((err: unknown) => {
      if (
        err instanceof HttpErrorResponse &&
        err.status === 401 &&
        token &&
        !RUTAS_PUBLICAS.includes(req.url)
      ) {
        auth.cerrarSesionPorVencimiento();
      }
      return throwError(() => err);
    }),
  );
};
