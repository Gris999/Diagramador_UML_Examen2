import { P2PService } from './p2p.service';

describe('P2PService collaboration roles', () => {
  let signaling: any;
  let service: P2PService;

  beforeEach(() => {
    signaling = {
      connect: jasmine.createSpy('connect'),
      broadcast: jasmine.createSpy('broadcast'),
      removeParticipant: jasmine.createSpy('removeParticipant')
    };
    service = new P2PService(signaling);
  });

  async function receive(message: any) {
    await (service as any).handleSignaling(message);
  }

  it('marks the client as removed when the host expels it', async () => {
    expect(service.removed()).toBeFalse();

    await receive({ type: 'removed', by: 'peer-host' });

    expect(service.removed()).toBeTrue();
  });

  it('starts every new connection as not expelled', async () => {
    await receive({ type: 'removed', by: 'peer-host' });
    expect(service.removed()).toBeTrue();

    service.init('sala-nueva');

    expect(service.removed()).toBeFalse();
    expect(signaling.connect).toHaveBeenCalledWith('sala-nueva', false);
  });

  it('takes its own id from the server welcome even when another peer joined first', async () => {
    await receive({ type: 'presence', action: 'self', peer: 'peer-me' });
    await receive({ type: 'presence', action: 'join', peer: 'peer-other' });

    expect(service.isCurrentParticipant('peer-me')).toBeTrue();
    expect(service.isCurrentParticipant('peer-other')).toBeFalse();
  });

  it('keeps working with servers that do not send the welcome (first join is its own)', async () => {
    await receive({ type: 'presence', action: 'join', peer: 'peer-me' });

    expect(service.isCurrentParticipant('peer-me')).toBeTrue();
  });

  it('updates local role state from presence snapshots', async () => {
    await receive({ type: 'presence', action: 'join', peer: 'peer-a' });
    await receive({
      type: 'presence',
      action: 'state',
      members: [
        { peer: 'peer-a', role: 'host', name: 'Ana' },
        { peer: 'peer-b', role: 'participant', name: 'Beatriz' }
      ]
    });

    expect(service.participants()).toEqual([
      { peer: 'peer-a', role: 'host', name: 'Ana' },
      { peer: 'peer-b', role: 'participant', name: 'Beatriz' }
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
