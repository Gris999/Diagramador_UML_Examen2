import { Component, input, PLATFORM_ID, provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { ActivityEvent } from '../../services/colaboration/activity-event';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { NotificationPermissionState, NotificationService } from '../../services/colaboration/notification.service';
import { P2PService } from '../../services/colaboration/p2p.service';
import { DiagramService } from '../../services/diagram/diagram.service';
import { ActivityPanel } from '../activity-panel/activity-panel';
import { FollowView, isIosDevice } from './follow-view';

@Component({ selector: 'app-activity-panel', standalone: true, template: '<p data-testid="activity-stub"></p>' })
class ActivityPanelStub {
  readOnly = input(false);
  embedded = input(false);
}

describe('FollowView', () => {
  let fixture: ComponentFixture<FollowView>;
  let diagram: {
    initialize: jasmine.Spy;
    watchGraph: jasmine.Spy;
    hasDiagramElements: jasmine.Spy;
    fitToViewport: jasmine.Spy;
    leaveRoom: jasmine.Spy;
  };
  let iaStatus: ReturnType<typeof signal<{ state: 'thinking' | 'idle'; by: string }>>;
  let navigate: jasmine.Spy;
  let reconnectViewerNow: jasmine.Spy;
  let liveActivityEvents: ReturnType<typeof signal<ActivityEvent[]>>;
  let permission: ReturnType<typeof signal<NotificationPermissionState>>;
  let notifications: {
    permission: typeof permission;
    requestPermission: jasmine.Spy;
    notifyChange: jasmine.Spy;
    notifyIdea: jasmine.Spy;
  };

  function activity(id: number, overrides: Partial<ActivityEvent> = {}): ActivityEvent {
    return {
      id,
      room: 'sala-1',
      actor: 1,
      actor_name: 'Ana',
      actor_kind: 'user',
      type: 'add_class',
      target_id: 'c1',
      summary: 'añadió una clase',
      data: {},
      created_at: '2026-10-26T12:00:00Z',
      ...overrides
    };
  }

  function configure(platform: 'browser' | 'server' = 'browser'): void {
    TestBed.configureTestingModule({
      imports: [FollowView],
      providers: [
        provideZonelessChangeDetection(),
        { provide: PLATFORM_ID, useValue: platform },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'sala-1' } } } },
        { provide: Router, useValue: { navigate } },
        { provide: DiagramService, useValue: diagram },
        { provide: CollaborationService, useValue: { iaStatus } },
        { provide: P2PService, useValue: { liveActivityEvents, reconnectViewerNow } },
        { provide: NotificationService, useValue: notifications }
      ]
    });
    TestBed.overrideComponent(FollowView, {
      remove: { imports: [ActivityPanel] },
      add: { imports: [ActivityPanelStub] }
    });
    fixture = TestBed.createComponent(FollowView);
  }

  async function start(): Promise<void> {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  function element(testId: string): HTMLElement | null {
    return (fixture.nativeElement as HTMLElement).querySelector(`[data-testid="${testId}"]`);
  }

  beforeEach(() => {
    jasmine.clock().install();
    iaStatus = signal<{ state: 'thinking' | 'idle'; by: string }>({ state: 'idle', by: '' });
    navigate = jasmine.createSpy('navigate');
    reconnectViewerNow = jasmine.createSpy('reconnectViewerNow');
    liveActivityEvents = signal<ActivityEvent[]>([]);
    permission = signal<NotificationPermissionState>('default');
    notifications = {
      permission,
      requestPermission: jasmine.createSpy('requestPermission').and.callFake(async () => {
        permission.set('granted');
        return 'granted';
      }),
      notifyChange: jasmine.createSpy('notifyChange'),
      notifyIdea: jasmine.createSpy('notifyIdea')
    };
    diagram = {
      initialize: jasmine.createSpy('initialize').and.resolveTo(),
      watchGraph: jasmine.createSpy('watchGraph'),
      hasDiagramElements: jasmine.createSpy('hasDiagramElements').and.returnValue(false),
      fitToViewport: jasmine.createSpy('fitToViewport'),
      leaveRoom: jasmine.createSpy('leaveRoom')
    };
  });

  afterEach(() => {
    jasmine.clock().uninstall();
  });

  it('opens the room as a read-only viewer', async () => {
    configure();

    await start();

    expect(diagram.initialize).toHaveBeenCalledOnceWith(jasmine.any(HTMLElement), 'sala-1', { readOnly: true });
    expect(element('follow-room')!.textContent).toContain('Solo lectura');
    expect(element('follow-room')!.textContent).toContain('sala-1');
  });

  it('offers no editing controls and keeps the canvas from receiving touches', async () => {
    configure();

    await start();

    // Lo único que se puede tocar es el botón de avisos: nada que edite el diagrama.
    expect(fixture.nativeElement.querySelectorAll('input, textarea').length).toBe(0);
    const buttons = Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLElement[];
    expect(buttons.map(button => button.dataset['testid'])).toEqual(['follow-notifications']);
    const canvas = element('follow-canvas')!;
    expect(canvas.querySelector('.pointer-events-none')).not.toBeNull();
  });

  it('shows the activity in read-only mode using the full width', async () => {
    configure();

    await start();

    expect(element('activity-stub')).not.toBeNull();
  });

  it('waits for the diagram, then hides the waiting message once there is content', async () => {
    configure();
    await start();
    expect(element('follow-empty')).not.toBeNull();

    diagram.hasDiagramElements.and.returnValue(true);
    diagram.watchGraph.calls.mostRecent().args[0]();
    fixture.detectChanges();

    expect(element('follow-empty')).toBeNull();
  });

  it('refits the diagram, with a short delay, when it changes or the screen is resized', async () => {
    configure();
    await start();
    diagram.fitToViewport.calls.reset();

    const onChange = diagram.watchGraph.calls.mostRecent().args[0];
    onChange();
    onChange();
    onChange();
    jasmine.clock().tick(200);
    expect(diagram.fitToViewport).toHaveBeenCalledTimes(1);

    window.dispatchEvent(new Event('resize'));
    jasmine.clock().tick(200);
    expect(diagram.fitToViewport).toHaveBeenCalledTimes(2);
  });

  it('shows who the IA is working for', async () => {
    configure();
    await start();
    expect(element('follow-ia-status')!.textContent).toContain('IA disponible');

    iaStatus.set({ state: 'thinking', by: 'Ana' });
    fixture.detectChanges();

    expect(element('follow-ia-status')!.textContent).toContain('Pensando (a pedido de Ana)');
  });

  it('tells the user when the room could not be opened', async () => {
    diagram.initialize.and.rejectWith(new Error('sin red'));
    configure();

    await start();

    expect(fixture.nativeElement.querySelector('[role="alert"]')!.textContent).toContain('No se pudo abrir la sala');
    expect(diagram.watchGraph).not.toHaveBeenCalled();
  });

  it('leaves the room and stops listening to the screen size when it is closed', async () => {
    configure();
    await start();
    diagram.fitToViewport.calls.reset();

    fixture.destroy();
    window.dispatchEvent(new Event('resize'));
    jasmine.clock().tick(500);

    expect(diagram.leaveRoom).toHaveBeenCalledOnceWith('sala-1');
    expect(diagram.fitToViewport).not.toHaveBeenCalled();
  });

  describe('notifications', () => {
    it('offers to turn the notifications on, and asks for the permission only when it is tapped', async () => {
      configure();
      await start();

      expect(notifications.requestPermission).not.toHaveBeenCalled();
      expect(element('follow-notifications')!.textContent).toContain('Activar avisos');

      element('follow-notifications')!.click();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(notifications.requestPermission).toHaveBeenCalledTimes(1);
      expect(element('follow-notifications')).toBeNull();
      expect(element('follow-notifications-on')!.textContent).toContain('Avisos activados');
    });

    it('says the notifications are blocked when the browser refuses them', async () => {
      permission.set('denied');
      configure();

      await start();

      expect(element('follow-notifications')).toBeNull();
      expect(element('follow-notifications-blocked')!.textContent).toContain('bloqueados');
    });

    it('shows nothing about notifications where the browser cannot show them', async () => {
      permission.set('unsupported');
      configure();

      await start();

      expect(element('follow-notifications')).toBeNull();
      expect(element('follow-notifications-on')).toBeNull();
      expect(element('follow-notifications-blocked')).toBeNull();
      expect(element('follow-ios-hint')).toBeNull();
    });

    it('tells an iPhone user in Safari to add the page to the home screen, since notifications only exist there', async () => {
      spyOnProperty(navigator, 'userAgent', 'get').and.returnValue(
        'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
      );
      permission.set('unsupported');
      configure();

      await start();

      expect(element('follow-ios-hint')!.textContent).toContain('Agregar a Inicio');
      expect(element('follow-notifications')).toBeNull();
    });

    it('does not show the iPhone hint once the notifications are available in the home screen app', async () => {
      spyOnProperty(navigator, 'userAgent', 'get').and.returnValue('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)');
      permission.set('default');
      configure();

      await start();

      expect(element('follow-ios-hint')).toBeNull();
      expect(element('follow-notifications')).not.toBeNull();
    });

    describe('isIosDevice', () => {
      it('recognizes iPhone and iPad, including an iPad that presents itself as a Mac', () => {
        expect(isIosDevice('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)', 5)).toBeTrue();
        expect(isIosDevice('Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X)', 5)).toBeTrue();
        expect(isIosDevice('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 5)).toBeTrue();
      });

      it('does not take Android, Windows or a real Mac for an iPhone', () => {
        expect(isIosDevice('Mozilla/5.0 (Linux; Android 14; Pixel 8) Chrome/120 Mobile', 5)).toBeFalse();
        expect(isIosDevice('Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120', 0)).toBeFalse();
        expect(isIosDevice('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 0)).toBeFalse();
      });
    });

    it('notifies a new change from another person once the permission is granted', async () => {
      permission.set('granted');
      configure();
      await start();

      liveActivityEvents.set([activity(7, { actor_name: 'Beto', summary: 'eliminó un elemento' })]);
      fixture.detectChanges();
      await fixture.whenStable();

      expect(notifications.notifyChange).toHaveBeenCalledOnceWith('Beto', 'eliminó un elemento');
    });

    it('does not notify anything without the permission', async () => {
      configure();
      await start();

      liveActivityEvents.set([activity(7)]);
      fixture.detectChanges();
      await fixture.whenStable();

      expect(notifications.notifyChange).not.toHaveBeenCalled();
      expect(notifications.notifyIdea).not.toHaveBeenCalled();
    });

    it('does not notify what had already happened when the notifications were turned on', async () => {
      liveActivityEvents.set([activity(3), activity(2)]);
      configure();
      await start();

      element('follow-notifications')!.click();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(notifications.notifyChange).not.toHaveBeenCalled();
    });

    it('does not repeat a notification when the list changes but the event is the same', async () => {
      permission.set('granted');
      configure();
      await start();

      liveActivityEvents.set([activity(7)]);
      fixture.detectChanges();
      await fixture.whenStable();
      liveActivityEvents.set([activity(8, { summary: 'editó una clase' }), activity(7)]);
      fixture.detectChanges();
      await fixture.whenStable();

      expect(notifications.notifyChange).toHaveBeenCalledTimes(2);
      expect(notifications.notifyChange.calls.argsFor(0)).toEqual(['Ana', 'añadió una clase']);
      expect(notifications.notifyChange.calls.argsFor(1)).toEqual(['Ana', 'editó una clase']);
    });

    it('notifies several events that arrive together from the oldest to the newest', async () => {
      permission.set('granted');
      configure();
      await start();

      liveActivityEvents.set([activity(9, { summary: 'tercero' }), activity(8, { summary: 'segundo' }), activity(7, { summary: 'primero' })]);
      fixture.detectChanges();
      await fixture.whenStable();

      expect(notifications.notifyChange.calls.allArgs().map(args => args[1])).toEqual(['primero', 'segundo', 'tercero']);
    });

    it('announces an AI review as an idea with how many ideas it has', async () => {
      permission.set('granted');
      configure();
      await start();

      liveActivityEvents.set([
        activity(7, {
          actor_name: 'IA',
          actor_kind: 'ia',
          type: 'ia_review',
          summary: 'revisó el diagrama a pedido de Ana: 3 observaciones',
          data: { findings: [{ text: 'Falta una clave primaria', prompt: 'agrega id' }, { text: 'b', prompt: 'b' }, { text: 'c', prompt: 'c' }] }
        })
      ]);
      fixture.detectChanges();
      await fixture.whenStable();

      expect(notifications.notifyIdea).toHaveBeenCalledOnceWith('La IA publicó una revisión con 3 ideas: Falta una clave primaria');
      expect(notifications.notifyChange).not.toHaveBeenCalled();
    });

    it('announces a review without ideas as a plain change of the AI', async () => {
      permission.set('granted');
      configure();
      await start();

      liveActivityEvents.set([
        activity(7, { actor_name: 'IA', actor_kind: 'ia', type: 'ia_review', summary: 'revisó el diagrama: sin observaciones', data: { findings: [] } })
      ]);
      fixture.detectChanges();
      await fixture.whenStable();

      expect(notifications.notifyChange).toHaveBeenCalledOnceWith('IA', 'revisó el diagrama: sin observaciones');
      expect(notifications.notifyIdea).not.toHaveBeenCalled();
    });
  });

  it('does nothing on the server (SSR)', async () => {
    configure('server');

    await start();

    expect(diagram.initialize).not.toHaveBeenCalled();
  });

  describe('coming back to the app after the phone was locked', () => {
    it('reopens the live connection when the person was away only a moment', async () => {
      configure();
      await start();
      const reload = spyOn(fixture.componentInstance, 'reloadPage');

      fixture.componentInstance.handleVisibility(false);
      jasmine.clock().mockDate(new Date(Date.now() + 5000));
      fixture.componentInstance.handleVisibility(true);

      expect(reconnectViewerNow).toHaveBeenCalledTimes(1);
      expect(reload).not.toHaveBeenCalled();
    });

    it('reloads the screen when the person was away a while: the connection and the data are old', async () => {
      configure();
      await start();
      const reload = spyOn(fixture.componentInstance, 'reloadPage');

      fixture.componentInstance.handleVisibility(false);
      jasmine.clock().mockDate(new Date(Date.now() + 30000));
      fixture.componentInstance.handleVisibility(true);

      expect(reload).toHaveBeenCalledTimes(1);
      expect(reconnectViewerNow).not.toHaveBeenCalled();
    });

    it('reopens the connection when it becomes visible without having been hidden first', async () => {
      configure();
      await start();
      const reload = spyOn(fixture.componentInstance, 'reloadPage');

      fixture.componentInstance.handleVisibility(true);

      expect(reconnectViewerNow).toHaveBeenCalledTimes(1);
      expect(reload).not.toHaveBeenCalled();
    });
  });
});

