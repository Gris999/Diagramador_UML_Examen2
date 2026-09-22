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
});
