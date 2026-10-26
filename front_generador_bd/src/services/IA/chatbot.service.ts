import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ChatbotService {
  constructor(private http: HttpClient) {}

  /** Mientras es verdadero, «Generar modelo» muestra que la IA está trabajando. */
  public isLoading = signal<boolean>(false);

  /**
   * Convierte la voz en el texto de la instrucción. Solo transcribe: la instrucción se manda después a la IA de la sala
   * (`IaActionsService.request`), igual que si se hubiera escrito, para que pase por los topes, la actividad y la conversación.
   */
  transcribeAudio(audio: Blob) {
    const formData = new FormData();

    const mimeType = audio.type.split(';', 1)[0] || 'audio/webm';
    const extension = mimeType === 'audio/ogg' ? 'ogg' : 'webm';

    formData.append('audio', audio, `instruccion-uml.${extension}`);
    formData.append('transcribe_only', '1');

    return this.http.post<{ transcript: string }>(`${environment.endpoint_python}api/uml_from_audio/`, formData);
  }
}
