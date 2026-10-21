import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, input, OnDestroy, OnInit, PLATFORM_ID, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { environment } from '../../environments/environment';
import { ActivityEvent } from '../../services/colaboration/activity-event';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { P2PService } from '../../services/colaboration/p2p.service';
import { IaActionsService } from '../../services/IA/ia-actions.service';

type ActivityHistoryResponse = ActivityEvent[] | { events: ActivityEvent[] };

@Component({
  selector: 'app-activity-panel',
  standalone: true,
  templateUrl: './activity-panel.html'
})
export class ActivityPanel implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly p2p = inject(P2PService);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly actions = inject(IaActionsService);
  private readonly collab = inject(CollaborationService);
  private readonly history = signal<ActivityEvent[]>([]);

  private roomId: string | null = null;

  /** "Ahora" como señal: así el tiempo relativo cambia de forma controlada y no en pleno ciclo de detección. */
  private readonly now = signal(Date.now());
  private clock?: ReturnType<typeof setInterval>;

  /** Vista de seguimiento: se ven las ideas de la IA pero no se pueden aplicar. */
  readonly readOnly = input(false);
  /** Ocupa todo el ancho disponible (celular) en lugar del ancho fijo del editor. */
  readonly fluid = input(false);

  readonly applying = signal<string | null>(null);
  readonly suggestionError = signal('');

  readonly events = computed(() => this.mergeEvents(
    this.history(),
    this.p2p.liveActivityEvents()
  ));

  ngOnInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    this.clock = setInterval(() => this.now.set(Date.now()), 30_000);

    const roomId = this.route.snapshot.paramMap.get('roomId');
    if (!roomId) return;
    this.roomId = roomId;

    const url = `${environment.endpoint_python}api/rooms/${encodeURIComponent(roomId)}/activity/?limit=100`;
    this.http.get<ActivityHistoryResponse>(url).subscribe({
      next: response => {
        const events = Array.isArray(response) ? response : response.events;
        this.history.set(Array.isArray(events) ? events : []);
      },
      error: () => this.history.set([])
    });
  }

  /** Ideas que dejó la IA en una revisión (siempre se muestran como texto). */
  findingsOf(event: ActivityEvent): { text: string; prompt: string }[] {
    const findings = event.data?.['findings'];
    if (event.type !== 'ia_review' || !Array.isArray(findings)) return [];
    return findings
      .filter((item): item is { text: string; prompt?: string } =>
        !!item && typeof item.text === 'string')
      .map(item => ({ text: item.text, prompt: typeof item.prompt === 'string' ? item.prompt : '' }));
  }

  isApplied(event: ActivityEvent, index: number): boolean {
    return this.collab.appliedSuggestions().has(`${event.id}:${index}`);
  }

  isApplying(event: ActivityEvent, index: number): boolean {
    return this.applying() === `${event.id}:${index}`;
  }

  /** Cualquiera puede aplicar una idea: el cambio queda a nombre de quien la aplica. */
  apply(event: ActivityEvent, index: number, finding: { prompt: string }): void {
    if (this.readOnly() || !this.roomId || !finding.prompt || this.applying() || this.isApplied(event, index)) return;

    this.suggestionError.set('');
    this.applying.set(`${event.id}:${index}`);
    this.actions.applySuggestion(this.roomId, event.id, index, finding.prompt).subscribe({
      next: () => this.applying.set(null),
      error: () => {
        this.applying.set(null);
        this.suggestionError.set('La IA no pudo aplicar esa idea ahora. Intenta de nuevo.');
      }
    });
  }

  ngOnDestroy(): void {
    clearInterval(this.clock);
  }

  relativeTime(createdAt: string, now: number = this.now()): string {
    const timestamp = Date.parse(createdAt);
    if (!Number.isFinite(timestamp)) return '';

    const elapsedSeconds = Math.max(0, Math.floor((now - timestamp) / 1000));
    if (elapsedSeconds < 60) return 'ahora';

    const minutes = Math.floor(elapsedSeconds / 60);
    if (minutes < 60) return `hace ${minutes} min`;

    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `hace ${hours} h`;

    const days = Math.floor(hours / 24);
    return days === 1 ? 'hace 1 día' : `hace ${days} días`;
  }

  private mergeEvents(history: ActivityEvent[], live: ActivityEvent[]): ActivityEvent[] {
    const byId = new Map<number, ActivityEvent>();
    history.forEach(event => byId.set(event.id, event));
    live.forEach(event => byId.set(event.id, event));

    return [...byId.values()].sort(
      (left, right) => this.timestamp(right.created_at) - this.timestamp(left.created_at)
    );
  }

  private timestamp(value: string): number {
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
}
