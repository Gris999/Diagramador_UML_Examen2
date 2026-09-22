import { P2PService } from './p2p.service';

describe('P2PService WebSocket operation transport', () => {
  let signaling: any;
  let service: P2PService;

  beforeEach(() => {
    signaling = {
      broadcast: jasmine.createSpy('broadcast'),
      close: jasmine.createSpy('close'),
      connect: jasmine.createSpy('connect'),
      removeParticipant: jasmine.createSpy('removeParticipant'),
      sendSignal: jasmine.createSpy('sendSignal')
    };
    service = new P2PService(signaling);
  });

  async function receive(message: any) {
    await (service as any).handleSignaling(message);
  }

  it('broadcasts create, update, delete, and move through the signaling WebSocket', () => {
    const rtcSend = jasmine.createSpy('rtcSend');
    (service as any).peers.set('peer-b', {
      pc: {},
      dc: { readyState: 'open', send: rtcSend },
      pendingIceCandidates: []
    });
    const operations = [
      { t: 'add_class', id: 'class-1', payload: { name: 'User' } },
      { t: 'edit_text', id: 'class-1', field: 'name', value: 'Customer' },
      { t: 'delete', id: 'class-1' },
      { t: 'move', id: 'class-1', x: 40, y: 60 }
    ];

    operations.forEach(operation => service.sendToAll(operation));

    expect(signaling.broadcast.calls.allArgs()).toEqual(
      operations.map(operation => [operation])
    );
    expect(rtcSend).not.toHaveBeenCalled();
  });

  it('delivers remote WebSocket operations to the collaboration handler', async () => {
    service.onData = jasmine.createSpy('onData');
    await receive({ type: 'presence', action: 'join', peer: 'peer-a' });
    signaling.broadcast.calls.reset();
    const operation = { t: 'delete', id: 'class-1' };

    await receive({ type: 'broadcast', from: 'peer-b', payload: operation });

    expect(service.onData).toHaveBeenCalledOnceWith('peer-b', operation);
  });

  it('ignores WebSocket broadcasts echoed from the current client', async () => {
    service.onData = jasmine.createSpy('onData');
    await receive({ type: 'presence', action: 'join', peer: 'peer-a' });

    await receive({
      type: 'broadcast',
      from: 'peer-a',
      payload: { t: 'edit_text', id: 'class-1', field: 'name', value: 'User' }
    });

    expect(service.onData).not.toHaveBeenCalled();
  });

  it('reports readiness once when the server assigns the local identity', async () => {
    service.onReady = jasmine.createSpy('onReady');

    await receive({ type: 'presence', action: 'join', peer: 'peer-a' });
    await receive({ type: 'presence', action: 'join', peer: 'peer-b' });

    expect(service.onReady).toHaveBeenCalledTimes(1);
  });
});
