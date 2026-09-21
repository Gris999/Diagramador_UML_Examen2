import { P2PService } from './p2p.service';

describe('P2PService collaboration roles', () => {
  let signaling: any;
  let service: P2PService;

  beforeEach(() => {
    signaling = {
      broadcast: jasmine.createSpy('broadcast'),
      removeParticipant: jasmine.createSpy('removeParticipant')
    };
    service = new P2PService(signaling);
  });

  async function receive(message: any) {
    await (service as any).handleSignaling(message);
  }

  it('updates local role state from presence snapshots', async () => {
    await receive({ type: 'presence', action: 'join', peer: 'peer-a' });
    await receive({
      type: 'presence',
      action: 'state',
      members: [
        { peer: 'peer-a', role: 'host' },
        { peer: 'peer-b', role: 'participant' }
      ]
    });

    expect(service.participants()).toEqual([
      { peer: 'peer-a', role: 'host' },
      { peer: 'peer-b', role: 'participant' }
    ]);
    expect(service.isHost()).toBeTrue();
  });

  it('reflects promotion when a later snapshot makes the local peer host', async () => {
    await receive({ type: 'presence', action: 'join', peer: 'peer-b' });
    await receive({
      type: 'presence',
      action: 'state',
      members: [
        { peer: 'peer-a', role: 'host' },
        { peer: 'peer-b', role: 'participant' }
      ]
    });
    expect(service.isHost()).toBeFalse();

    await receive({
      type: 'presence',
      action: 'state',
      members: [
        { peer: 'peer-b', role: 'host' }
      ]
    });

    expect(service.isHost()).toBeTrue();
  });

  it('only sends removal requests when the local peer is host', async () => {
    await receive({ type: 'presence', action: 'join', peer: 'peer-a' });
    await receive({
      type: 'presence',
      action: 'state',
      members: [
        { peer: 'peer-a', role: 'participant' },
        { peer: 'peer-b', role: 'host' }
      ]
    });
    service.removeParticipant('peer-b');
    expect(signaling.removeParticipant).not.toHaveBeenCalled();

    await receive({
      type: 'presence',
      action: 'state',
      members: [
        { peer: 'peer-a', role: 'host' },
        { peer: 'peer-b', role: 'participant' }
      ]
    });
    service.removeParticipant('peer-b');

    expect(signaling.removeParticipant).toHaveBeenCalledOnceWith('peer-b');
  });
});
