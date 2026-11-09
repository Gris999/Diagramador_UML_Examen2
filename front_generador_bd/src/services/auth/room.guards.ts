import { HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of, switchMap } from 'rxjs';
import { isPhone } from '../device';
import { AuthService } from './auth.service';
import { RoomAccessService } from './room-access.service';

/**
 * Antes de abrir una sala comprueba que el correo de la sesión tenga acceso (la sala es suya o lo invitaron). Quien no está invitado va a
 * «/sin-acceso». Sin el modo «entrar con el correo», o en el servidor de la página (SSR), deja pasar. Lo que de verdad protege la sala es el
 * servidor (API y WebSocket); esto solo evita abrir una pantalla que no va a funcionar.
 */
export const roomAccessGuard: CanActivateFn = route => {
  const auth = inject(AuthService);
  const access = inject(RoomAccessService);
  const router = inject(Router);
  const roomId = route.paramMap.get('roomId');
  if (!auth.isBrowser() || !roomId) return true;

  return auth.ensureConfig().pipe(
    switchMap(config =>
      !config.authRequired
        ? of(true)
        : access.enter(roomId).pipe(
            map(() => true),
            catchError((failure: unknown) => {
              const status = failure instanceof HttpErrorResponse ? failure.status : 0;
              if (status === 403) return of(router.createUrlTree(['/sin-acceso'], { queryParams: { sala: roomId } }));
              // 401: el interceptor ya llevó a la persona a entrar de nuevo. Otro fallo: se deja pasar y la pantalla mostrará su error.
              return of(status !== 401);
            })
          )
    )
  );
};

/** Quien solo tiene rol de lector no abre el editor: se va a la vista de solo lectura de la misma sala. Va después de `roomAccessGuard`, que trae el rol. */
export const viewerGuard: CanActivateFn = route => {
  const access = inject(RoomAccessService);
  const router = inject(Router);
  const roomId = route.paramMap.get('roomId');
  if (!roomId) return true;
  return access.lastAccess(roomId)?.can_edit === false ? router.createUrlTree(['/sala', roomId, 'seguir']) : true;
};

/** En un celular el editor no se abre: se va a la vista de solo lectura de la misma sala (la edición es desde un computador o una tableta). */
export const phoneGuard: CanActivateFn = route => {
  const router = inject(Router);
  const roomId = route.paramMap.get('roomId');
  if (typeof navigator === 'undefined' || !roomId || !isPhone()) return true;
  return router.createUrlTree(['/sala', roomId, 'seguir']);
};
