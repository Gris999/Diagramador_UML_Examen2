import { DOCUMENT } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, HostListener, OnInit, computed, inject, input, output, signal } from '@angular/core';
import { AuthService } from '../../services/auth/auth.service';
import { RoomAccessService, RoomMember } from '../../services/auth/room-access.service';
import { InviteService, parseEmails } from '../../services/colaboration/invite.service';
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
export class ShareDialog implements OnInit {
  private readonly document = inject(DOCUMENT);
  private readonly invites = inject(InviteService);
  private readonly auth = inject(AuthService);
  private readonly access = inject(RoomAccessService);

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

  /** Lo que se escribe en «Invitar por correo». */
  readonly emailsText = signal('');
  readonly message = signal('');
  readonly sending = signal(false);
  readonly result = signal<{ kind: 'ok' | 'error'; text: string } | null>(null);
  /** El servidor no puede mandar correos: se ofrece abrir el correo de la propia persona con el mensaje escrito. */
  private readonly mailFallback = signal(false);

  readonly parsed = computed(() => parseEmails(this.emailsText()));
  readonly serverMail = computed(() => this.auth.config()?.mailConfigured !== false && !this.mailFallback());
  readonly mailtoHref = computed(() => {
    const note = this.message().trim();
    const body = ['Hola,', '', 'Te invito a trabajar en equipo en un diagrama de clases UML.', ...(note ? ['', note] : []), '', `Entra aquí: ${this.inviteLink()}`].join('\n');
    return `mailto:${this.parsed().valid.join(',')}?subject=${encodeURIComponent('Te invito a un diagrama UML')}&body=${encodeURIComponent(body)}`;
  });

  /** Con el modo «entrar con el correo» a la sala solo se entra por invitación: no se ofrece copiar el enlace ni el código, y se lista quién tiene acceso. */
  readonly restricted = computed(() => this.auth.config()?.authRequired === true);
  readonly members = signal<RoomMember[]>([]);

  ngOnInit(): void {
    // Se pregunta una vez qué puede hacer el servidor (mandar correos, pedir sesión) para mostrar lo que corresponde.
    this.auth.ensureConfig().subscribe(config => {
      if (config.authRequired) this.access.members(this.roomId()).subscribe({ next: access => this.members.set(access.members ?? []), error: () => undefined });
    });
  }

  onEmails(event: Event): void {
    this.emailsText.set((event.target as HTMLInputElement).value);
    this.result.set(null);
  }

  onMessage(event: Event): void {
    this.message.set((event.target as HTMLTextAreaElement).value);
  }

  sendInvites(): void {
    const { valid, invalid } = this.parsed();
    if (this.sending()) return;
    if (invalid.length > 0) {
      this.result.set({ kind: 'error', text: `Revisa este correo: «${invalid[0]}» no parece válido.` });
      return;
    }
    if (valid.length === 0) return;

    this.sending.set(true);
    this.result.set(null);
    this.invites.send(this.roomId(), valid, this.message().trim()).subscribe({
      next: ({ sent, failed, members }) => {
        this.sending.set(false);
        if (members && members.length > 0) this.members.set(members);
        if (failed.length === 0) this.emailsText.set('');
        this.result.set({
          kind: failed.length === 0 ? 'ok' : 'error',
          text: failed.length === 0
            ? `Invitación enviada a ${sent.join(', ')}.`
            : `Enviada a ${sent.join(', ') || 'nadie'}. No se pudo enviar a: ${failed.join(', ')}.`
        });
      },
      error: (failure: unknown) => {
        this.sending.set(false);
        if (failure instanceof HttpErrorResponse && failure.status === 503) {
          this.mailFallback.set(true);
          this.result.set({ kind: 'error', text: 'Este servidor todavía no puede mandar correos. Usa «Abrir mi correo».' });
          return;
        }
        const reason = failure instanceof HttpErrorResponse ? failure.error?.error : undefined;
        this.result.set({ kind: 'error', text: typeof reason === 'string' ? reason : 'No pudimos mandar las invitaciones. Intenta de nuevo.' });
      }
    });
  }

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
