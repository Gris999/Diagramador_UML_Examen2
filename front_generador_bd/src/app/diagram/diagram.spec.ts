import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { ActivityEvent } from '../../services/colaboration/activity-event';
import { P2PService } from '../../services/colaboration/p2p.service';
import { DiagramService } from '../../services/diagram/diagram.service';

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

