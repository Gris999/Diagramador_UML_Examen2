import { isPlatformBrowser } from '@angular/common';
import { inject, Injectable, InjectionToken, PLATFORM_ID, signal } from '@angular/core';

/** Lo que se usa de la API de notificaciones del navegador (`window.Notification`). */
export type NotificationApi = {
  permission: NotificationPermission;
  requestPermission(): Promise<NotificationPermission>;
  new (title: string, options?: NotificationOptions): unknown;
};

/** El navegador no ofrece avisos (o es el servidor, en SSR). */
export type NotificationPermissionState = NotificationPermission | 'unsupported';

export const NOTIFICATION_API = new InjectionToken<NotificationApi | undefined>('NOTIFICATION_API', {
  providedIn: 'root',
  factory: () =>
    isPlatformBrowser(inject(PLATFORM_ID)) && typeof Notification !== 'undefined'
      ? (Notification as unknown as NotificationApi)
      : undefined
});

/** Android no deja crear un `Notification` directamente y el iPhone lo acepta sin mostrar nada: los avisos pasan por un service worker. */
export const SERVICE_WORKERS = new InjectionToken<ServiceWorkerContainer | undefined>('SERVICE_WORKERS', {
  providedIn: 'root',
  factory: () =>
    isPlatformBrowser(inject(PLATFORM_ID)) && typeof navigator !== 'undefined' ? navigator.serviceWorker : undefined
});

const WORKER_URL = '/notification-sw.js';
const MAX_BODY_CHARS = 140;

/**
 * Avisos del navegador para la vista de seguimiento del celular. Solo funcionan con la página abierta: no hay servidor de avisos ni
 * suscripción push.
 */
@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly api = inject(NOTIFICATION_API);
  private readonly workers = inject(SERVICE_WORKERS);
  private registration?: Promise<ServiceWorkerRegistration>;

  readonly permission = signal<NotificationPermissionState>(this.api ? this.api.permission : 'unsupported');

  /** Pide el permiso al navegador. Si ya se concedió o se bloqueó no vuelve a preguntar. */
  async requestPermission(): Promise<NotificationPermissionState> {
    if (!this.api) return 'unsupported';
    if (this.api.permission === 'default') {
      try {
        this.permission.set(await this.api.requestPermission());
      } catch {
        this.permission.set(this.api.permission);
      }
    } else {
      this.permission.set(this.api.permission);
    }
    return this.permission();
  }

  /** Alguien cambió el diagrama: el título es quién y el cuerpo, qué hizo. */
  notifyChange(author: string, summary: string): void {
    this.show(author, summary);
  }

  /** La IA dejó una idea o una revisión. */
  notifyIdea(text: string): void {
    this.show('Nueva idea de la IA', text);
  }

  /**
   * El service worker va primero: es la única forma que muestra el aviso en el iPhone (la app agregada a Inicio) y en Android.
   * En el iPhone `new Notification()` no da error pero tampoco muestra nada, así que no sirve como "plan A con respaldo".
   */
  private show(title: string, text: string): void {
    if (!this.api || this.permission() !== 'granted') return;
    const options: NotificationOptions = { body: this.shorten(text), tag: 'uml-follow' };
    if (!this.workers) {
      this.showDirectly(title, options);
      return;
    }
    void this.showFromWorker(title, options).then(shown => {
      if (!shown) this.showDirectly(title, options);
    });
  }

  private showDirectly(title: string, options: NotificationOptions): void {
    if (!this.api) return;
    try {
      new this.api(title, options);
    } catch {
      // Sin ninguna forma de avisar en este navegador: la actividad sigue visible en la pantalla.
    }
  }

  private async showFromWorker(title: string, options: NotificationOptions): Promise<boolean> {
    try {
      const registration = await this.workerRegistration();
      await registration.showNotification(title, options);
      return true;
    } catch {
      this.registration = undefined;
      return false;
    }
  }

  /** El service worker se registra una sola vez y se reutiliza en cada aviso. */
  private workerRegistration(): Promise<ServiceWorkerRegistration> {
    const workers = this.workers;
    if (!workers) return Promise.reject(new Error('Sin service workers'));
    this.registration ??= workers.register(WORKER_URL).then(() => workers.ready);
    return this.registration;
  }

  private shorten(text: string): string {
    return text.length > MAX_BODY_CHARS ? `${text.slice(0, MAX_BODY_CHARS - 1)}…` : text;
  }
}
