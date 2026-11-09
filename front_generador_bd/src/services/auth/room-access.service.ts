import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map, tap } from 'rxjs';
import { environment } from '../../environments/environment';

/** Lo que una persona puede hacer en una sala: `owner` (todo), `editor` (editar e invitar) o `viewer` (solo mirar). */
export type RoomRole = 'owner' | 'editor' | 'viewer';
export type LinkAccess = 'restricted' | 'anyone';
export type AssignableRole = 'editor' | 'viewer';

export type RoomMember = { email: string; role: RoomRole | string; source?: string };

export type RoomAccess = {
  /** `false` cuando el servidor no controla el acceso (modo sin cuentas). */
  required: boolean;
  email: string | null;
  role: RoomRole | string | null;
  is_owner?: boolean;
  can_edit?: boolean;
  title?: string;
  /** Acceso general, como en Google Docs: restringido (solo los agregados) o cualquiera con el enlace. */
  link_access?: LinkAccess;
  /** Con qué rol entra quien llega por el enlace cuando está abierto. */
  link_role?: AssignableRole;
  owner?: string | null;
  members: RoomMember[];
};

/** Un diagrama de la lista «Mis diagramas». */
export type MyRoom = {
  room: string;
  title: string;
  role: RoomRole | string;
  owner: string | null;
  link_access: LinkAccess;
  created_at: string;
  last_opened_at: string | null;
};

export type SettingsPatch = { title?: string; link_access?: LinkAccess; link_role?: AssignableRole };

/**
 * Cómo se comparte una sala cuando se entra con el correo: quién tiene acceso y con qué rol, el acceso general (restringido o cualquiera con el
 * enlace), el nombre del diagrama, borrarlo y la lista «Mis diagramas». Con el servidor sin ese modo no hay nada de esto.
 */
@Injectable({ providedIn: 'root' })
export class RoomAccessService {
  private readonly http = inject(HttpClient);
  private readonly last = new Map<string, RoomAccess>();

  /** Entra a la sala: la primera persona que abre una sala sin dueño queda como propietario; sin acceso el servidor contesta 403. */
  enter(roomId: string): Observable<RoomAccess> {
    return this.http.post<RoomAccess>(this.url(roomId, 'access/'), {}).pipe(tap(access => this.last.set(roomId, access)));
  }

  /** Mira cómo está la sala (rol, nombre, acceso general, quién está) sin reclamarla. */
  info(roomId: string): Observable<RoomAccess> {
    return this.http.get<RoomAccess>(this.url(roomId, 'access/')).pipe(tap(access => this.last.set(roomId, access)));
  }

  /** Lo último que se supo de la sala al entrar a ella (para decidir, por ejemplo, si se abre el editor o la vista de solo lectura). */
  lastAccess(roomId: string): RoomAccess | undefined {
    return this.last.get(roomId);
  }

  /** El propietario cambia el nombre y el acceso general. */
  updateSettings(roomId: string, patch: SettingsPatch): Observable<RoomAccess> {
    return this.http.put<RoomAccess>(this.url(roomId, 'settings/'), patch).pipe(tap(access => this.last.set(roomId, access)));
  }

  /** El propietario cambia el rol de alguien de la lista. */
  setMemberRole(roomId: string, email: string, role: AssignableRole): Observable<RoomAccess> {
    return this.http.put<RoomAccess>(this.url(roomId, 'members/'), { email, role }).pipe(tap(access => this.last.set(roomId, access)));
  }

  /** El propietario quita a alguien; cualquiera puede quitarse a sí mismo de su lista. */
  removeMember(roomId: string, email: string): Observable<RoomAccess | { left: boolean }> {
    return this.http.request<RoomAccess | { left: boolean }>('DELETE', this.url(roomId, 'members/'), { body: { email } });
  }

  /** El propietario borra el diagrama para todas las personas. */
  deleteRoom(roomId: string): Observable<void> {
    return this.http.delete(this.url(roomId, '')).pipe(map(() => undefined));
  }

  /** «Mis diagramas»: los que creó, a los que lo invitaron y los que abrió por un enlace público. */
  myRooms(): Observable<MyRoom[]> {
    return this.http
      .get<{ rooms: MyRoom[] }>(`${environment.endpoint_python}api/rooms/`)
      .pipe(map(response => (Array.isArray(response?.rooms) ? response.rooms : [])));
  }

  private url(roomId: string, suffix: string): string {
    return `${environment.endpoint_python}api/rooms/${encodeURIComponent(roomId)}/${suffix}`;
  }
}
