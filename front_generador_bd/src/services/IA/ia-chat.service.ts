import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { IdentityService } from '../colaboration/identity.service';

export type IaChatMessage = {
  id: number;
  role: 'user' | 'ia';
  content: string;
  created_at: string;
};

/**
 * Chat privado de cada participante con la IA de la sala. El token anónimo del
 * navegador identifica a quien pregunta; el servidor solo devuelve sus mensajes.
 */
@Injectable({ providedIn: 'root' })
export class IaChatService {
  private readonly http = inject(HttpClient);
  private readonly identity = inject(IdentityService);

  history(roomId: string): Observable<IaChatMessage[]> {
    return this.http
      .get<{ messages: IaChatMessage[] }>(`${this.baseUrl(roomId)}chat/?limit=50`, {
        headers: this.headers()
      })
      .pipe(map(response => (Array.isArray(response?.messages) ? response.messages : [])));
  }

  ask(roomId: string, message: string, uml: unknown): Observable<string> {
    return this.http
      .post<{ reply: string }>(
        `${this.baseUrl(roomId)}ia/chat/`,
        { mode: 'ask', message, uml },
        { headers: this.headers() }
      )
      .pipe(map(response => response.reply));
  }

  private baseUrl(roomId: string): string {
    return `${environment.endpoint_python}api/rooms/${encodeURIComponent(roomId)}/`;
  }

  private headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Participant-Token': this.identity.getIdentity().token });
  }
}
