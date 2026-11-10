import { HttpErrorResponse } from '@angular/common/http';
import { isPlatformBrowser } from '@angular/common';
import { Component, computed, effect, ElementRef, inject, OnInit, PLATFORM_ID, signal, untracked, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CollaborationService } from '../../services/colaboration/collaboration.service';
import { IdentityService } from '../../services/colaboration/identity.service';
import { P2PService } from '../../services/colaboration/p2p.service';
import { IaActionsService } from '../../services/IA/ia-actions.service';
import { IA_NAME, IaChatMessage, IaChatService, IaProposal, IaProviderInfo, iaErrorMessage, isAddressedToIa } from '../../services/IA/ia-chat.service';

const MAX_MESSAGE_CHARS = 2000;

@Component({
  selector: 'app-ia-chat-panel',
  standalone: true,
  templateUrl: './ia-chat-panel.html'
})
export class IaChatPanel implements OnInit {
  private readonly chat = inject(IaChatService);
  private readonly actions = inject(IaActionsService);
  private readonly route = inject(ActivatedRoute);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly identity = inject(IdentityService);
  private readonly collab = inject(CollaborationService);
  private readonly p2p = inject(P2PService);

  @ViewChild('messageList') messageList?: ElementRef<HTMLElement>;

  readonly open = signal(false);
  readonly messages = signal<IaChatMessage[]>([]);
  readonly draft = signal('');
  readonly sending = signal(false);
  /** El historial ya se cargó (o falló): hasta entonces no se envía, para no duplicar mensajes. */
  readonly historyReady = signal(false);
  readonly error = signal('');
  readonly maxChars = MAX_MESSAGE_CHARS;
  /** Un cambio que la IA propuso y espera el permiso de esta persona (aparecen los botones Aplicar y Descartar). */
  readonly proposal = signal<IaProposal | null>(null);

  /** El modelo de IA de la sala y los que hay disponibles; `null` si no se pudo saber. */
  readonly providerInfo = signal<IaProviderInfo | null>(null);
  readonly providerLabel = computed(() => this.providerInfo()?.label ?? '');
  readonly switching = signal(false);

  /** Cómo se llama la IA en el chat: las personas le hablan empezando el mensaje con su nombre. */
  readonly iaName = IA_NAME;
  /** Estado de la IA en la sala (quién le pidió algo): se muestra aunque el pedido sea de otra persona. */
  readonly iaStatus = this.collab.iaStatus;
  /** Mensajes de la sala que llegaron con el chat cerrado. */
  readonly unread = signal(0);

  private roomId: string | null = null;
  private historyLoaded = false;
  private wasThinking = false;
  private lastChatTick = this.p2p.chatTick();

  constructor() {
    // El servidor avisa cada vez que alguien escribe en la sala (o la IA contesta): se vuelve a leer la conversación sin que nadie recargue.
    effect(() => {
      const tick = this.p2p.chatTick();
      if (tick === this.lastChatTick) return;
      this.lastChatTick = tick;
      untracked(() => {
        if (this.open()) this.refreshHistory();
        else this.unread.update(count => count + 1);
      });
    });
    // La conversación es de toda la sala: cuando la IA termina un pedido (de quien sea) se vuelve a leer lo que dijeron los demás.
    effect(() => {
      const thinking = this.collab.iaStatus().state === 'thinking';
      const finished = this.wasThinking && !thinking;
      this.wasThinking = thinking;
      if (finished && this.open()) {
        this.refreshHistory();
        this.loadProvider();
      }
    });
  }

  /** Nombre con el que esta persona figura en la sala: sirve para distinguir sus mensajes de los de los demás. */
  readonly myName = computed(() => this.identity.getIdentity().name);

  ngOnInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.roomId = this.route.snapshot.paramMap.get('roomId');
  }

  toggle(): void {
    this.open.update(value => !value);
    if (this.open()) {
      this.unread.set(0);
      this.loadProvider();
      this.loadHistory();
      this.scrollToEnd();
    }
  }

  onDraftInput(event: Event): void {
    this.draft.set((event.target as HTMLTextAreaElement).value);
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }

  /** Responde a la propuesta de la IA con los botones: es lo mismo que decirle «sí» o «no» a Uma (así queda en la conversación de la sala). */
  answerProposal(accept: boolean): void {
    this.send(accept ? 'Sí, aplícalo' : 'No, descártalo', true);
  }

  /** ¿Este texto es para la IA? Si empieza con su nombre, o es un «sí» o «no» corto a una propuesta suya que espera permiso. */
  forIa(text: string): boolean {
    if (isAddressedToIa(text)) return true;
    const words = text.trim().split(/\s+/).length;
    return this.proposal() !== null && words <= 4 && /^(s[ií]|ok|dale|aplic[aá]lo|hazlo|adelante|no|descart[aá]lo|cancela)(?![a-záéíóúñ])/i.test(text.trim());
  }

  /** Se puede enviar: hay texto, el historial cargó y, si es para la IA, ella no está atendiendo a esta persona. */
  readonly canSend = computed(() => {
    const text = this.draft().trim();
    return this.historyReady() && text.length > 0 && !(this.sending() && this.forIa(text));
  });

  /** Cambia el modelo de IA de toda la sala (nube o local), si el servidor lo tiene disponible. */
  chooseProvider(id: string): void {
    const info = this.providerInfo();
    if (!this.roomId || !info || info.provider === id || this.switching()) return;
    this.error.set('');
    this.switching.set(true);
    this.chat.setRoomProvider(this.roomId, id).subscribe({
      next: updated => {
        this.providerInfo.set(updated);
        this.switching.set(false);
      },
      error: (failure: unknown) => {
        // El servidor explica por qué no se pudo cambiar (modelo no disponible, demasiados cambios seguidos).
        const reason = failure instanceof HttpErrorResponse ? failure.error?.error : undefined;
        this.error.set(typeof reason === 'string' ? reason : this.messageFor(failure));
        this.switching.set(false);
      }
    });
  }

  /**
   * Manda lo escrito (o `override`, que usan los botones de la propuesta). Si empieza con el nombre de la IA («Uma, …») se lo pide a ella y el servidor
   * decide si es pregunta, cambio, revisión o historial; si no, es un mensaje para las demás personas y la IA no se entera.
   */
  send(override?: string, toIa?: boolean): void {
    const text = (override ?? this.draft()).trim();
    if (!this.roomId || !text || !this.historyReady()) return;
    if (text.length > MAX_MESSAGE_CHARS) {
      this.error.set(`El mensaje no puede superar ${MAX_MESSAGE_CHARS} caracteres.`);
      return;
    }

    if (!(toIa ?? this.forIa(text))) {
      this.say(text, override === undefined);
      return;
    }
    if (this.sending()) return;

    this.error.set('');
    this.sending.set(true);
    this.append({ role: 'user', content: text, author_name: this.myName() });
    if (override === undefined) this.draft.set('');

    this.actions.request(this.roomId, 'auto', text).subscribe({
      next: response => {
        this.append({ role: 'ia', content: response.reply, author_name: 'IA' });
        // La pregunta y la respuesta ya están guardadas en el servidor: se reemplazan las copias locales por las de la sala.
        this.refreshHistory();
        // Una propuesta nueva reemplaza a la anterior; «sí», «no» o un cambio directo la cierran. Una pregunta no la toca.
        if (response.proposal) {
          this.proposal.set(response.proposal);
          // El cambio propuesto se dibuja sobre el diagrama («holograma») hasta que la persona diga que sí o que no.
          this.actions.showPreview(response.proposal.preview);
        } else if (response.changes || response.intent === 'confirm' || response.intent === 'discard') {
          this.proposal.set(null);
          this.actions.clearPreview();
        }
        this.sending.set(false);
      },
      error: (failure: unknown) => {
        this.error.set(this.messageFor(failure));
        this.sending.set(false);
      }
    });
  }

  /** Un mensaje para las demás personas: aparece enseguida y el servidor lo reparte en vivo a toda la sala. */
  private say(text: string, clearDraft: boolean): void {
    if (!this.roomId) return;
    this.error.set('');
    const localId = this.append({ role: 'user', content: text, author_name: this.myName() });
    if (clearDraft) this.draft.set('');
    this.chat.say(this.roomId, text).subscribe({
      next: () => this.refreshHistory(),
      error: (failure: unknown) => {
        this.messages.update(current => current.filter(message => message.id !== localId));
        if (clearDraft) this.draft.set(text);
        this.error.set(this.sayErrorMessage(failure));
      }
    });
  }

  private sayErrorMessage(failure: unknown): string {
    if (failure instanceof HttpErrorResponse) {
      if (failure.status === 429) return 'Demasiados mensajes seguidos. Espera un momento.';
      if (failure.status === 403) return 'Todavía no te identificaste en la sala. Recarga la página e inténtalo de nuevo.';
    }
    return 'No se pudo enviar el mensaje. Intenta de nuevo.';
  }

  /** Lee qué modelo usa la sala; se vuelve a leer al abrir el chat y cuando la IA termina un pedido, por si alguien lo cambió. */
  private loadProvider(): void {
    if (!this.roomId) return;
    this.chat.roomProvider(this.roomId).subscribe({
      next: info => this.providerInfo.set(info && typeof info.label === 'string' && Array.isArray(info.options) ? info : null),
      error: () => undefined // es solo informativo
    });
  }

  private loadHistory(): void {
    if (!this.roomId || this.historyLoaded) return;
    this.historyLoaded = true;
    this.chat.history(this.roomId).subscribe({
      next: history => {
        this.messages.set(history);
        this.historyReady.set(true);
        this.scrollToEnd();
      },
      error: () => {
        // Sin historial el chat sigue funcionando; se reintenta al reabrir.
        this.historyLoaded = false;
        this.historyReady.set(true);
      }
    });
  }

  /** Vuelve a leer la conversación de la sala; si no trae nada se deja lo que hay en pantalla (la conversación solo crece). */
  private refreshHistory(): void {
    if (!this.roomId) return;
    this.chat.history(this.roomId).subscribe({
      next: history => {
        if (history.length === 0) return;
        this.messages.set(this.withPending(history));
        this.scrollToEnd();
      },
      error: () => undefined
    });
  }

  /** Agrega un mensaje local (todavía no guardado, con id negativo) y devuelve ese id. */
  private append(message: { role: 'user' | 'ia'; content: string; author_name?: string }): number {
    const localId = -(this.messages().length + 1 + Math.floor(Math.random() * 1_000_000));
    this.messages.update(current => [
      ...current,
      {
        id: localId,
        role: message.role,
        author_name: message.author_name,
        content: message.content,
        created_at: new Date().toISOString()
      }
    ]);
    this.scrollToEnd();
    return localId;
  }

  /** Lo de la sala más lo que esta persona acaba de escribir y el servidor todavía no devolvió. */
  private withPending(history: IaChatMessage[]): IaChatMessage[] {
    const pending = this.messages().filter(
      local => local.id < 0 && !history.some(saved => saved.author_name === local.author_name && saved.content === local.content)
    );
    return [...history, ...pending];
  }

  private messageFor(failure: unknown): string {
    return iaErrorMessage(failure);
  }

  private scrollToEnd(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    setTimeout(() => {
      const element = this.messageList?.nativeElement;
      if (element) element.scrollTop = element.scrollHeight;
    });
  }
}
