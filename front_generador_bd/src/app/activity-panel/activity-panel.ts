import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, OnInit, PLATFORM_ID, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { environment } from '../../environments/environment';
import { ActivityEvent } from '../../services/colaboration/activity-event';
import { P2PService } from '../../services/colaboration/p2p.service';

type ActivityHistoryResponse = ActivityEvent[] | { events: ActivityEvent[] };

@Component({
  selector: 'app-activity-panel',
  standalone: true,
  templateUrl: './activity-panel.html'
})
export class ActivityPanel implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly p2p = inject(P2PService);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly history = signal<ActivityEvent[]>([]);

  readonly events = computed(() => this.mergeEvents(
    this.history(),
    this.p2p.liveActivityEvents()
  ));

  ngOnInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    const roomId = this.route.snapshot.paramMap.get('roomId');
    if (!roomId) return;

    const url = `${environment.endpoint_python}api/rooms/${encodeURIComponent(roomId)}/activity/?limit=100`;
    this.http.get<ActivityHistoryResponse>(url).subscribe({
      next: response => {
        const events = Array.isArray(response) ? response : response.events;
        this.history.set(Array.isArray(events) ? events : []);
      },
      error: () => this.history.set([])
    });
  }

  relativeTime(createdAt: string): string {
    const timestamp = Date.parse(createdAt);
    if (!Number.isFinite(timestamp)) return '';

    const elapsedSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
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
