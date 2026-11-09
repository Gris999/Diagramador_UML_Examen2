import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

/**
 * Manda la sesión (`Authorization: Bearer`) solo en los pedidos a la API de este sistema, nunca a otros sitios. Si el servidor contesta 401 en
 * cualquier ruta que no sea la de entrar, la sesión ya no vale: se borra y se vuelve a la pantalla de entrada.
 */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const api = `${environment.endpoint_python}api/`;
  const ours = request.url.startsWith(api);
  const token = auth.token();

  const outgoing = ours && token ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : request;
  return next(outgoing).pipe(
    catchError(error => {
      if (ours && error instanceof HttpErrorResponse && error.status === 401 && !request.url.startsWith(`${api}auth/`)) {
        auth.expire();
      }
      return throwError(() => error);
    })
  );
};
