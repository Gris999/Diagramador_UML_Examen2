import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { AuthService } from './auth.service';

/**
 * Deja pasar solo a quien inició sesión cuando el servidor lo exige; si no, lo manda a «/entrar» y, al terminar, lo trae de vuelta a donde iba.
 * En el servidor de la página (SSR) no hay sesión que mirar: deja pasar y lo decide el navegador.
 */
export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.isBrowser()) return true;

  return auth.ensureConfig().pipe(
    map(config =>
      !config.authRequired || auth.loggedIn()
        ? true
        : router.createUrlTree(['/entrar'], { queryParams: { volver: state.url } })
    )
  );
};
