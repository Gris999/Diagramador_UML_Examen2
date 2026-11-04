import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { saveAs } from 'file-saver';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class BackendGeneratorService {
  public loading=signal<boolean>(false);// estando para ver el estado de carga

  constructor(private http: HttpClient) {}

  /**
   * Envía el JSON UML al backend y descarga el zip generado.
   *
   * El host se deriva en runtime desde window.location, igual que ya hace
   * SignalingService para el WebSocket de colaboración, en vez de depender
   * de un dominio fijo en environment.ts (que se rompe en cada despliegue
   * distinto: local, EC2, dominio, etc.).
   *
   * El puerto es configurable via environment.springPort: en despliegues
   * directos (sin proxy) es 7001, tal cual publica docker-compose.app.yml.
   * Detrás de un reverse proxy de un solo origen (p.ej. Cloudflare Tunnel),
   * environment.springPort se deja vacío y se usa la ruta relativa
   * /generate, que nginx reenvía a 127.0.0.1:7001.
   */
  generateBackend(json: any, filename: string = 'backend.zip') {
    const protocol = window.location.protocol;
    const host = window.location.hostname;
    const port = environment.springPort ? `:${environment.springPort}` : '';
    const url = `${protocol}//${host}${port}/generate`;

    this.loading.set(true);
    this.http.post(url, json, {
      responseType: 'blob'
    }).subscribe({
      next: (zipBlob: Blob) => {
        saveAs(zipBlob, filename);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error generando backend:', err);
        this.loading.set(false);
        alert('No se pudo generar el backend. Inténtalo de nuevo en unos momentos.');
      }
    });
  }
}
