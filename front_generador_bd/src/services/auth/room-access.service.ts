import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export type RoomMember = { email: string; role: 'owner' | 'invited' | string };

export type RoomAccess = {
  /** `false` cuando el servidor no controla el acceso (modo sin cuentas). */
  required: boolean;
  email: string | null;
  role: string | null;
  members: RoomMember[];
};

/** Quién tiene acceso a una sala: con el servidor en modo «entrar con el correo» solo entran el propietario y quienes invitó alguien de la sala. */
@Injectable({ providedIn: 'root' })
export class RoomAccessService {
  private readonly http = inject(HttpClient);

  /** Entra a la sala: la primera persona que abre una sala sin dueño queda como propietario; a quien no está invitado el servidor le contesta 403. */
  enter(roomId: string): Observable<RoomAccess> {
    return this.http.post<RoomAccess>(this.url(roomId), {});
  }

  /** Mira quién tiene acceso (sin reclamar la sala). */
  members(roomId: string): Observable<RoomAccess> {
    return this.http.get<RoomAccess>(this.url(roomId));
  }

  private url(roomId: string): string {
    return `${environment.endpoint_python}api/rooms/${encodeURIComponent(roomId)}/access/`;
  }
}
