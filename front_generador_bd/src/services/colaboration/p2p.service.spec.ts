import { P2PService } from './p2p.service';

describe('P2PService ICE candidate buffering', () => {
  const remoteId = 'peer-b';
  const offer = { type: 'offer', sdp: 'offer-sdp' };
  const answer = { type: 'answer', sdp: 'answer-sdp' };

  let originalPeerConnection: typeof RTCPeerConnection;
  let originalSessionDescription: typeof RTCSessionDescription;
  let peerConnections: FakePeerConnection[];
  let signaling: any;
  let service: P2PService;

  class FakePeerConnection {
    remoteDescription: RTCSessionDescription | null = null;
    signalingState: RTCSignalingState = 'stable';
    onicecandidate: ((event: RTCPeerConnectionIceEvent) => void) | null = null;
    ondatachannel: ((event: RTCDataChannelEvent) => void) | null = null;

    addIceCandidate = jasmine.createSpy('addIceCandidate').and.resolveTo();
    close = jasmine.createSpy('close');
    createAnswer = jasmine.createSpy('createAnswer').and.resolveTo(answer as RTCSessionDescriptionInit);
    setLocalDescription = jasmine.createSpy('setLocalDescription').and.resolveTo();
    setRemoteDescription = jasmine.createSpy('setRemoteDescription').and.callFake(
      async (description: RTCSessionDescription) => {
        this.remoteDescription = description;
        this.signalingState = description.type === 'answer' ? 'stable' : 'have-remote-offer';
      }
    );
  }

  beforeEach(() => {
    originalPeerConnection = globalThis.RTCPeerConnection;
    originalSessionDescription = globalThis.RTCSessionDescription;
    peerConnections = [];

    (globalThis as any).RTCPeerConnection = class extends FakePeerConnection {
      constructor() {
        super();
        peerConnections.push(this);
      }
    };
    (globalThis as any).RTCSessionDescription = class {
      type: RTCSdpType;
      sdp: string;

      constructor(description: RTCSessionDescriptionInit) {
        this.type = description.type;
        this.sdp = description.sdp ?? '';
      }
    };

    signaling = {
      close: jasmine.createSpy('close'),
      sendSignal: jasmine.createSpy('sendSignal')
    };
    service = new P2PService(signaling);
  });

  afterEach(() => {
    (globalThis as any).RTCPeerConnection = originalPeerConnection;
    (globalThis as any).RTCSessionDescription = originalSessionDescription;
  });

  async function receive(payload: any) {
    await (service as any).handleSignaling({ type: 'signal', from: remoteId, payload });
  }

  it('queues ICE received before remoteDescription without applying it', async () => {
    await receive({ type: 'ice', candidate: { candidate: 'candidate-1' } });

    expect(peerConnections[0].addIceCandidate).not.toHaveBeenCalled();
  });

  it('flushes queued ICE in arrival order after an offer installs remoteDescription', async () => {
    const firstCandidate = { candidate: 'candidate-1' };
    const secondCandidate = { candidate: 'candidate-2' };
    await receive({ type: 'ice', candidate: firstCandidate });
    const pc = peerConnections[0];

    let resolveRemoteDescription!: () => void;
    pc.setRemoteDescription.and.callFake((description: RTCSessionDescription) => new Promise<void>(resolve => {
      resolveRemoteDescription = () => {
        pc.remoteDescription = description;
        pc.signalingState = 'have-remote-offer';
        resolve();
      };
    }));

    const offerHandling = receive(offer);
    await receive({ type: 'ice', candidate: secondCandidate });
    expect(pc.addIceCandidate).not.toHaveBeenCalled();

    resolveRemoteDescription();
    await offerHandling;

    expect(pc.addIceCandidate.calls.allArgs()).toEqual([
      [firstCandidate],
      [secondCandidate]
    ]);
  });

  it('flushes queued ICE in arrival order after an answer installs remoteDescription', async () => {
    const firstCandidate = { candidate: 'candidate-1' };
    const secondCandidate = { candidate: 'candidate-2' };
    await receive({ type: 'ice', candidate: firstCandidate });
    await receive({ type: 'ice', candidate: secondCandidate });
    const pc = peerConnections[0];
    pc.signalingState = 'have-local-offer';

    await receive(answer);

    expect(pc.addIceCandidate.calls.allArgs()).toEqual([
      [firstCandidate],
      [secondCandidate]
    ]);
  });

  it('applies ICE immediately when remoteDescription is ready', async () => {
    await receive(offer);
    const pc = peerConnections[0];
    pc.addIceCandidate.calls.reset();
    const candidate = { candidate: 'candidate-ready' };

    await receive({ type: 'ice', candidate });

    expect(pc.addIceCandidate).toHaveBeenCalledOnceWith(candidate);
  });

  it('does not apply flushed candidates twice', async () => {
    const candidate = { candidate: 'candidate-once' };
    await receive({ type: 'ice', candidate });
    const pc = peerConnections[0];

    await receive(offer);
    await receive(offer);

    expect(pc.addIceCandidate).toHaveBeenCalledOnceWith(candidate);
  });

  it('clears pending ICE when peers are closed', async () => {
    await receive({ type: 'ice', candidate: { candidate: 'candidate-pending' } });
    const peer = (service as any).peers.get(remoteId);

    service.closeSocketRTC();

    expect(peer.pendingIceCandidates).toEqual([]);
    expect(peer.pc.close).toHaveBeenCalled();
    expect(signaling.close).toHaveBeenCalled();
  });
});
