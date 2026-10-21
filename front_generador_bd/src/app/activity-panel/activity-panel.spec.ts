import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { PLATFORM_ID, provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { environment } from '../../environments/environment';
import { ActivityEvent } from '../../services/colaboration/activity-event';
import { P2PService } from '../../services/colaboration/p2p.service';
import { ActivityPanel } from './activity-panel';

describe('ActivityPanel', () => {
  let fixture: ComponentFixture<ActivityPanel>;
  let http: HttpTestingController;
  let liveActivityEvents: ReturnType<typeof signal<ActivityEvent[]>>;
  const historyUrl = `${environment.endpoint_python}api/rooms/room%20one/activity/?limit=100`;

  function event(id: number, createdAt: string, overrides: Partial<ActivityEvent> = {}): ActivityEvent {
    return {
      id,
      room: 'room one',
      actor: null,
      actor_name: 'Ana',
      actor_kind: 'user',
      type: 'add_class',
      target_id: `class-${id}`,
      summary: `añadió la clase Clase${id}`,
      data: {},
      created_at: createdAt,
      ...overrides
    };
  }

  beforeEach(async () => {
    liveActivityEvents = signal<ActivityEvent[]>([]);
    await TestBed.configureTestingModule({
      imports: [ActivityPanel],
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PLATFORM_ID, useValue: 'browser' },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => 'room one' } } }
        },
        { provide: P2PService, useValue: { liveActivityEvents } }
      ]
    }).compileComponents();

    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(ActivityPanel);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('loads history and renders it newest first', () => {
    http.expectOne(historyUrl).flush({
      events: [
        event(1, '2026-10-21T10:00:00Z'),
        event(2, '2026-10-21T11:00:00Z', { actor_name: 'Beatriz' })
      ]
    });
    fixture.detectChanges();

    const entries = fixture.nativeElement.querySelectorAll('[data-testid="activity-entry"]');
    expect(entries.length).toBe(2);
    expect(entries[0].textContent).toContain('Beatriz');
    expect(entries[1].textContent).toContain('Ana');
  });

  it('merges live events with history and deduplicates by event id', () => {
    const historyRequest = http.expectOne(historyUrl);
    liveActivityEvents.set([
      event(2, '2026-10-21T12:00:00Z', { actor_name: 'Carla' }),
      event(1, '2026-10-21T11:00:00Z', { summary: 'editó el nombre de Cliente' })
    ]);
    historyRequest.flush({
      events: [event(1, '2026-10-21T10:00:00Z')]
    });
    fixture.detectChanges();

    const entries = fixture.nativeElement.querySelectorAll('[data-testid="activity-entry"]');
    expect(entries.length).toBe(2);
    expect(entries[0].textContent).toContain('Carla');
    expect(entries[1].textContent).toContain('editó el nombre de Cliente');
  });

  it('keeps the empty state when history is unavailable', () => {
    http.expectOne(historyUrl).flush('unavailable', {
      status: 503,
      statusText: 'Service Unavailable'
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Todavía no hay actividad.');
    expect(fixture.nativeElement.querySelector('[data-testid="activity-entry"]')).toBeNull();
  });

  it('formats recent timestamps as relative time', () => {
    http.expectOne(historyUrl).flush({ events: [] });
    jasmine.clock().install();
    try {
      jasmine.clock().mockDate(new Date('2026-10-21T12:02:30Z'));
      expect(fixture.componentInstance.relativeTime('2026-10-21T12:00:00Z')).toBe('hace 2 min');
    } finally {
      jasmine.clock().uninstall();
    }
  });
});
