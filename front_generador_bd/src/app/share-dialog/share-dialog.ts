import { DOCUMENT, NgTemplateOutlet } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Component, HostListener, OnInit, computed, inject, input, output, signal } from '@angular/core';
import { AuthService } from '../../services/auth/auth.service';
import { AssignableRole, LinkAccess, RoomAccess, RoomAccessService, RoomMember, RoomRole } from '../../services/auth/room-access.service';
import { InviteService, parseEmails } from '../../services/colaboration/invite.service';
import { copyText } from './copy-text';

export type ShareItem = 'invite' | 'code' | 'follow';

/** Cuánto tiempo se ve «¡Copiado!» en el botón que se acaba de usar. */
const COPIED_MS = 2000;

/** Cómo se llama cada rol en pantalla. */
export function roleLabel(role: RoomRole | string): string {
  return role === 'owner' ? 'Propietario' : role === 'editor' ? 'Editor' : 'Lector';
}

/**
 * Ventana «Compartir» de la sala. Con el servidor sin cuentas, como la de draw.io: el enlace de invitación, el código y el enlace para seguirla
 * desde el celular. Con «entrar con el correo», como Google Docs: agregar personas por correo con su rol (editor o lector), ver y cambiar quién
 * tiene acceso y el acceso general (restringido, o cualquiera con el enlace como lector o como editor, que es cuando el enlace se puede copiar).
 */
@Component({
  selector: 'app-share-dialog',
  standalone: true,
  imports: [NgTemplateOutlet],
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

  /** Con el modo «entrar con el correo» se comparte con roles y acceso general; sin él, con el enlace y el código de siempre. */
  readonly withAccounts = computed(() => this.auth.config()?.authRequired === true);
  readonly roomInfo = signal<RoomAccess | null>(null);
  readonly members = computed<RoomMember[]>(() => this.roomInfo()?.members ?? []);
  readonly isOwner = computed(() => this.roomInfo()?.is_owner === true);
  /** Quien solo puede leer no invita a nadie. */
  readonly canInvite = computed(() => this.roomInfo()?.can_edit !== false);
  readonly linkAccess = computed<LinkAccess>(() => this.roomInfo()?.link_access ?? 'restricted');
  readonly linkRole = computed<AssignableRole>(() => this.roomInfo()?.link_role ?? 'viewer');
  readonly title = computed(() => this.roomInfo()?.title ?? '');
  /** Con qué rol entran las personas que se invitan ahora. */
  readonly inviteRole = signal<AssignableRole>('editor');
  readonly changing = signal(false);
  readonly settingsError = signal('');
  readonly roleLabel = roleLabel;

  ngOnInit(): void {
    // Se pregunta una vez qué puede hacer el servidor (mandar correos, pedir sesión) para mostrar lo que corresponde.
    this.auth.ensureConfig().subscribe(config => {
      if (config.authRequired) this.access.info(this.roomId()).subscribe({ next: info => this.roomInfo.set(info), error: () => undefined });
    });
  }

  onInviteRole(event: Event): void {
    this.inviteRole.set((event.target as HTMLSelectElement).value === 'viewer' ? 'viewer' : 'editor');
  }

  /** Acceso general: restringido o cualquiera con el enlace (solo el propietario lo cambia). */
  onLinkAccess(event: Event): void {
    const value = (event.target as HTMLSelectElement).value === 'anyone' ? 'anyone' : 'restricted';
    this.change(this.access.updateSettings(this.roomId(), { link_access: value }));
  }

  /** Con qué rol entra quien llega por el enlace. */
  onLinkRole(event: Event): void {
    const value = (event.target as HTMLSelectElement).value === 'editor' ? 'editor' : 'viewer';
    this.change(this.access.updateSettings(this.roomId(), { link_role: value }));
  }

  onMemberRole(email: string, event: Event): void {
    const value = (event.target as HTMLSelectElement).value === 'viewer' ? 'viewer' : 'editor';
    this.change(this.access.setMemberRole(this.roomId(), email, value));
  }

  removeMember(email: string): void {
    this.change(this.access.removeMember(this.roomId(), email) as Observable<RoomAccess>);
  }

  /** Aplica un cambio de permisos: al volver, la lista y el acceso se muestran como quedaron; si falla, se dice por qué. */
  private change(request: Observable<RoomAccess>): void {
    if (this.changing()) return;
    this.changing.set(true);
    this.settingsError.set('');
    request.subscribe({
      next: info => {
        this.changing.set(false);
        if (info && Array.isArray(info.members)) this.roomInfo.set(info);
      },
      error: (failure: unknown) => {
        this.changing.set(false);
        const reason = failure instanceof HttpErrorResponse ? failure.error?.error : undefined;
        this.settingsError.set(typeof reason === 'string' ? reason : 'No pudimos guardar el cambio. Intenta de nuevo.');
      }
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
    this.invites.send(this.roomId(), valid, this.message().trim(), this.inviteRole()).subscribe({
      next: ({ sent, failed, members }) => {
        this.sending.set(false);
        if (members && members.length > 0) this.roomInfo.update(info => (info ? { ...info, members } : info));
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
