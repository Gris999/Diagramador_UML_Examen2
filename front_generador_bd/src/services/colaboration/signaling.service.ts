import { Injectable } from '@angular/core';
import { environment } from '../../environments/environment';
import { ActivityEvent } from './activity-event';
import { AuthService, readStoredSession } from '../auth/auth.service';
import { IdentityService } from './identity.service';
import { resolveWsHost } from './ws-host.util';

type CollaborationParticipant = {
  peer: string;
  role: 'host' | 'participant';
  name?: string | null;
};

type Msg =
  | {
      type: 'presence';
      action: 'self' | 'join' | 'leave' | 'remove' | 'state';
      peer?: string;
      members?: CollaborationParticipant[];
    }
  | { type: 'signal'; from: string; payload: any }
  | { type: 'broadcast'; from: string; payload: any }
  | { type: 'activity'; event: ActivityEvent }
  | { type: 'chat'; message?: unknown }
  | { type: 'removed'; by: string }
  | { type: 'remove_rejected' };

@Injectable({ providedIn: 'root' })
export class SignalingService {
  private socket!: WebSocket;
  private _roomId!: string;
  public onMessage?: (msg: Msg) => void;

  /** `auth` es opcional para quien arma el servicio a mano (pruebas): sin él se lee la sesión guardada en el navegador. */
  constructor(private readonly identity: IdentityService, private readonly auth?: AuthService) {}

  /** `viewer`: conexión de solo lectura (vista móvil); no entra al orden de roles de la sala. */
  connect(roomId: string, viewer = false) {
    // Evita conexiones fantasma: si ya había un socket abierto (por ejemplo,
    // el componente anterior no cerró la sala correctamente), se cierra antes
    // de abrir uno nuevo para no dejarlo registrado como miembro en el backend.
    if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
      this.socket.onclose = null;
      this.socket.close();
    }
    this._roomId = roomId;

    // Detecta ws:// o wss:// correctamente
    //const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
    //const wsUrl = `${scheme}://${location.hostname}:8000/ws/canvas/${roomId}/`;
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = resolveWsHost(window.location, environment.WebSocket_python);

    const port =

      //   window.location.protocol === 'https:'
      //     ? ''
      //     : environment.wsPort
      //       ? `:${environment.wsPort}`
      //       : '';
      // const wsUrl = `${scheme}://${host}${port}${environment.wsPath}${roomId}/`;

      window.location.protocol === 'https:'
        ? ''
        : environment.wsPort
          ? `:${environment.wsPort}`
          : '';
    // Con el servidor en modo «entrar con el correo», la sesión viaja en la dirección (`?s=`): sin ella el servidor cierra la conexión con 4401.
    const params: string[] = [];
    if (viewer) params.push('mode=viewer');
    const session = this.auth?.token() ?? readStoredSession()?.token;
    if (session) params.push(`s=${encodeURIComponent(session)}`);
    const wsUrl = `${scheme}://${host}${port}${environment.wsPath}${roomId}/${params.length ? '?' + params.join('&') : ''}`;

    console.log('[Signaling] Connecting to', wsUrl);
    const socket = new WebSocket(wsUrl);
    this.socket = socket;

    socket.onopen = () => {
      console.log('[Signaling] Connected to', wsUrl);
      // Quien solo observa no se identifica ni pide nombre.
      if (viewer) return;
      const identity = this.identity.getIdentity();
      socket.send(JSON.stringify({ type: 'hello', ...identity }));
    };
    socket.onmessage = (ev) => {
      try {
        const msg: Msg = JSON.parse(ev.data);
        if (this.onMessage) this.onMessage(msg);
      } catch (e) {
        console.error('[Signaling] Error parsing message', e);
      }
    };
    socket.onclose = (event?: { code?: number }) => {
      console.log('[Signaling] Disconnected');
      // 4401: el servidor no aceptó la sesión (venció o no es válida): se borra y se vuelve a la pantalla de entrada.
      if (event?.code === 4401) this.auth?.expire();
      // 4403: la sesión vale pero ese correo no está en la lista de la sala.
      if (event?.code === 4403) this.auth?.notInvited(roomId);
    };
  }

  sendSignal(to: string, payload: any) {
    this.socket?.send(JSON.stringify({ type: 'signal', to, payload }));
  }

  broadcast(payload: any) {
    this.socket?.send(JSON.stringify({ type: 'broadcast', payload }));
  }

  removeParticipant(peer: string) {
    this.socket?.send(JSON.stringify({ type: 'remove_participant', peer }));
  }

  close() {
    this.socket?.close();
  }
}
