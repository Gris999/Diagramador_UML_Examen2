import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ChatbotService {
  constructor(private http: HttpClient) {}

  public isLoading=signal<boolean>(false);

  generateDiagram(prompt: string, uml: any | null = null) {
    return this.http.post<any>(`${environment.endpoint_python}api/chatbot/`, {
      prompt,
      uml
    });
  }

  generateDiagramFromAudio(audio: Blob, uml: any | null = null) {
    const formData = new FormData();

    const mimeType =
      audio.type.split(';', 1)[0] || 'audio/webm';

    const extension =
      mimeType === 'audio/ogg' ? 'ogg' : 'webm';

    formData.append(
      'audio',
      audio,
      `instruccion-uml.${extension}`
    );

    if (uml) {
      formData.append('uml', JSON.stringify(uml));
    }

    return this.http.post<any>(
      `${environment.endpoint_python}api/uml_from_audio/`,
      formData
    );
  }

}
