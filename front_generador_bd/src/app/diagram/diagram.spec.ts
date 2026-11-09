import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { ActivityEvent } from '../../services/colaboration/activity-event';
import { P2PService } from '../../services/colaboration/p2p.service';
import { DiagramService } from '../../services/diagram/diagram.service';
import { RelationshipService } from '../../services/diagram/relationship.service';
import { ToolService } from '../../services/diagram/tool.service';

import { Diagram } from './diagram';

describe('Diagram', () => {
  let component: Diagram;
  let fixture: ComponentFixture<Diagram>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Diagram],
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'sala-prueba' } } } }
      ]
    })
    .compileComponents();

    // Solo se instancia: detectChanges() arrancaría JointJS y la colaboración
    // (WebSocket), que no son lo que verifica esta prueba de cableado.
    fixture = TestBed.createComponent(Diagram);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('tells an expelled participant and sends them back to the start page', () => {
    const alertSpy = spyOn(window, 'alert');
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    const diagram = TestBed.inject(DiagramService);
    const clearStorage = spyOn(diagram, 'clearStorage');
    const closeDiagram = spyOn(diagram, 'closeDiagram');
    (component as any).roomId = 'sala-prueba';

    TestBed.inject(P2PService).removed.set(true);
    TestBed.tick();

    expect(alertSpy).toHaveBeenCalledOnceWith('El host te expulsó de la sala.');
    expect(clearStorage).toHaveBeenCalled();
    // Su copia puede estar atrasada: no debe guardar un respaldo final.
    expect(closeDiagram).toHaveBeenCalledOnceWith('sala-prueba', { saveBackup: false });
    expect(navigate).toHaveBeenCalledOnceWith(['/']);
  });

  it('does nothing while nobody has been expelled', () => {
    const alertSpy = spyOn(window, 'alert');

    TestBed.tick();

    expect(alertSpy).not.toHaveBeenCalled();
  });

  describe('top bar', () => {
    const activity = (id: number): ActivityEvent => ({
      id, room: 'sala-prueba', actor: 1, actor_name: 'Ana', actor_kind: 'human', type: 'class_added',
      target_id: String(id), summary: 'añadió una clase', data: {}, created_at: '2026-11-08T10:00:00Z'
    });

    it('opens one menu at a time and closes it when its button is tapped again', () => {
      expect(component.menu()).toBeNull();

      component.toggleMenu('activity');
      expect(component.menu()).toBe('activity');

      component.toggleMenu('participants');
      expect(component.menu()).toBe('participants');

      component.toggleMenu('participants');
      expect(component.menu()).toBeNull();
    });

    it('closes the open menu when something outside of the menus is tapped, but not when a menu itself is tapped', () => {
      component.toggleMenu('participants');
      const inside = document.createElement('div');
      inside.setAttribute('data-menu-root', '');
      const child = document.createElement('button');
      inside.appendChild(child);
      document.body.appendChild(inside);
      const outside = document.createElement('p');
      document.body.appendChild(outside);

      try {
        child.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        expect(component.menu()).toBe('participants');

        outside.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        expect(component.menu()).toBeNull();
      } finally {
        inside.remove();
        outside.remove();
      }
    });

    it('closes the open menu with Escape', () => {
      component.toggleMenu('activity');

      component.handleEscape(new KeyboardEvent('keydown', { key: 'Escape' }));

      expect(component.menu()).toBeNull();
    });

    it('counts the activity that arrives while the menu is closed and clears the count once it is opened', () => {
      const p2p = TestBed.inject(P2PService);
      expect(component.unreadActivity()).toBe(0);

      p2p.liveActivityEvents.set([activity(1), activity(2), activity(3)]);
      expect(component.unreadActivity()).toBe(3);

      component.toggleMenu('activity');
      expect(component.unreadActivity()).toBe(0);

      // Mientras el menú está abierto, lo nuevo se ve ahí mismo: al cerrarlo no queda como pendiente.
      p2p.liveActivityEvents.update(events => [...events, activity(4)]);
      expect(component.unreadActivity()).toBe(0);
      component.toggleMenu('activity');
      expect(component.unreadActivity()).toBe(0);

      p2p.liveActivityEvents.update(events => [...events, activity(5)]);
      expect(component.unreadActivity()).toBe(1);
    });

    it('does not mark the activity as seen when only the participants menu is used', () => {
      TestBed.inject(P2PService).liveActivityEvents.set([activity(1)]);

      component.toggleMenu('participants');

      expect(component.unreadActivity()).toBe(1);
    });

    it('shows at most three people in the top bar and summarizes the rest', () => {
      const p2p = TestBed.inject(P2PService);
      p2p.participants.set(['Ana', 'Beto', 'Carla', 'Diego', 'Elena'].map((name, index) => ({ peer: 'p' + index, role: index === 0 ? 'host' : 'participant', name })));

      expect(component.participantList().length).toBe(5);
      expect(component.visiblePeople().map(person => person.name)).toEqual(['Ana', 'Beto', 'Carla']);
      expect(component.hiddenPeople()).toBe(2);
    });

    it('names a person by what they gave or, for old connections, by their place in the list', () => {
      expect(component.personName({ name: 'Ana' }, 0)).toBe('Ana');
      expect(component.personName({ name: null }, 1)).toBe('Usuario 2');
      expect(component.personName({}, 2)).toBe('Usuario 3');
    });

    it('opens the share window with the code of the room and closes the menu', () => {
      component.toggleMenu('activity');

      component.openShare();

      expect(component.shareOpen()).toBeTrue();
      expect(component.menu()).toBeNull();
      expect(component.roomCode).toBe('sala-prueba');
    });

    it('hides and shows the tools panel', () => {
      expect(component.sidebarOpen()).toBeTrue();

      component.toggleSidebar();
      expect(component.sidebarOpen()).toBeFalse();

      component.toggleSidebar();
      expect(component.sidebarOpen()).toBeTrue();
    });

    it('tells that the canvas is empty until the graph has elements', () => {
      expect(component.isEmpty()).toBeTrue();
    });
  });

  describe('the tool chosen with a click', () => {
    let paper: { once: jasmine.Spy; off: jasmine.Spy };
    let container: HTMLElement;
    let diagram: any;
    let createUmlClass: jasmine.Spy;
    let tools: ToolService;

    beforeEach(() => {
      paper = { once: jasmine.createSpy('once'), off: jasmine.createSpy('off') };
      container = document.createElement('div');
      (component as any).paperContainer = { nativeElement: container };
      diagram = TestBed.inject(DiagramService) as any;
      diagram.paper = paper;
      diagram.readOnly = false;
      createUmlClass = spyOn(diagram, 'createUmlClass');
      tools = TestBed.inject(ToolService);
    });

    afterEach(() => {
      diagram.paper = undefined;
      tools.clear();
    });

    it('puts a class where the next click on the empty canvas lands, centred on it, and frees the tool', () => {
      tools.arm('class');
      TestBed.tick();

      expect(paper.once).toHaveBeenCalledOnceWith('blank:pointerclick', jasmine.any(Function));
      expect(container.style.cursor).toBe('crosshair');

      paper.once.calls.mostRecent().args[1]({}, 300, 205);

      expect(createUmlClass).toHaveBeenCalledOnceWith(jasmine.objectContaining({ name: 'Entidad', position: { x: 210, y: 150 } }));
      expect(tools.armed()).toBeNull();
    });

    it('never places a class outside of the canvas (negative corner)', () => {
      tools.arm('class');
      TestBed.tick();

      paper.once.calls.mostRecent().args[1]({}, 10, 10);

      expect(createUmlClass).toHaveBeenCalledOnceWith(jasmine.objectContaining({ position: { x: 0, y: 0 } }));
    });

    it('starts choosing the two classes when a relationship is chosen', () => {
      const start = spyOn(TestBed.inject(RelationshipService), 'startLinkCreation');

      tools.arm('composition');
      TestBed.tick();

      expect(start).toHaveBeenCalledOnceWith(paper, container, 'composition');
    });

    it('Escape lets the tool go and removes the click it was waiting for', () => {
      tools.arm('class');
      TestBed.tick();

      component.handleEscape(new KeyboardEvent('keydown', { key: 'Escape' }));
      TestBed.tick();

      expect(tools.armed()).toBeNull();
      expect(paper.off).toHaveBeenCalledWith('blank:pointerclick', jasmine.any(Function));
      expect(container.style.cursor).toBe('default');
    });

    it('Escape cancels a relationship that was half chosen', () => {
      const cancel = spyOn(TestBed.inject(RelationshipService), 'cancelLinkCreation');
      spyOn(TestBed.inject(RelationshipService), 'startLinkCreation');
      tools.arm('association');
      TestBed.tick();

      component.handleEscape(new KeyboardEvent('keydown', { key: 'Escape' }));
      TestBed.tick();

      expect(cancel).toHaveBeenCalledWith(container);
    });

    it('choosing another tool drops the click the first one was waiting for', () => {
      spyOn(TestBed.inject(RelationshipService), 'startLinkCreation');
      tools.arm('class');
      TestBed.tick();

      tools.arm('dependency');
      TestBed.tick();

      expect(paper.off).toHaveBeenCalledWith('blank:pointerclick', jasmine.any(Function));
    });

    it('does nothing in a diagram that can only be read', () => {
      diagram.readOnly = true;

      tools.arm('class');
      TestBed.tick();

      expect(paper.once).not.toHaveBeenCalled();
      expect(tools.armed()).toBeNull();
    });

    it('dragging a relationship from the palette to the canvas chooses it, as the click does', () => {
      container.getBoundingClientRect = () => ({ left: 100, top: 50 }) as DOMRect;

      component.onDragEnded({ source: { data: { type: 'generalization' } }, dropPoint: { x: 400, y: 300 } } as any);

      expect(tools.armed()).toBe('generalization');
    });

    it('dragging a class from the palette still puts it where it was dropped', () => {
      container.getBoundingClientRect = () => ({ left: 100, top: 50 }) as DOMRect;

      component.onDragEnded({ source: { data: { type: 'class' } }, dropPoint: { x: 400, y: 300 } } as any);

      expect(createUmlClass).toHaveBeenCalledOnceWith(jasmine.objectContaining({ position: { x: 300, y: 250 } }));
      expect(tools.armed()).toBeNull();
    });
  });
});

describe('Diagram opened after an expulsion', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Diagram],
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'sala-prueba' } } } }
      ]
    }).compileComponents();
  });

  it('does not treat a person expelled earlier as expelled again when they come back to the room', () => {
    const alertSpy = spyOn(window, 'alert');
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    // El servicio vive toda la sesión: el aviso de la expulsión anterior sigue ahí cuando la persona vuelve a entrar sin recargar la página.
    TestBed.inject(P2PService).removed.set(true);

    TestBed.createComponent(Diagram);
    TestBed.tick();

    expect(alertSpy).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });

  it('still expels the person when the host removes them while they are in the new visit', () => {
    const alertSpy = spyOn(window, 'alert');
    spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    spyOn(TestBed.inject(DiagramService), 'clearStorage');
    spyOn(TestBed.inject(DiagramService), 'closeDiagram');
    TestBed.inject(P2PService).removed.set(true);
    TestBed.createComponent(Diagram);
    TestBed.tick();

    TestBed.inject(P2PService).removed.set(true);
    TestBed.tick();

    expect(alertSpy).toHaveBeenCalledOnceWith('El host te expulsó de la sala.');
  });
});

