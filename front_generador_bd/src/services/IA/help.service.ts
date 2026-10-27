import { isPlatformBrowser } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable, PLATFORM_ID } from '@angular/core';
import { map, Observable, timeout } from 'rxjs';
import { v4 as uuid, validate as isUuid } from 'uuid';
import { environment } from '../../environments/environment';

export const HELP_TOKEN_STORAGE_KEY = 'uml-help-token';

/** Igual que en el servidor: solo se usa lo más reciente de la conversación. */
export const MAX_HELP_HISTORY = 6;
const HELP_REQUEST_TIMEOUT_MS = 60_000;

export type HelpMessage = { role: 'user' | 'ia'; content: string };

/**
 * Asistente que enseña a usar la herramienta. La conversación es personal: la guarda el navegador y se manda completa (los últimos
 * mensajes) en cada pregunta. No necesita sala ni nombre: un identificador anónimo propio sirve para el tope de uso del servidor.
 */
@Injectable({ providedIn: 'root' })
export class HelpService {
  private readonly http = inject(HttpClient);
  private readonly platformId = inject(PLATFORM_ID);
  private memoryToken?: string;

  ask(message: string, history: HelpMessage[]): Observable<string> {
    return this.http
      .post<{ reply?: string }>(
        `${environment.endpoint_python}api/ia/help/`,
        { message, history: history.slice(-MAX_HELP_HISTORY) },
        { headers: new HttpHeaders({ 'X-Help-Token': this.token() }) }
      )
      .pipe(
        timeout(HELP_REQUEST_TIMEOUT_MS),
        map(response => (typeof response?.reply === 'string' ? response.reply : ''))
      );
  }

  private token(): string {
    if (this.memoryToken) return this.memoryToken;

    const stored = this.read();
    this.memoryToken = stored && isUuid(stored) ? stored : uuid();
    this.write(this.memoryToken);
    return this.memoryToken;
  }

  private read(): string | null {
    if (!isPlatformBrowser(this.platformId)) return null;
    try {
      return window.localStorage.getItem(HELP_TOKEN_STORAGE_KEY);
    } catch {
      return null;
    }
  }

  private write(token: string): void {
    if (!isPlatformBrowser(this.platformId)) return;
    try {
      window.localStorage.setItem(HELP_TOKEN_STORAGE_KEY, token);
    } catch {
      // El identificador queda en memoria mientras dure la página.
    }
  }
}
