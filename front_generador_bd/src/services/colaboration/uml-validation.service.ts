import { Injectable } from '@angular/core';
import { environment } from '../../environments/environment';
import { resolveWsHost } from './ws-host.util';

@Injectable({ providedIn: 'root' })
export class UmlValidationService {
  private socket?: WebSocket;

  connect(onResult: (data: any) => void) {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = resolveWsHost(window.location, environment.WebSocket_python);

    const port =
      window.location.protocol === 'https:'
        ? ''
        : environment.wsPort
          ? `:${environment.wsPort}`
          : '';

    this.socket = new WebSocket(`${scheme}://${host}${port}/ws/uml/`);

    this.socket.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.action === 'validation_result') {
          onResult(data);
        }
      } catch (e) {
        console.error('Error parseando mensaje de validación', e);
      }
    };
  }


  validateModel(umlJson: any) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn('[UML Validation] WebSocket no conectado todavía');
      return;
    }

    const payload = {
      action: 'validate_model',
      uml: umlJson
    };
    this.socket.send(JSON.stringify(payload));
  }
}
