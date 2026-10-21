import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { UmlExportDTO } from '../exports/diagram-export.service';

@Injectable({
  providedIn: 'root'
})
export class XmiService {
  private readonly baseUrl = `${environment.endpoint_python}api/xmi`;

  constructor(private http: HttpClient) {}

  exportXmi(uml: UmlExportDTO): Observable<Blob> {
    // `association-class` es un conector visual auxiliar, no un tipo de
    // relación UML soportado por el intercambio XMI. Se filtra únicamente en
    // este borde: persistencia, colaboración y generadores aún lo necesitan.
    const xmiUml: UmlExportDTO = {
      ...uml,
      relationships: uml.relationships.filter(
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
