import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { PLATFORM_ID, provideZonelessChangeDetection, signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { environment } from '../../environments/environment';
import { ActivityEvent } from '../../services/colaboration/activity-event';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { P2PService } from '../../services/colaboration/p2p.service';
import { IaActionsService } from '../../services/IA/ia-actions.service';
import { ActivityPanel } from './activity-panel';

describe('ActivityPanel', () => {
  let fixture: ComponentFixture<ActivityPanel>;
  let http: HttpTestingController;
  let liveActivityEvents: ReturnType<typeof signal<ActivityEvent[]>>;
  let appliedSuggestions: ReturnType<typeof signal<ReadonlySet<string>>>;
  let applySuggestion: jasmine.Spy;
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
    appliedSuggestions = signal<ReadonlySet<string>>(new Set());
    applySuggestion = jasmine.createSpy('applySuggestion').and.returnValue(of('Listo'));
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
        { provide: P2PService, useValue: { liveActivityEvents } },
        { provide: CollaborationService, useValue: { appliedSuggestions } },
        { provide: IaActionsService, useValue: { applySuggestion } }
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
    const panel = fixture.componentInstance;
    const now = Date.parse('2026-10-21T12:02:30Z');

    expect(panel.relativeTime('2026-10-21T12:02:00Z', now)).toBe('ahora');
    expect(panel.relativeTime('2026-10-21T12:00:00Z', now)).toBe('hace 2 min');
    expect(panel.relativeTime('2026-10-21T09:00:00Z', now)).toBe('hace 3 h');
    expect(panel.relativeTime('2026-10-20T12:00:00Z', now)).toBe('hace 1 día');
    expect(panel.relativeTime('no es una fecha', now)).toBe('');
  });

  describe('follow view (read only)', () => {
    it('shows the ideas but offers no way to apply them', () => {
      fixture.componentRef.setInput('readOnly', true);
      http.expectOne(historyUrl).flush({
        events: [event(9, '2026-10-21T12:00:00Z', {
          actor_name: 'IA',
          actor_kind: 'ia',
          type: 'ia_review',
          summary: 'revisó el diagrama a pedido de Ana: 1 observación',
          data: { findings: [{ text: 'Falta una clave', prompt: 'agrega id' }] }
        })]
      });
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelectorAll('[data-testid="ia-suggestion"]').length).toBe(1);
      expect(fixture.nativeElement.querySelector('[data-testid="apply-suggestion"]')).toBeNull();

      fixture.componentInstance.apply(
        event(9, '2026-10-21T12:00:00Z'),
        0,
        { prompt: 'agrega id' }
      );
      expect(applySuggestion).not.toHaveBeenCalled();
    });

    it('can use the full width of a phone instead of the fixed editor width', () => {
      http.expectOne(historyUrl).flush({ events: [] });
      const section = fixture.nativeElement.querySelector('[data-testid="activity-panel"]') as HTMLElement;
      expect(section.classList).toContain('w-72');

      fixture.componentRef.setInput('fluid', true);
      fixture.detectChanges();

      expect(section.classList).toContain('w-full');
      expect(section.classList).not.toContain('w-72');
    });
  });

  describe('IA events', () => {
    function reviewEvent(overrides: Partial<ActivityEvent> = {}): ActivityEvent {
      return event(9, '2026-10-21T12:00:00Z', {
        actor_name: 'IA',
        actor_kind: 'ia',
        type: 'ia_review',
        summary: 'revisó el diagrama a pedido de Ana: 2 observaciones',
        data: {
          findings: [
            { text: 'Cliente no tiene clave <b>primaria</b>', prompt: 'agrega id: int a Cliente' },
            { text: 'Pedido está aislado', prompt: '' }
          ]
        },
        ...overrides
      });
    }

    function load(events: ActivityEvent[]): void {
      http.expectOne(historyUrl).flush({ events });
      fixture.detectChanges();
    }

    function buttons(): HTMLButtonElement[] {
      return Array.from(fixture.nativeElement.querySelectorAll('[data-testid="apply-suggestion"]'));
    }

    it('marks IA events as such and shows who asked for them', () => {
      load([reviewEvent()]);

      const entry = fixture.nativeElement.querySelector('[data-testid="activity-entry"]');
      expect(entry.textContent).toContain('🤖 IA');
      expect(entry.textContent).toContain('a pedido de Ana');
    });

    it('lists the review findings as plain text and only offers Apply when there is something to apply', () => {
      load([reviewEvent()]);

      const suggestions = fixture.nativeElement.querySelectorAll('[data-testid="ia-suggestion"]');
      expect(suggestions.length).toBe(2);
      expect(suggestions[0].textContent).toContain('<b>primaria</b>');
      expect(suggestions[0].querySelector('b')).toBeNull();
      expect(buttons().length).toBe(1);
    });

    it('applies a suggestion through the IA on behalf of whoever clicks it', () => {
      load([reviewEvent()]);

      buttons()[0].click();

      expect(applySuggestion).toHaveBeenCalledOnceWith('room one', 9, 0, 'agrega id: int a Cliente');
    });

    it('shows an idea as applied, for everyone, once someone applied it', () => {
      load([reviewEvent()]);

      appliedSuggestions.set(new Set(['9:0']));
      fixture.detectChanges();

      expect(buttons()[0].textContent).toContain('Aplicada');
      expect(buttons()[0].disabled).toBeTrue();
      buttons()[0].click();
      expect(applySuggestion).not.toHaveBeenCalled();
    });

    it('tells the user when the IA could not apply an idea and lets them retry', () => {
      applySuggestion.and.returnValue(throwError(() => new Error('502')));
      load([reviewEvent()]);

      buttons()[0].click();
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('[data-testid="suggestion-error"]').textContent)
        .toContain('no pudo aplicar');
      expect(buttons()[0].disabled).toBeFalse();
    });

    it('ignores malformed findings instead of failing', () => {
      load([reviewEvent({ data: { findings: [null, 5, { nope: true }, { text: 'Válida', prompt: 7 }] } })]);

      const suggestions = fixture.nativeElement.querySelectorAll('[data-testid="ia-suggestion"]');
      expect(suggestions.length).toBe(1);
      expect(buttons().length).toBe(0);
    });
  });
});