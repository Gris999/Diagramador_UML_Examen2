import { isPlatformBrowser } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  effect,
  inject,
  OnDestroy,
  PLATFORM_ID,
  signal,
  untracked,
  ViewChild
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ActivityEvent } from '../../services/colaboration/activity-event';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { NotificationService } from '../../services/colaboration/notification.service';
import { P2PService } from '../../services/colaboration/p2p.service';
import { DiagramService } from '../../services/diagram/diagram.service';
import { ActivityPanel } from '../activity-panel/activity-panel';

const FIT_DEBOUNCE_MS = 150;

/**
 * Vista de seguimiento pensada para el celular: muestra el diagrama de la sala
 * actualizándose en vivo y debajo la actividad del equipo. No tiene ningún
 * control de edición y su conexión es de solo lectura (el servidor también lo
 * exige), así que no puede cambiar nada ni convertirse en host. Lo único que se puede tocar es el botón que activa los avisos del navegador:
 * con el permiso concedido y la página abierta, avisa de cada evento nuevo de la sala.
 */
@Component({
  selector: 'app-follow-view',
  standalone: true,
  imports: [ActivityPanel],
  templateUrl: './follow-view.html'
})
export class FollowView implements AfterViewInit, OnDestroy {
  private readonly diagram = inject(DiagramService);
  private readonly collab = inject(CollaborationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly p2p = inject(P2PService);
  private readonly notifications = inject(NotificationService);

  @ViewChild('scroll', { static: true }) scroll!: ElementRef<HTMLElement>;
  @ViewChild('paperContainer', { static: true }) paperContainer!: ElementRef<HTMLElement>;

  readonly roomId = this.route.snapshot.paramMap.get('roomId') ?? '';
  readonly iaStatus = this.collab.iaStatus;
  readonly hasContent = signal(false);
  readonly failed = signal(false);
  readonly notificationPermission = this.notifications.permission;

  /** Último evento del que ya se decidió si avisar: lo que ya había al abrir la vista o al activar los avisos no se avisa. */
  private lastSeenEventId = 0;

  private fitTimer?: ReturnType<typeof setTimeout>;
  private readonly onResize = () => this.scheduleFit();

  constructor() {
    this.lastSeenEventId = this.newestId(this.p2p.liveActivityEvents());
    effect(() => {
      const events = this.p2p.liveActivityEvents();
      untracked(() => {
        const fresh = events.filter(event => event.id > this.lastSeenEventId).sort((a, b) => a.id - b.id);
        for (const event of fresh) {
          this.lastSeenEventId = event.id;
          this.notifyNewActivity(event);
        }
      });
    });
  }

  async ngAfterViewInit(): Promise<void> {
    if (!isPlatformBrowser(this.platformId) || !this.roomId) return;

    try {
      await this.diagram.initialize(this.paperContainer.nativeElement, this.roomId, { readOnly: true });
    } catch {
      this.failed.set(true);
      return;
    }
    this.diagram.watchGraph(() => {
      this.hasContent.set(this.diagram.hasDiagramElements());
      this.scheduleFit();
    });
    window.addEventListener('resize', this.onResize);
    this.scheduleFit();
  }

  ngOnDestroy(): void {
    clearTimeout(this.fitTimer);
    if (isPlatformBrowser(this.platformId)) {
      window.removeEventListener('resize', this.onResize);
    }
    if (this.roomId) this.diagram.leaveRoom(this.roomId);
  }

  goHome(): void {
    this.router.navigate(['/']);
  }

  /** El navegador pide el permiso solo cuando la persona toca el botón, nunca al cargar la página. */
  async enableNotifications(): Promise<void> {
    await this.notifications.requestPermission();
  }

  /** Avisa de un evento nuevo de la sala: una revisión de la IA como idea, cualquier otro como cambio de su autor. */
  notifyNewActivity(event: ActivityEvent): void {
    if (this.notifications.permission() !== 'granted') return;

    const findings = event.type === 'ia_review' ? this.findingTexts(event) : [];
    if (findings.length > 0) {
      const count = findings.length === 1 ? '1 idea' : `${findings.length} ideas`;
      this.notifications.notifyIdea(`La IA publicó una revisión con ${count}: ${findings[0]}`);
      return;
    }
    this.notifications.notifyChange(event.actor_name || 'Alguien', event.summary);
  }

  private findingTexts(event: ActivityEvent): string[] {
    const findings = event.data?.['findings'];
    if (!Array.isArray(findings)) return [];
    return findings
      .map(item => (item && typeof item.text === 'string' ? item.text : ''))
      .filter(text => text.length > 0);
  }

  private newestId(events: ActivityEvent[]): number {
    return events.reduce((newest, event) => Math.max(newest, event.id), 0);
  }

  private scheduleFit(): void {
    clearTimeout(this.fitTimer);
    this.fitTimer = setTimeout(
      () => this.diagram.fitToViewport(this.scroll.nativeElement),
      FIT_DEBOUNCE_MS
    );
  }
}
