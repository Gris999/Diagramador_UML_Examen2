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
    return this.http.post(
      `${this.baseUrl}/export/`,
      uml,
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
