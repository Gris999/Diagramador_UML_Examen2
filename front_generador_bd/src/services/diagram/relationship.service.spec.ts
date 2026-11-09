import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { DiagramService } from './diagram.service';
import { RelationshipService } from './relationship.service';
import { ToolService } from './tool.service';

describe('RelationshipService (choosing the classes by clicking)', () => {
  let service: RelationshipService;
  let tools: ToolService;
  let diagram: { createTypedRelationship: jasmine.Spy };
  let handlers: Record<string, (view: any) => void>;
  let paper: any;
  let container: HTMLElement;
  let views: Map<string, { highlight: jasmine.Spy; unhighlight: jasmine.Spy }>;

  const cell = (id: string, link = false) => ({ id, isLink: () => link, get: () => 'association' });
  const click = (model: any) => handlers['cell:pointerclick']({ model });

  beforeEach(() => {
    handlers = {};
    views = new Map();
    paper = {
      on: (name: string, handler: any) => (handlers[name] = handler),
      off: (name: string) => delete handlers[name],
      findViewByModel: (model: any) => {
        if (!views.has(model.id)) views.set(model.id, { highlight: jasmine.createSpy('highlight'), unhighlight: jasmine.createSpy('unhighlight') });
        return views.get(model.id);
      }
    };
    container = document.createElement('div');
    diagram = { createTypedRelationship: jasmine.createSpy('createTypedRelationship') };
    TestBed.configureTestingModule({ providers: [provideZonelessChangeDetection(), { provide: DiagramService, useValue: diagram }] });
    service = TestBed.inject(RelationshipService);
    tools = TestBed.inject(ToolService);
  });

  it('first click chooses the origin (highlighted), second creates the relationship and frees the tool', () => {
    tools.arm('association');
    service.startLinkCreation(paper, container, 'association');

    click(cell('a'));
    expect(tools.chosen()).toBe(1);
    expect(views.get('a')!.highlight).toHaveBeenCalled();
    expect(diagram.createTypedRelationship).not.toHaveBeenCalled();

    click(cell('b'));

    expect(diagram.createTypedRelationship).toHaveBeenCalledOnceWith('a', 'b', 'association');
    expect(views.get('a')!.unhighlight).toHaveBeenCalled();
    expect(tools.armed()).toBeNull();
    expect(handlers['cell:pointerclick']).toBeUndefined();
    expect(container.style.cursor).toBe('default');
  });

  it('shows the crosshair while waiting', () => {
    service.startLinkCreation(paper, container, 'generalization');

    expect(container.style.cursor).toBe('crosshair');
  });

  it('a second click on the same class does not join it with itself: it keeps waiting for the destination', () => {
    tools.arm('association');
    service.startLinkCreation(paper, container, 'association');

    click(cell('a'));
    click(cell('a'));

    expect(diagram.createTypedRelationship).not.toHaveBeenCalled();
    expect(tools.armed()).toBe('association');

    click(cell('b'));

    expect(diagram.createTypedRelationship).toHaveBeenCalledOnceWith('a', 'b', 'association');
  });

  it('a line cannot be an end of an ordinary relationship', () => {
    tools.arm('composition');
    service.startLinkCreation(paper, container, 'composition');

    click(cell('line', true));

    expect(tools.chosen()).toBe(0);
  });

  it('an association class joins a class and a line, in either order', () => {
    service.startLinkCreation(paper, container, 'association-class');
    click(cell('line', true));
    click(cell('clase'));
    expect(diagram.createTypedRelationship).toHaveBeenCalledWith('clase', 'line', 'association-class');

    diagram.createTypedRelationship.calls.reset();
    service.startLinkCreation(paper, container, 'association-class');
    click(cell('clase2'));
    click(cell('line2', true));
    expect(diagram.createTypedRelationship).toHaveBeenCalledWith('clase2', 'line2', 'association-class');
  });

  it('cancelling drops the highlight, the cursor and the listener without creating anything', () => {
    service.startLinkCreation(paper, container, 'association');
    click(cell('a'));

    service.cancelLinkCreation(container);

    expect(views.get('a')!.unhighlight).toHaveBeenCalled();
    expect(handlers['cell:pointerclick']).toBeUndefined();
    expect(container.style.cursor).toBe('default');
    expect(diagram.createTypedRelationship).not.toHaveBeenCalled();
  });
});
