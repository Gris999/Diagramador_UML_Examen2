import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { saveAs } from 'file-saver';

// Puerto fijo del generador Spring (back_generator_uml), publicado tal cual
// en docker-compose.app.yml (SERVER_PORT=7001, "7001:7001").
const SPRING_GENERATOR_PORT = 7001;

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
   */
  generateBackend(json: any, filename: string = 'backend.zip') {
    const protocol = window.location.protocol;
    const host = window.location.hostname;
    const url = `${protocol}//${host}:${SPRING_GENERATOR_PORT}/generate`;

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
      }
    });
  }
}
