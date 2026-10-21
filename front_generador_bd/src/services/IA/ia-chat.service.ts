import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable, timeout } from 'rxjs';
import { environment } from '../../environments/environment';
import { IdentityService } from '../colaboration/identity.service';

export type IaChatMode = 'ask' | 'change' | 'review';

// Si el servidor no contesta en este tiempo se muestra un error en vez de
// dejar a la sala viendo "pensando…" sin fin.
const IA_REQUEST_TIMEOUT_MS = 110_000;

export type IaChatMessage = {
  id: number;
  role: 'user' | 'ia';
  mode?: IaChatMode;
  content: string;
  created_at: string;
};

export type IaSuggestion = { id: number; text: string; prompt: string };

export type IaChatResponse = {
  reply: string;
  /** Solo en modo `change`: cambios que el navegador de quien pidió debe aplicar. */
  changes?: unknown;
  /** Solo en modo `review`: ideas que cualquiera de la sala puede aplicar. */
  suggestions?: IaSuggestion[];
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

  send(roomId: string, mode: IaChatMode, message: string, uml: unknown): Observable<IaChatResponse> {
    return this.http.post<IaChatResponse>(
      `${this.baseUrl(roomId)}ia/chat/`,
      { mode, message, uml },
      { headers: this.headers() }
    ).pipe(timeout(IA_REQUEST_TIMEOUT_MS));
  }

  private baseUrl(roomId: string): string {
    return `${environment.endpoint_python}api/rooms/${encodeURIComponent(roomId)}/`;
  }

  private headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Participant-Token': this.identity.getIdentity().token });
  }
}
