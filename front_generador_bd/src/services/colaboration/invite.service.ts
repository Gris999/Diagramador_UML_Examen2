import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { IdentityService } from './identity.service';

import type { RoomMember } from '../auth/room-access.service';

export type InviteResult = { sent: string[]; failed: string[]; /** Quién tiene acceso ahora (solo con el modo «entrar con el correo»). */ members?: RoomMember[] };

/** Los correos de un texto escrito a mano (separados por comas, punto y coma, espacios o saltos de línea), sin repetir y sin importar mayúsculas. */
export function parseEmails(text: string): { valid: string[]; invalid: string[] } {
  const valid: string[] = [];
  const invalid: string[] = [];
  for (const raw of (text ?? '').split(/[\s,;]+/)) {
    const email = raw.trim().toLowerCase();
    if (!email) continue;
    if (/^[^\s@,;<>]{1,64}@[^\s@,;<>]+\.[a-z]{2,}$/.test(email) && !email.includes('..')) {
      if (!valid.includes(email)) valid.push(email);
    } else if (!invalid.includes(raw.trim())) {
      invalid.push(raw.trim());
    }
  }
  return { valid, invalid };
}

/** Invitar por correo a la sala: el servidor manda el enlace a cada dirección (solo lo puede hacer quien está en la sala). */
@Injectable({ providedIn: 'root' })
export class InviteService {
  private readonly http = inject(HttpClient);
  private readonly identity = inject(IdentityService);

  send(roomId: string, emails: string[], message: string): Observable<InviteResult> {
    return this.http.post<InviteResult>(
      `${environment.endpoint_python}api/rooms/${encodeURIComponent(roomId)}/invite/`,
      { emails, message },
      { headers: new HttpHeaders({ 'X-Participant-Token': this.identity.getIdentity().token }) }
    );
  }
}
