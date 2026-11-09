import { Component, ElementRef, Injector, OnInit, afterNextRender, computed, inject, input, signal, viewChild } from '@angular/core';
import { AuthService } from '../../services/auth/auth.service';
import { RoomAccess, RoomAccessService } from '../../services/auth/room-access.service';
import { roleLabel } from '../share-dialog/share-dialog';

/**
 * El nombre del diagrama en la barra de arriba del editor, con el rol de la persona. El propietario lo cambia con un clic; los demás solo lo ven.
 * Solo aparece cuando el servidor trabaja con cuentas (sin ellas los diagramas no tienen nombre).
 */
@Component({
  selector: 'app-room-title',
  standalone: true,
  templateUrl: './room-title.html'
})
export class RoomTitle implements OnInit {
  private readonly access = inject(RoomAccessService);
  private readonly auth = inject(AuthService);
  private readonly injector = inject(Injector);

  readonly roomId = input.required<string>();
  private readonly field = viewChild<ElementRef<HTMLInputElement>>('titleInput');

  readonly info = signal<RoomAccess | null>(null);
  readonly editing = signal(false);
  readonly draft = signal('');
  readonly saving = signal(false);
  readonly error = signal('');

  readonly visible = computed(() => this.auth.config()?.authRequired === true && this.info() !== null);
  readonly isOwner = computed(() => this.info()?.is_owner === true);
  readonly title = computed(() => this.info()?.title ?? '');
  readonly roleText = computed(() => roleLabel(this.info()?.role ?? 'viewer'));

  ngOnInit(): void {
    this.auth.ensureConfig().subscribe(config => {
      if (!config.authRequired) return;
      // Al abrir la sala la guardia ya trajo cómo está; si no (recarga directa), se pregunta.
      const known = this.access.lastAccess(this.roomId());
      if (known) this.info.set(known);
      else this.access.info(this.roomId()).subscribe({ next: info => this.info.set(info), error: () => undefined });
    });
  }

  startEdit(): void {
    if (!this.isOwner()) return;
    this.draft.set(this.title());
    this.error.set('');
    this.editing.set(true);
    // El campo recién aparece: se le da el cursor y se selecciona el nombre para escribir encima (`autofocus` no sirve en un campo que se agrega después).
    afterNextRender(() => {
      const input = this.field()?.nativeElement;
      input?.focus();
      input?.select();
    }, { injector: this.injector });
  }

  onInput(event: Event): void {
    this.draft.set((event.target as HTMLInputElement).value);
  }

  cancel(): void {
    this.editing.set(false);
    this.error.set('');
  }

  save(): void {
    if (!this.editing() || this.saving()) return;
    const title = this.draft().trim();
    if (title === this.title()) {
      this.editing.set(false);
      return;
    }
    this.saving.set(true);
    this.access.updateSettings(this.roomId(), { title }).subscribe({
      next: info => {
        this.info.set(info);
        this.saving.set(false);
        this.editing.set(false);
      },
      error: () => {
        this.error.set('No pudimos guardar el nombre.');
        this.saving.set(false);
      }
    });
  }
}
