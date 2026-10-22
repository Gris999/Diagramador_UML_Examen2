import { isPlatformBrowser } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, ElementRef, inject, OnInit, PLATFORM_ID, signal, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { IaActionsService } from '../../services/IA/ia-actions.service';
import { IaChatMessage, IaChatMode, IaChatService } from '../../services/IA/ia-chat.service';

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

  @ViewChild('messageList') messageList?: ElementRef<HTMLElement>;

  readonly open = signal(false);
  readonly messages = signal<IaChatMessage[]>([]);
  readonly draft = signal('');
  readonly sending = signal(false);
  /** El historial ya se cargó (o falló): hasta entonces no se envía, para no duplicar mensajes. */
  readonly historyReady = signal(false);
  readonly error = signal('');
  readonly maxChars = MAX_MESSAGE_CHARS;
  readonly mode = signal<IaChatMode>('ask');
  readonly modes: { id: IaChatMode; label: string; hint: string }[] = [
    { id: 'ask', label: 'Preguntar', hint: 'La IA solo responde: no toca el diagrama' },
    { id: 'change', label: 'Pedir cambio', hint: 'La IA modifica el diagrama y todos lo ven' },
    { id: 'review', label: 'Revisar', hint: 'La IA revisa el diagrama y publica sus ideas para todos' }
  ];

  /** "IA local (modelo)" o "IA en la nube (Gemini)"; vacío si no se pudo saber. */
  readonly providerLabel = signal('');

  readonly modeHint = computed(() => this.modes.find(option => option.id === this.mode())?.hint ?? '');

  private roomId: string | null = null;
  private historyLoaded = false;

  ngOnInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.roomId = this.route.snapshot.paramMap.get('roomId');
  }

  toggle(): void {
    this.open.update(value => !value);
    if (this.open()) {
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

  setMode(mode: IaChatMode): void {
    this.mode.set(mode);
  }

  send(): void {
    const mode = this.mode();
    const typed = this.draft().trim();
    // Revisar no necesita texto: el servidor usa un pedido por defecto.
    const text = typed || (mode === 'review' ? 'Revisa el diagrama' : '');
    if (!this.roomId || !text || this.sending() || !this.historyReady()) return;
    if (text.length > MAX_MESSAGE_CHARS) {
      this.error.set(`El mensaje no puede superar ${MAX_MESSAGE_CHARS} caracteres.`);
      return;
    }

    this.error.set('');
    this.sending.set(true);
    this.append({ role: 'user', content: text, mode });
    this.draft.set('');

    this.actions.request(this.roomId, mode, text).subscribe({
      next: response => {
        this.append({ role: 'ia', content: response.reply, mode });
        this.sending.set(false);
      },
      error: (failure: unknown) => {
        this.error.set(this.messageFor(failure));
        this.sending.set(false);
      }
    });
  }

  private loadProvider(): void {
    if (this.providerLabel()) return;
    this.chat.provider().subscribe({
      next: info => this.providerLabel.set(typeof info?.label === 'string' ? info.label : ''),
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

  private append(message: { role: 'user' | 'ia'; content: string; mode?: IaChatMode }): void {
    this.messages.update(current => [
      ...current,
      {
        id: -(current.length + 1),
        role: message.role,
        mode: message.mode,
        content: message.content,
        created_at: new Date().toISOString()
      }
    ]);
    this.scrollToEnd();
  }

  private messageFor(failure: unknown): string {
    if (failure instanceof HttpErrorResponse) {
      if (failure.status === 429) return 'Demasiadas preguntas seguidas. Espera un momento.';
      if (failure.status === 403) {
        return 'Todavía no te identificaste en la sala. Recarga la página e inténtalo de nuevo.';
      }
      if (failure.status === 400 && typeof failure.error?.error === 'string') {
        return failure.error.error;
      }
    }
    return 'La IA no pudo responder ahora. Intenta de nuevo.';
  }

  private scrollToEnd(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    setTimeout(() => {
      const element = this.messageList?.nativeElement;
      if (element) element.scrollTop = element.scrollHeight;
    });
  }
}
