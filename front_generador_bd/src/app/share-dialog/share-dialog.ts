import { DOCUMENT } from '@angular/common';
import { Component, HostListener, computed, inject, input, output, signal } from '@angular/core';
import { copyText } from './copy-text';

export type ShareItem = 'invite' | 'code' | 'follow';

/** Cuánto tiempo se ve «¡Copiado!» en el botón que se acaba de usar. */
const COPIED_MS = 2000;

/**
 * Ventana «Compartir» de la sala, como la de draw.io: un lugar único donde se sacan el enlace para invitar a editar, el código
 * de la sala y el enlace para seguirla desde el celular (solo lectura). Todo se arma con el origen del sitio y el código de la sala.
 */
@Component({
  selector: 'app-share-dialog',
  standalone: true,
  templateUrl: './share-dialog.html'
})
export class ShareDialog {
  private readonly document = inject(DOCUMENT);

  readonly roomId = input.required<string>();
  readonly closed = output<void>();

  /** Qué botón acaba de copiar algo (para mostrar «¡Copiado!» un momento). */
  readonly copied = signal<ShareItem | null>(null);
  private copiedTimer?: ReturnType<typeof setTimeout>;

  private readonly origin = this.document.location?.origin ?? '';

  /** Entrar directo a la sala: la persona solo escribe su nombre. */
  readonly inviteLink = computed(() => `${this.origin}/diagram/${encodeURIComponent(this.roomId())}`);
  /** Vista del celular: solo lectura y con avisos. */
  readonly followLink = computed(() => `${this.origin}/sala/${encodeURIComponent(this.roomId())}/seguir`);

  async copy(item: ShareItem): Promise<void> {
    const text = item === 'invite' ? this.inviteLink() : item === 'follow' ? this.followLink() : this.roomId();
    if (!(await copyText(text))) return;
    this.copied.set(item);
    clearTimeout(this.copiedTimer);
    this.copiedTimer = setTimeout(() => this.copied.set(null), COPIED_MS);
  }

  selectAll(event: Event): void {
    (event.target as HTMLInputElement).select();
  }

  @HostListener('document:keydown.escape')
  close(): void {
    clearTimeout(this.copiedTimer);
    this.closed.emit();
  }
}
