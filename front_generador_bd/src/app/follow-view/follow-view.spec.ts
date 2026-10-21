import { Component, input, PLATFORM_ID, provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { DiagramService } from '../../services/diagram/diagram.service';
import { ActivityPanel } from '../activity-panel/activity-panel';
import { FollowView } from './follow-view';

@Component({ selector: 'app-activity-panel', standalone: true, template: '<p data-testid="activity-stub"></p>' })
class ActivityPanelStub {
  readOnly = input(false);
  fluid = input(false);
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

  function configure(platform: 'browser' | 'server' = 'browser'): void {
    TestBed.configureTestingModule({
      imports: [FollowView],
      providers: [
        provideZonelessChangeDetection(),
        { provide: PLATFORM_ID, useValue: platform },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'sala-1' } } } },
        { provide: Router, useValue: { navigate } },
        { provide: DiagramService, useValue: diagram },
        { provide: CollaborationService, useValue: { iaStatus } }
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

    expect(fixture.nativeElement.querySelectorAll('button, input, textarea').length).toBe(0);
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

  it('does nothing on the server (SSR)', async () => {
    configure('server');

    await start();

    expect(diagram.initialize).not.toHaveBeenCalled();
  });
});
