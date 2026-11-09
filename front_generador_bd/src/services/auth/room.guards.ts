import { HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, UrlTree } from '@angular/router';
import { catchError, map, of, switchMap } from 'rxjs';
import { isPhone } from '../device';
import { AuthService } from './auth.service';
import { RoomAccessService } from './room-access.service';

/**
 * Entra a la sala antes de abrirla y decide a dónde va la persona. Quien no tiene acceso va a «/sin-acceso». Con `editor`, quien solo puede leer va a la
 * vista de solo lectura de la misma sala en vez del editor. Sin el modo «entrar con el correo», o en el servidor de la página (SSR), deja pasar.
 * Lo que de verdad protege la sala es el servidor (API y WebSocket); esto solo evita abrir una pantalla que no va a funcionar.
 *
 * Es una sola guardia (y no una para el acceso y otra para el rol) porque Angular corre a la vez todas las guardias de una ruta: la del rol no
 * esperaría la respuesta del servidor.
 */
function enterRoom(route: ActivatedRouteSnapshot, editor: boolean) {
  const auth = inject(AuthService);
  const access = inject(RoomAccessService);
  const router = inject(Router);
  const roomId = route.paramMap.get('roomId');
  if (!auth.isBrowser() || !roomId) return of(true);

  return auth.ensureConfig().pipe(
    switchMap(config =>
      !config.authRequired
        ? of(true)
        : access.enter(roomId).pipe(
            map((info): boolean | UrlTree => (editor && info.can_edit === false ? router.createUrlTree(['/sala', roomId, 'seguir']) : true)),
            catchError((failure: unknown) => {
              const status = failure instanceof HttpErrorResponse ? failure.status : 0;
              if (status === 403) return of(router.createUrlTree(['/sin-acceso'], { queryParams: { sala: roomId } }));
              // 401: el interceptor ya llevó a la persona a entrar de nuevo. Otro fallo: se deja pasar y la pantalla mostrará su error.
              return of(status !== 401);
            })
          )
    )
  );
}

/** Vista de solo lectura de una sala: solo hace falta tener acceso. */
export const roomAccessGuard: CanActivateFn = route => enterRoom(route, false);

/** El editor: tener acceso y poder editar; un lector va a la vista de solo lectura. */
export const editorRoomGuard: CanActivateFn = route => enterRoom(route, true);

/** En un celular el editor no se abre: se va a la vista de solo lectura de la misma sala (la edición es desde un computador o una tableta). */
export const phoneGuard: CanActivateFn = route => {
  const router = inject(Router);
  const roomId = route.paramMap.get('roomId');
  if (typeof navigator === 'undefined' || !roomId || !isPhone()) return true;
  return router.createUrlTree(['/sala', roomId, 'seguir']);
};
