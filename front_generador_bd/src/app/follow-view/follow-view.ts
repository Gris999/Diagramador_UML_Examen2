import { isPlatformBrowser } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  inject,
  OnDestroy,
  PLATFORM_ID,
  signal,
  ViewChild
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { DiagramService } from '../../services/diagram/diagram.service';
import { ActivityPanel } from '../activity-panel/activity-panel';

const FIT_DEBOUNCE_MS = 150;

/**
 * Vista de seguimiento pensada para el celular: muestra el diagrama de la sala
 * actualizándose en vivo y debajo la actividad del equipo. No tiene ningún
 * control de edición y su conexión es de solo lectura (el servidor también lo
 * exige), así que no puede cambiar nada ni convertirse en host.
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

  @ViewChild('scroll', { static: true }) scroll!: ElementRef<HTMLElement>;
  @ViewChild('paperContainer', { static: true }) paperContainer!: ElementRef<HTMLElement>;

  readonly roomId = this.route.snapshot.paramMap.get('roomId') ?? '';
  readonly iaStatus = this.collab.iaStatus;
  readonly hasContent = signal(false);
  readonly failed = signal(false);

  private fitTimer?: ReturnType<typeof setTimeout>;
  private readonly onResize = () => this.scheduleFit();

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

  private scheduleFit(): void {
    clearTimeout(this.fitTimer);
    this.fitTimer = setTimeout(
      () => this.diagram.fitToViewport(this.scroll.nativeElement),
      FIT_DEBOUNCE_MS
    );
  }
}
