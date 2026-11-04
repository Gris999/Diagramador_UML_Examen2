import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
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
  /** Quién lo dijo: el nombre de la persona o «IA». La conversación es la de toda la sala. */
  author_name?: string;
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

/** Texto para la persona cuando un pedido a la IA falla (lo usan el chat y el cuadro «Generar modelo»). */
export function iaErrorMessage(failure: unknown): string {
  if (failure instanceof HttpErrorResponse) {
    if (failure.status === 409) {
      return typeof failure.error?.error === 'string'
        ? failure.error.error
        : 'La IA está atendiendo a otra persona. Espera a que termine.';
    }
    if (failure.status === 429) return 'Demasiadas preguntas seguidas. Espera un momento.';
    if (failure.status === 403) {
      return 'Todavía no te identificaste en la sala. Recarga la página e inténtalo de nuevo.';
    }
    if (failure.status === 400 && typeof failure.error?.error === 'string') {
      return failure.error.error;
    }
  }
  return 'La IA no pudo responder ahora. Intenta de nuevo.';
}

/**
 * Conversación de la sala con la IA: la ven y la alimentan todas las personas de la sala. El token anónimo del
 * navegador identifica a quien pregunta; el servidor devuelve los mensajes de la sala con el autor de cada uno.
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

  /** Marca la idea como aplicada para todos una vez que el cambio llegó al diagrama. */
  confirmSuggestion(roomId: string, eventId: number, index: number): Observable<unknown> {
    return this.http.put(this.suggestionUrl(roomId, eventId, index), {}, { headers: this.headers() });
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
