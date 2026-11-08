import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject, signal } from '@angular/core';

export type Theme = 'dark' | 'light';

/** Clave en el navegador donde se recuerda el tema elegido (solo una comodidad: sin ella se usa el oscuro). */
export const THEME_STORAGE_KEY = 'diagramador-tema';

/**
 * Tema de la interfaz: oscuro por defecto y claro a elección. Se aplica como `data-theme` en `<html>`, y las variables de color de
 * `styles.css` cambian con él. Un script pequeño de `index.html` lo pone antes del primer dibujo para que no haya parpadeo.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);
  private readonly browser = isPlatformBrowser(inject(PLATFORM_ID));

  readonly theme = signal<Theme>(this.saved());

  constructor() {
    this.apply(this.theme());
  }

  toggle(): void {
    this.set(this.theme() === 'dark' ? 'light' : 'dark');
  }

  set(theme: Theme): void {
    this.theme.set(theme);
    this.apply(theme);
    if (!this.browser) return;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Sin almacenamiento (ventana privada o bloqueado): el tema vale para esta visita y ya.
    }
  }

  private apply(theme: Theme): void {
    this.document.documentElement.setAttribute('data-theme', theme);
  }

  private saved(): Theme {
    if (!this.browser) return 'dark';
    try {
      return localStorage.getItem(THEME_STORAGE_KEY) === 'light' ? 'light' : 'dark';
    } catch {
      return 'dark';
    }
  }
}
