import { isPlatformBrowser } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, ElementRef, inject, OnInit, PLATFORM_ID, signal, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { DiagramService } from '../../services/diagram/diagram.service';
import { IaChatMessage, IaChatService } from '../../services/IA/ia-chat.service';

const MAX_MESSAGE_CHARS = 2000;

@Component({
  selector: 'app-ia-chat-panel',
  standalone: true,
  templateUrl: './ia-chat-panel.html'
})
export class IaChatPanel implements OnInit {
  private readonly chat = inject(IaChatService);
  private readonly diagram = inject(DiagramService);
  private readonly route = inject(ActivatedRoute);
  private readonly platformId = inject(PLATFORM_ID);

  @ViewChild('messageList') messageList?: ElementRef<HTMLElement>;

  readonly open = signal(false);
  readonly messages = signal<IaChatMessage[]>([]);
  readonly draft = signal('');
  readonly sending = signal(false);
  readonly error = signal('');
  readonly maxChars = MAX_MESSAGE_CHARS;

  private roomId: string | null = null;
  private historyLoaded = false;

  ngOnInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.roomId = this.route.snapshot.paramMap.get('roomId');
  }

  toggle(): void {
    this.open.update(value => !value);
    if (this.open()) {
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

  send(): void {
    const text = this.draft().trim();
    if (!this.roomId || !text || this.sending()) return;
    if (text.length > MAX_MESSAGE_CHARS) {
      this.error.set(`El mensaje no puede superar ${MAX_MESSAGE_CHARS} caracteres.`);
      return;
    }

    this.error.set('');
    this.sending.set(true);
    this.append({ role: 'user', content: text });
    this.draft.set('');

    this.chat.ask(this.roomId, text, this.diagram.exportToJson()).subscribe({
      next: reply => {
        this.append({ role: 'ia', content: reply });
        this.sending.set(false);
      },
      error: (failure: unknown) => {
        this.error.set(this.messageFor(failure));
        this.sending.set(false);
      }
    });
  }

  private loadHistory(): void {
    if (!this.roomId || this.historyLoaded) return;
    this.historyLoaded = true;
    this.chat.history(this.roomId).subscribe({
      next: history => {
        // Si el usuario ya escribió algo mientras cargaba, se conserva debajo del historial.
        this.messages.update(current => [...history, ...current]);
        this.scrollToEnd();
      },
      error: () => {
        // Sin historial el chat sigue funcionando; se reintenta al reabrir.
        this.historyLoaded = false;
      }
    });
  }

  private append(message: { role: 'user' | 'ia'; content: string }): void {
    this.messages.update(current => [
      ...current,
      {
        id: -(current.length + 1),
        role: message.role,
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
