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
    send = jasmine.createSpy('send');

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
    const service = new SignalingService({ getIdentity: () => ({ token: 'token', name: 'Ana' }) } as any);

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
    const service = new SignalingService({ getIdentity: () => ({ token: 'token', name: 'Ana' }) } as any);

    service.connect('room-1');
    const firstSocket = createdSockets[0];
    firstSocket.readyState = 3; // already CLOSED

    service.connect('room-2');

    expect(firstSocket.closeSpy).not.toHaveBeenCalled();
  });

  it('sends the remembered identity only after the socket opens', () => {
    const identity = {
      getIdentity: jasmine.createSpy('getIdentity').and.returnValue({
        token: '8edc7cac-cfe2-45f7-9142-84671025d21a',
        name: 'Ana'
      })
    };
    const service = new SignalingService(identity as any);

    service.connect('room-1');
    const socket = createdSockets[0];
    expect(socket.send).not.toHaveBeenCalled();

    socket.onopen();

    expect(identity.getIdentity).toHaveBeenCalledTimes(1);
    expect(JSON.parse(socket.send.calls.mostRecent().args[0])).toEqual({
      type: 'hello',
      token: '8edc7cac-cfe2-45f7-9142-84671025d21a',
      name: 'Ana'
    });
  });

  it('opens a read-only connection for viewers, without introducing itself', () => {
    const identity = { getIdentity: jasmine.createSpy('getIdentity') };
    const service = new SignalingService(identity as any);

    service.connect('room-1', true);
    const socket = createdSockets[0];
    socket.onopen();

    expect(socket.url).toMatch(/\/room-1\/\?mode=viewer$/);
    expect(socket.send).not.toHaveBeenCalled();
    expect(identity.getIdentity).not.toHaveBeenCalled();
  });

  it('keeps the plain room URL for editors', () => {
    const service = new SignalingService({ getIdentity: () => ({ token: 't', name: 'Ana' }) } as any);

    service.connect('room-1');

    expect(createdSockets[0].url).toMatch(/\/room-1\/$/);
  });

  describe('entering with the email', () => {
    const identity = { getIdentity: () => ({ token: 'token', name: 'Ana' }) } as any;

    afterEach(() => localStorage.removeItem('diagramador-sesion'));

    it('opens the socket with the session of the person in the address', () => {
      const service = new SignalingService(identity, { token: () => 'se sion/1', expire: jasmine.createSpy('expire') } as any);

      service.connect('room-1');

      expect(createdSockets[0].url).toMatch(/\/room-1\/\?s=se%20sion%2F1$/);
    });

    it('puts the session next to the viewer mode for the mobile view', () => {
      const service = new SignalingService(identity, { token: () => 'abc', expire: jasmine.createSpy('expire') } as any);

      service.connect('room-1', true);

      expect(createdSockets[0].url).toMatch(/\/room-1\/\?mode=viewer&s=abc$/);
    });

    it('reads the saved session when it is built without the auth service', () => {
      localStorage.setItem('diagramador-sesion', JSON.stringify({ token: 'guardada', email: 'a@b.co', name: 'A' }));

      new SignalingService(identity).connect('room-1');

      expect(createdSockets[0].url).toMatch(/\?s=guardada$/);
    });

    it('adds nothing to the address when nobody is logged in', () => {
      new SignalingService(identity, { token: () => null, expire: jasmine.createSpy('expire') } as any).connect('room-1');

      expect(createdSockets[0].url).toMatch(/\/room-1\/$/);
    });

    it('expires the session when the server closes the connection with 4401', () => {
      const expire = jasmine.createSpy('expire');
      new SignalingService(identity, { token: () => 'x', expire } as any).connect('room-1');

      (createdSockets[0].onclose as any)({ code: 4401 });

      expect(expire).toHaveBeenCalledTimes(1);
    });

    it('shows the "not invited" page when the server closes the connection with 4403', () => {
      const notInvited = jasmine.createSpy('notInvited');
      const expire = jasmine.createSpy('expire');
      new SignalingService(identity, { token: () => 'x', expire, notInvited } as any).connect('room-9');

      (createdSockets[0].onclose as any)({ code: 4403 });

      expect(notInvited).toHaveBeenCalledOnceWith('room-9');
      expect(expire).not.toHaveBeenCalled();
    });

    it('does not expire the session for any other way of closing', () => {
      const expire = jasmine.createSpy('expire');
      new SignalingService(identity, { token: () => 'x', expire } as any).connect('room-1');

      (createdSockets[0].onclose as any)({ code: 1006 });
      (createdSockets[0].onclose as any)();

      expect(expire).not.toHaveBeenCalled();
    });
  });
});


describe('SignalingService: the phone (viewer) reconnects by itself', () => {
  let realWebSocket: any;
  let sockets: any[];

  class FakeWebSocket {
    readyState = 0;
    onopen: (() => void) | null = null;
    onmessage: ((ev: any) => void) | null = null;
    onclose: ((event?: { code?: number }) => void) | null = null;
    closeSpy = jasmine.createSpy('close');
    send = jasmine.createSpy('send');
    constructor(public url: string) {
      sockets.push(this);
    }
    close() {
      this.readyState = 3;
      this.closeSpy();
    }
  }

  const identity = { getIdentity: () => ({ token: 't', name: 'Ana' }) } as any;

  beforeEach(() => {
    jasmine.clock().install();
    sockets = [];
    realWebSocket = (window as any).WebSocket;
    (window as any).WebSocket = FakeWebSocket;
    (window as any).WebSocket.CLOSED = 3;
  });

  afterEach(() => {
    jasmine.clock().uninstall();
    (window as any).WebSocket = realWebSocket;
  });

  it('reopens the connection after the system cuts it, waiting 1, 2 and 4 seconds', () => {
    const service = new SignalingService(identity);
    service.connect('sala', true);

    sockets[0].onclose({ code: 1006 });
    jasmine.clock().tick(999);
    expect(sockets.length).toBe(1);
    jasmine.clock().tick(1);
    expect(sockets.length).toBe(2);
    expect(sockets[1].url).toContain('mode=viewer');

    sockets[1].onclose({ code: 1006 });
    jasmine.clock().tick(2000);
    expect(sockets.length).toBe(3);

    sockets[2].onclose({ code: 1006 });
    jasmine.clock().tick(3999);
    expect(sockets.length).toBe(3);
    jasmine.clock().tick(1);
    expect(sockets.length).toBe(4);
  });

  it('starts again from one second after a connection that worked', () => {
    const service = new SignalingService(identity);
    service.connect('sala', true);
    sockets[0].onclose({ code: 1006 });
    jasmine.clock().tick(1000);
    sockets[1].onclose({ code: 1006 });
    jasmine.clock().tick(2000);

    sockets[2].onopen!();
    sockets[2].onclose({ code: 1006 });
    jasmine.clock().tick(1000);

    expect(sockets.length).toBe(4);
  });

  it('tells the app it is back only on the second opening, not on the first', () => {
    const service = new SignalingService(identity);
    const back = jasmine.createSpy('onReconnect');
    service.onReconnect = back;
    service.connect('sala', true);

    sockets[0].onopen!();
    expect(back).not.toHaveBeenCalled();

    sockets[0].onclose({ code: 1006 });
    jasmine.clock().tick(1000);
    sockets[1].onopen!();

    expect(back).toHaveBeenCalledTimes(1);
  });

  it('never sends an identity as a viewer, even when it reconnects', () => {
    const service = new SignalingService(identity);
    service.connect('sala', true);
    sockets[0].onclose({ code: 1006 });
    jasmine.clock().tick(1000);

    sockets[1].onopen!();

    expect(sockets[1].send).not.toHaveBeenCalled();
  });

  it('does not retry when the server says not to: session expired, no access or room full', () => {
    for (const code of [4401, 4403, 4009]) {
      sockets = [];
      const service = new SignalingService(identity, { token: () => 'x', expire: () => undefined, notInvited: () => undefined } as any);
      service.connect('sala', true);

      sockets[0].onclose({ code });
      jasmine.clock().tick(20000);

      expect(sockets.length).withContext(`código ${code}`).toBe(1);
    }
  });

  it('does not retry after leaving the room, even with a retry already waiting', () => {
    const service = new SignalingService(identity);
    service.connect('sala', true);
    sockets[0].onclose({ code: 1006 });

    service.close();
    jasmine.clock().tick(20000);

    expect(sockets.length).toBe(1);
  });

  it('does not retry for a person who edits: only the phone reconnects on its own', () => {
    const service = new SignalingService(identity);
    service.connect('sala');

    sockets[0].onclose({ code: 1006 });
    jasmine.clock().tick(20000);

    expect(sockets.length).toBe(1);
  });

  it('opens a new connection right away when the person comes back to the app, dropping the old one', () => {
    const service = new SignalingService(identity);
    service.connect('sala', true);
    sockets[0].readyState = 1; // abierta, pero el sistema pudo dejarla muerta sin avisar

    service.reconnectViewerNow();

    expect(sockets[0].closeSpy).toHaveBeenCalled();
    expect(sockets.length).toBe(2);
    expect(sockets[1].url).toContain('mode=viewer');
  });

  it('an old connection that closes after being replaced does not schedule another retry', () => {
    const service = new SignalingService(identity);
    service.connect('sala', true);
    const old = sockets[0];
    service.reconnectViewerNow();

    old.onclose?.({ code: 1006 });
    jasmine.clock().tick(20000);

    expect(sockets.length).toBe(2);
  });

  it('reconnectViewerNow does nothing for an editor or before connecting', () => {
    const service = new SignalingService(identity);
    service.reconnectViewerNow();
    service.connect('sala');
    service.reconnectViewerNow();

    expect(sockets.length).toBe(1);
  });
});

