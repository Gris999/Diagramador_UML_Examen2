import { SignalingService } from './signaling.service';

describe('SignalingService connection lifecycle', () => {
  let realWebSocket: any;
  let createdSockets: any[];

  class FakeWebSocket {
    static instances: FakeWebSocket[] = [];
    readyState = 0; // WebSocket.CONNECTING
    onopen: (() => void) | null = null;
    onmessage: ((ev: any) => void) | null = null;
    onclose: (() => void) | null = null;
    closeSpy = jasmine.createSpy('close');

    constructor(public url: string) {
      createdSockets.push(this);
    }

    close() {
      this.readyState = 3; // WebSocket.CLOSED
      this.closeSpy();
    }
  }

  beforeEach(() => {
    createdSockets = [];
    realWebSocket = (window as any).WebSocket;
    (window as any).WebSocket = FakeWebSocket;
    // Preserve the readyState constants FakeWebSocket relies on implicitly.
    (window as any).WebSocket.CLOSED = 3;
  });

  afterEach(() => {
    (window as any).WebSocket = realWebSocket;
  });

  it('closes a still-open previous socket before opening a new one for the same or another room', () => {
    const service = new SignalingService();

    service.connect('room-1');
    expect(createdSockets.length).toBe(1);
    const firstSocket = createdSockets[0];
    firstSocket.readyState = 1; // OPEN, simulating a leaked connection

    service.connect('room-2');

    // Regresión: si el socket anterior no se cierra explícitamente antes de
    // reemplazarlo, la conexión queda registrada indefinidamente como
    // miembro de la sala en el backend (usuario fantasma).
    expect(firstSocket.closeSpy).toHaveBeenCalled();
    expect(createdSockets.length).toBe(2);
  });

  it('does not attempt to close an already-closed previous socket', () => {
    const service = new SignalingService();

    service.connect('room-1');
    const firstSocket = createdSockets[0];
    firstSocket.readyState = 3; // already CLOSED

    service.connect('room-2');

    expect(firstSocket.closeSpy).not.toHaveBeenCalled();
  });
});
