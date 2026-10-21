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
