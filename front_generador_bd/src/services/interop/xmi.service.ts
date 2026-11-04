import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { UmlExportDTO } from '../exports/diagram-export.service';
import { resolveAssociationClassesForGenerators } from '../diagram/association-class.util';

@Injectable({
  providedIn: 'root'
})
export class XmiService {
  private readonly baseUrl = `${environment.endpoint_python}api/xmi`;

  constructor(private http: HttpClient) {}

  exportXmi(uml: UmlExportDTO): Observable<Blob> {
    // La clase asociativa que la herramienta genera sola (la M:N directa + un punteado hacia su medio) viaja en XMI
    // como una clase con dos relaciones 1:N, que es lo que el intercambio con Enterprise Architect ya entiende; así
    // al volver a importar el archivo no queda una M:N sin clase que la herramienta vuelva a completar sola.
    // `association-class` es un conector visual auxiliar, no un tipo de relación UML soportado por el intercambio
    // XMI: los que quedan se filtran únicamente en este borde (persistencia, colaboración y generadores lo necesitan).
    const resolved = resolveAssociationClassesForGenerators(uml as any, { onlyGenerated: true }) as unknown as UmlExportDTO;
    const xmiUml: UmlExportDTO = {
      ...resolved,
      relationships: resolved.relationships.filter(
        relationship => relationship.type !== 'association-class'
      )
    };
    return this.http.post(
      `${this.baseUrl}/export/`,
      xmiUml,
      {
        responseType: 'blob'
      }
    );
  }

  importXmi(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<any>(
      `${this.baseUrl}/import/`,
      formData
    );
  }
}
