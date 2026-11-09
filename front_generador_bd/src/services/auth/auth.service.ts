import { HttpClient } from '@angular/common/http';
import { Injectable, Injector, PLATFORM_ID, computed, inject, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { Observable, catchError, map, of, tap, timeout } from 'rxjs';
import { environment } from '../../environments/environment';

/** Dónde se recuerda la sesión (solo una comodidad: sin ella, se vuelve a pedir el código). */
export const SESSION_STORAGE_KEY = 'diagramador-sesion';

/** Lo que el servidor pide: si hay que iniciar sesión y si puede mandar correos. */
export type AuthConfig = { authRequired: boolean; mailConfigured: boolean };

export type Session = { token: string; email: string; name: string };

/** Lo que se asume si el servidor no contesta: no se bloquea a nadie por una falla de red (la API fallará sola si hace falta). */
const OPEN_CONFIG: AuthConfig = { authRequired: false, mailConfigured: false };
const CONFIG_TIMEOUT_MS = 5000;

/** La sesión guardada en el navegador, o `null` (sin navegador, sin permiso de almacenamiento o con datos raros). */
export function readStoredSession(): Session | null {
  try {
    if (typeof localStorage === 'undefined') return null;
    const parsed = JSON.parse(localStorage.getItem(SESSION_STORAGE_KEY) ?? 'null');
    if (
      parsed &&
      typeof parsed.token === 'string' && parsed.token &&
      typeof parsed.email === 'string' && parsed.email &&
      typeof parsed.name === 'string'
    ) {
      return { token: parsed.token, email: parsed.email, name: parsed.name };
    }
  } catch {
    // datos ilegibles: se trata como si no hubiera sesión
  }
  return null;
}

/**
 * Entrar con el correo: se pide un código, el servidor lo manda por correo y, al escribirlo, devuelve una sesión firmada que se manda en cada
 * pedido a la API (`auth.interceptor`) y al abrir el WebSocket. Con el servidor sin `AUTH_REQUIRED` nada de esto estorba.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly injector = inject(Injector);
  private readonly browser = isPlatformBrowser(inject(PLATFORM_ID));

  readonly config = signal<AuthConfig | null>(null);
  readonly session = signal<Session | null>(this.browser ? readStoredSession() : null);
  readonly loggedIn = computed(() => this.session() !== null);

  isBrowser(): boolean {
    return this.browser;
  }

  token(): string | null {
    return this.session()?.token ?? null;
  }

  /** Lo que pide el servidor; se pregunta una vez y se recuerda. Si no contesta a tiempo se deja pasar. */
  ensureConfig(): Observable<AuthConfig> {
    const known = this.config();
    if (known) return of(known);
    return this.http.get<AuthConfig>(this.url('config/')).pipe(
      timeout(CONFIG_TIMEOUT_MS),
      map(value => ({ authRequired: value?.authRequired === true, mailConfigured: value?.mailConfigured === true })),
      catchError(() => of(OPEN_CONFIG)),
      tap(value => this.config.set(value))
    );
  }

  /** Pide que se mande un código al correo. */
  requestCode(email: string): Observable<void> {
    return this.http.post(this.url('code/'), { email }).pipe(map(() => undefined));
  }

  /** Cambia el código por una sesión y la guarda. */
  verify(email: string, code: string): Observable<Session> {
    return this.http.post<Session>(this.url('verify/'), { email, code }).pipe(
      tap(session => this.save({ token: session.token, email: session.email, name: session.name }))
    );
  }

  logout(): void {
    this.session.set(null);
    this.forget();
  }

  /** La sesión ya no vale (venció o el servidor la rechazó): se borra y, si hay que iniciar sesión, se vuelve a la pantalla de entrada. */
  expire(): void {
    if (!this.session()) return;
    this.logout();
    if (this.config()?.authRequired) {
      const router = this.injector.get(Router);
      void router.navigate(['/entrar'], { queryParams: { volver: router.url } });
    }
  }

  private save(session: Session): void {
    this.session.set(session);
    if (!this.browser) return;
    try {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
    } catch {
      // sin almacenamiento: la sesión vale para esta visita
    }
  }

  private forget(): void {
    if (!this.browser) return;
    try {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    } catch {
      // nada que borrar
    }
  }

  private url(path: string): string {
    return `${environment.endpoint_python}api/auth/${path}`;
  }
}
