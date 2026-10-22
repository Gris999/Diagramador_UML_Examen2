import { of } from 'rxjs';
import { CollaborationService } from './collaboration.service';

describe('CollaborationService full-state readiness', () => {
  let backup: any;
  let p2p: any;

  beforeEach(() => {
    jasmine.clock().install();
    backup = {
      getBackup: jasmine.createSpy('getBackup')
    };
    p2p = {
      closeSocketRTC: jasmine.createSpy('closeSocketRTC'),
      init: jasmine.createSpy('init'),
      sendToAll: jasmine.createSpy('sendToAll')
    };
  });

  afterEach(() => {
    jasmine.clock().uninstall();
  });

  function initializeWithCells(cells: any[]) {
    const service = new CollaborationService(p2p, backup);
    service.registerDiagramApi({
      getGraph: () => ({ getCells: () => cells }),
      getJoint: () => ({}),
      createUmlClass: () => undefined,
      loadFromJson: () => undefined,
      exportToJson: () => ({ classes: [], relationships: [] })
    });
    service.init('room-1');
    return service;
  }

  it('requests full state through the room after an empty graph becomes ready', () => {
    initializeWithCells([]);

    p2p.onReady();

    expect(p2p.sendToAll).toHaveBeenCalledOnceWith({ t: 'request_full_state' });
  });

  it('does not request full state when local room state already exists', () => {
    initializeWithCells([{ id: 'class-1' }]);

    p2p.onReady();

    expect(p2p.sendToAll).not.toHaveBeenCalled();
  });

  it('applies generated junction metadata idempotently for remote classes and links', () => {
    const cells = new Map<string, any>();
    const graph = {
      getCells: () => [...cells.values()],
      getCell: (id: string) => cells.get(id),
      getLinks: () => [...cells.values()].filter(cell => cell.kind === 'link'),
      addCell: (cell: any) => cells.set(cell.id, cell)
    };
    const createUmlClass = jasmine.createSpy('createUmlClass').and.callFake((payload: any) => {
      const state: Record<string, any> = {
        generatedJunction: !!payload.generated,
        junctionOrigin: payload.junctionOrigin,
        pendingJunctionSync: !!payload.pendingJunctionSync
      };
      const cell = {
        id: payload.id,
        payload,
        kind: 'class',
        get: (key: string) => state[key],
        set: (key: string, value: any) => { state[key] = value; }
      };
      cells.set(cell.id, cell);
      return cell;
    });
    const createTypedRelationship = jasmine.createSpy('createTypedRelationship').and.callFake(
      (sourceId: string, targetId: string, type: string) => {
        const state: Record<string, any> = {
          source: { id: sourceId }, target: { id: targetId }, relationType: type
        };
        return {
          id: '',
          kind: 'link',
          set(key: string, value: any) {
            state[key] = value;
            if (key === 'id') this.id = value;
          },
          get(key: string) { return state[key]; }
        };
      }
    );
    const service = new CollaborationService(p2p, backup);
    service.registerDiagramApi({
      getGraph: () => graph,
      getJoint: () => ({}),
      createUmlClass,
      createTypedRelationship,
      loadFromJson: () => undefined,
      exportToJson: () => ({ classes: [], relationships: [] })
    });

    const classOp: any = {
      t: 'add_class',
      id: 'junction:a:b:rel-1',
      payload: { name: 'A_B', generated: true, junctionOrigin: { id: 'rel-1' } }
    };
    const linkOp: any = {
      t: 'add_link',
      id: 'junction-link:junction:a:b:rel-1:source',
      sourceId: 'a',
      targetId: 'junction:a:b:rel-1',
      payload: { type: 'association', labels: [], generated: true }
    };
    const targetLinkOp: any = {
      ...linkOp,
      id: 'junction-link:junction:a:b:rel-1:target',
      sourceId: 'b'
    };

    (service as any).applyRemoteOp(classOp);
    (service as any).applyRemoteOp(classOp);
    (service as any).applyRemoteOp(linkOp);
    (service as any).applyRemoteOp(linkOp);
    (service as any).applyRemoteOp(targetLinkOp);
    (service as any).applyRemoteOp(targetLinkOp);

    expect(createUmlClass).toHaveBeenCalledTimes(1);
    expect(createUmlClass).toHaveBeenCalledWith(
      jasmine.objectContaining({ generated: true, junctionOrigin: { id: 'rel-1' } }),
      true
    );
    expect(createTypedRelationship).toHaveBeenCalledTimes(2);
    expect(cells.get(linkOp.id).get('generatedJunctionLeg')).toBeTrue();
    expect(cells.get(targetLinkOp.id).get('generatedJunctionLeg')).toBeTrue();
    expect(cells.get(classOp.id).get('pendingJunctionSync')).toBeFalse();
    expect(cells.size).toBe(3);
  });
});


describe('CollaborationService IA signals', () => {
  let p2p: any;
  let service: CollaborationService;

  beforeEach(() => {
    jasmine.clock().install();
    p2p = {
      closeSocketRTC: jasmine.createSpy('closeSocketRTC'),
      init: jasmine.createSpy('init'),
      sendToAll: jasmine.createSpy('sendToAll')
    };
    service = new CollaborationService(p2p, { getBackup: () => of(null) } as any);
    service.registerDiagramApi({
      getGraph: () => undefined,
      getJoint: () => ({}),
      createUmlClass: () => undefined,
      loadFromJson: () => undefined,
      exportToJson: () => ({ classes: [], relationships: [] })
    } as any);
    service.init('room-1');
  });

  afterEach(() => {
    jasmine.clock().uninstall();
  });

  it('marks as IA every operation broadcast while the action runs, and only then', () => {
    service.runAsIa(() => service.broadcast({ t: 'delete', id: 'c1' }));
    service.broadcast({ t: 'delete', id: 'c2' });

    expect(p2p.sendToAll.calls.allArgs()).toEqual([
      [{ t: 'delete', id: 'c1', via_ia: true }],
      [{ t: 'delete', id: 'c2' }]
    ]);
  });

  it('stops marking operations as IA even when the action throws', () => {
    expect(() => service.runAsIa(() => { throw new Error('falló'); })).toThrowError('falló');

    service.broadcast({ t: 'delete', id: 'c3' });

    expect(p2p.sendToAll).toHaveBeenCalledOnceWith({ t: 'delete', id: 'c3' });
  });

  it('shares the IA status with the room and shows the remote one without needing a graph', () => {
    service.setIaStatus('thinking', 'Ana');
    expect(service.iaStatus()).toEqual({ state: 'thinking', by: 'Ana' });
    expect(p2p.sendToAll).toHaveBeenCalledOnceWith({ t: 'ia_status', state: 'thinking', by: 'Ana' });

    p2p.onData('peer-2', { t: 'ia_status', state: 'idle', by: '' });

    expect(service.iaStatus()).toEqual({ state: 'idle', by: '' });
  });

  it('clears a thinking status by itself if the requester never reports back', () => {
    p2p.onData('peer-2', { t: 'ia_status', state: 'thinking', by: 'Beto' });
    expect(service.iaStatus().state).toBe('thinking');

    jasmine.clock().tick(90_001);

    expect(service.iaStatus()).toEqual({ state: 'idle', by: '' });
  });

  it('tracks applied suggestions locally and from other participants', () => {
    service.markSuggestionApplied(7, 0);
    p2p.onData('peer-2', { t: 'ia_suggestion_applied', eventId: 7, index: 2 });

    expect(service.appliedSuggestions().has('7:0')).toBeTrue();
    expect(service.appliedSuggestions().has('7:2')).toBeTrue();
    expect(service.appliedSuggestions().has('7:1')).toBeFalse();
    expect(p2p.sendToAll).toHaveBeenCalledOnceWith({ t: 'ia_suggestion_applied', eventId: 7, index: 0 });
  });
});

describe('CollaborationService viewer mode', () => {
  let p2p: any;
  let service: CollaborationService;

  beforeEach(() => {
    p2p = {
      closeSocketRTC: jasmine.createSpy('closeSocketRTC'),
      init: jasmine.createSpy('init'),
      sendToAll: jasmine.createSpy('sendToAll')
    };
    service = new CollaborationService(p2p, { getBackup: () => of(null) } as any);
    service.registerDiagramApi({
      getGraph: () => ({ getCells: () => [{ id: 'c1' }] }),
      getJoint: () => ({}),
      createUmlClass: () => undefined,
      loadFromJson: () => undefined,
      exportToJson: () => ({ classes: [], relationships: [] })
    } as any);
  });

  it('connects as a viewer when asked to', () => {
    service.init('room-1', { viewer: true });

    expect(p2p.init).toHaveBeenCalledOnceWith('room-1', true);
  });

  it('connects as an editor by default', () => {
    service.init('room-1');

    expect(p2p.init).toHaveBeenCalledOnceWith('room-1', false);
  });

  it('never sends operations as a viewer, except asking for the full state', () => {
    service.init('room-1', { viewer: true });

    service.broadcast({ t: 'delete', id: 'c1' });
    service.broadcast({ t: 'move', id: 'c1', x: 1, y: 2 });
    service.broadcast({ t: 'ia_status', state: 'thinking', by: 'Ana' });
    service.broadcast({ t: 'request_full_state' });

    expect(p2p.sendToAll.calls.allArgs()).toEqual([[{ t: 'request_full_state' }]]);
  });

  it('still applies what the room sends to a viewer', () => {
    const createUmlClass = jasmine.createSpy('createUmlClass');
    service.registerDiagramApi({
      getGraph: () => ({ getCells: () => [{ id: 'c1' }], getCell: () => undefined }),
      getJoint: () => ({}),
      createUmlClass,
      loadFromJson: () => undefined,
      exportToJson: () => ({ classes: [], relationships: [] })
    } as any);
    service.init('room-1', { viewer: true });

    p2p.onData('peer-1', { t: 'add_class', id: 'c9', payload: { name: 'Factura' } });

    expect(createUmlClass).toHaveBeenCalledOnceWith(
      jasmine.objectContaining({ id: 'c9', name: 'Factura' }),
      true
    );
  });
});
