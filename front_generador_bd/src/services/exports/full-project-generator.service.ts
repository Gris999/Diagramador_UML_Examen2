import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { saveAs } from 'file-saver';
import { environment } from '../../environments/environment';

/**
 * Descarga única: un ZIP con el backend (Spring Boot), la app móvil (Flutter), el script SQL y las instrucciones,
 * todo a partir del mismo diagrama. El servidor lo arma en `api/generar_todo/`.
 */
@Injectable({ providedIn: 'root' })
export class FullProjectGeneratorService {
  private http = inject(HttpClient);
  private API = environment.endpoint_python;
  public loading = signal<boolean>(false);

  generateAll(json: any, fileName: string = 'proyecto-completo.zip') {
    this.loading.set(true);
    return this.http.post(`${this.API}api/generar_todo/`, json, { responseType: 'blob' }).subscribe({
      next: (zipBlob: Blob) => {
        saveAs(zipBlob, fileName);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error al generar el proyecto completo:', error);
        this.loading.set(false);
        alert('No se pudo generar el proyecto completo. Revisa que el diagrama tenga clases e inténtalo de nuevo en unos momentos.');
      }
    });
  }
}
