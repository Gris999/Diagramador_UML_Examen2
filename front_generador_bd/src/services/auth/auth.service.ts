import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, Injector, PLATFORM_ID, computed, inject, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { Observable, catchError, map, of, tap, throwError, timeout } from 'rxjs';
import { environment } from '../../environments/environment';

/** Dónde se recuerda la sesión (solo una comodidad: sin ella, se vuelve a pedir el código). */
export const SESSION_STORAGE_KEY = 'diagramador-sesion';

/** Las cuentas que ya entraron en este navegador (cada una con su sesión), para volver a ellas con un clic, sin pedir otro código. */
export const ACCOUNTS_STORAGE_KEY = 'diagramador-cuentas';
/** Cuántas cuentas se recuerdan a la vez; al pasar de ahí se olvida la que hace más tiempo no se usa. */
export const MAX_ACCOUNTS = 5;

/** Lo que el servidor pide: si hay que iniciar sesión y si puede mandar correos. */
export type AuthConfig = { authRequired: boolean; mailConfigured: boolean };

export type Session = { token: string; email: string; name: string };

/** Lo que se asume si el servidor no contesta: no se bloquea a nadie por una falla de red (la API fallará sola si hace falta). */
const OPEN_CONFIG: AuthConfig = { authRequired: false, mailConfigured: false };
const CONFIG_TIMEOUT_MS = 5000;

function asSession(parsed: unknown): Session | null {
  const { token, email, name } = (parsed && typeof parsed === 'object' ? parsed : {}) as Record<string, unknown>;
  if (typeof token === 'string' && token && typeof email === 'string' && email && typeof name === 'string') {
    return { token, email, name };
  }
  return null;
}

/** La sesión guardada en el navegador, o `null` (sin navegador, sin permiso de almacenamiento o con datos raros). */
export function readStoredSession(): Session | null {
  try {
    if (typeof localStorage === 'undefined') return null;
    return asSession(JSON.parse(localStorage.getItem(SESSION_STORAGE_KEY) ?? 'null'));
  } catch {
    // datos ilegibles: se trata como si no hubiera sesión
  }
  return null;
}

/** Las cuentas recordadas en este navegador (la más reciente primero), sin repetir correos y sin datos que no sean una sesión. */
export function readStoredAccounts(): Session[] {
  try {
    if (typeof localStorage === 'undefined') return [];
    const parsed = JSON.parse(localStorage.getItem(ACCOUNTS_STORAGE_KEY) ?? 'null');
    if (!Array.isArray(parsed)) return [];
    const seen = new Set<string>();
    const accounts: Session[] = [];
    for (const item of parsed) {
      const account = asSession(item);
      if (account && !seen.has(account.email)) {
        seen.add(account.email);
        accounts.push(account);
      }
    }
    return accounts.slice(0, MAX_ACCOUNTS);
  } catch {
    return [];
  }
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
  /** Las cuentas que ya entraron en este navegador: se puede volver a cualquiera con un clic (sin otro código) mientras su sesión valga. */
  readonly accounts = signal<Session[]>(this.browser ? this.initialAccounts() : []);

  /** Una sola vez por visita se le pregunta al servidor quién es esta sesión, y de paso se renueva (ver `renew`). */
  private renewed = false;

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

  /** Cierra la sesión de la cuenta actual y la olvida; las otras cuentas recordadas siguen ahí. */
  logout(): void {
    const current = this.session();
    this.session.set(null);
    if (current) this.accounts.update(list => list.filter(account => account.email !== current.email));
    this.forget();
    this.persistAccounts();
  }

  /** Olvida una cuenta recordada (si era la actual, equivale a cerrar su sesión). */
  forgetAccount(email: string): void {
    if (this.session()?.email === email) {
      this.logout();
      return;
    }
    this.accounts.update(list => list.filter(account => account.email !== email));
    this.persistAccounts();
  }

  /**
   * Vuelve a una cuenta recordada sin pedir otro código: el servidor comprueba su sesión y, si vale, devuelve una nueva. Si ya no vale (pasó
   * más de un mes sin entrar) la cuenta se olvida y el error lo trae 401, para que la pantalla pida un código nuevo.
   */
  resume(email: string): Observable<Session> {
    const account = this.accounts().find(item => item.email === email);
    if (!account) return throwError(() => new Error('Esa cuenta ya no está guardada.'));
    return this.http.get<Partial<Session>>(this.url('me/'), { headers: { Authorization: `Bearer ${account.token}` } }).pipe(
      map(answer => ({ token: answer?.token || account.token, email: account.email, name: answer?.name || account.name })),
      tap(session => this.save(session)),
      catchError(error => {
        if (error instanceof HttpErrorResponse && error.status === 401) this.forgetAccount(email);
        return throwError(() => error);
      })
    );
  }

  /**
   * Una vez por visita, quien ya entró le pregunta al servidor quién es y recibe una sesión nueva: mientras siga usando la herramienta no vuelve
   * a pedir el código (vale 30 días desde la última vez que entró). Si el servidor la rechaza, se pide entrar de nuevo.
   */
  renew(): void {
    const current = this.session();
    if (!this.browser || this.renewed || !current) return;
    this.renewed = true;
    this.http.get<Partial<Session>>(this.url('me/')).subscribe({
      next: answer => {
        if (answer?.token && this.session()?.email === current.email) this.save({ token: answer.token, email: current.email, name: current.name });
      },
      error: error => {
        if (error instanceof HttpErrorResponse && error.status === 401) this.expire();
      }
    });
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

  /** El servidor cerró la sala porque este correo no tiene invitación: se muestra la pantalla que lo explica. */
  notInvited(roomId: string | null): void {
    const router = this.injector.get(Router);
    void router.navigate(['/sin-acceso'], roomId ? { queryParams: { sala: roomId } } : {});
  }

  private save(session: Session): void {
    this.session.set(session);
    this.accounts.update(list => [session, ...list.filter(account => account.email !== session.email)].slice(0, MAX_ACCOUNTS));
    if (!this.browser) return;
    try {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
    } catch {
      // sin almacenamiento: la sesión vale para esta visita
    }
    this.persistAccounts();
  }

  /** Las cuentas guardadas de antes y, si la sesión de una versión anterior no está entre ellas, también esa. */
  private initialAccounts(): Session[] {
    const stored = readStoredAccounts();
    const active = readStoredSession();
    return active && !stored.some(account => account.email === active.email) ? [active, ...stored].slice(0, MAX_ACCOUNTS) : stored;
  }

  private persistAccounts(): void {
    if (!this.browser) return;
    try {
      localStorage.setItem(ACCOUNTS_STORAGE_KEY, JSON.stringify(this.accounts()));
    } catch {
      // sin almacenamiento: se recuerdan solo en esta visita
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
