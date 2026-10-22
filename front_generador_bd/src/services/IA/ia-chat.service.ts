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
  /** Solo en modo `change`: cuántos elementos elimina el cambio (pide confirmación si > 0). */
  destructive?: number;
  /** El usuario no confirmó un cambio destructivo: no se aplicó nada. */
  cancelled?: boolean;
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

  /** Qué IA responde (nube o modelo local), para mostrarlo en el chat. */
  provider(): Observable<{ provider: string; label: string }> {
    return this.http.get<{ provider: string; label: string }>(
      `${environment.endpoint_python}api/ia/provider/`
    );
  }

  send(roomId: string, mode: IaChatMode, message: string, uml: unknown): Observable<IaChatResponse> {
    return this.http.post<IaChatResponse>(
      `${this.baseUrl(roomId)}ia/chat/`,
      { mode, message, uml },
      { headers: this.headers() }
    ).pipe(timeout(IA_REQUEST_TIMEOUT_MS));
  }

  /** Reserva una idea de la IA para quien la va a aplicar (409 si otra persona ya la tomó). */
  claimSuggestion(roomId: string, eventId: number, index: number): Observable<unknown> {
    return this.http.post(this.suggestionUrl(roomId, eventId, index), {}, { headers: this.headers() });
  }

  /** Libera una idea reservada cuando el cambio no llegó a aplicarse. */
  releaseSuggestion(roomId: string, eventId: number, index: number): Observable<unknown> {
    return this.http.delete(this.suggestionUrl(roomId, eventId, index), { headers: this.headers() });
  }

  private suggestionUrl(roomId: string, eventId: number, index: number): string {
    return `${this.baseUrl(roomId)}activity/${eventId}/apply/${index}/`;
  }

  private baseUrl(roomId: string): string {
    return `${environment.endpoint_python}api/rooms/${encodeURIComponent(roomId)}/`;
  }

  private headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Participant-Token': this.identity.getIdentity().token });
  }
}
