import { Component, inject, signal } from '@angular/core';
import { HelpMessage, HelpService } from '../../services/IA/help.service';
import { iaErrorMessage } from '../../services/IA/ia-chat.service';

const MAX_MESSAGE_CHARS = 2000;

/**
 * Botón «Ayuda» y su panel: el asistente que enseña a usar la herramienta. Sirve en la página principal y dentro de la sala, y su
 * conversación es personal (no la ve nadie más).
 */
@Component({
  selector: 'app-help-panel',
  standalone: true,
  templateUrl: './help-panel.html'
})
export class HelpPanel {
  private readonly help = inject(HelpService);

  readonly open = signal(false);
  readonly messages = signal<HelpMessage[]>([]);
  readonly draft = signal('');
  readonly sending = signal(false);
  readonly error = signal('');
  readonly maxChars = MAX_MESSAGE_CHARS;

  toggle(): void {
    this.open.update(value => !value);
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
    if (!text || this.sending()) return;
    if (text.length > MAX_MESSAGE_CHARS) {
      this.error.set(`El mensaje no puede superar ${MAX_MESSAGE_CHARS} caracteres.`);
      return;
    }

    const previous = this.messages();
    this.error.set('');
    this.sending.set(true);
    this.messages.set([...previous, { role: 'user', content: text }]);
    this.draft.set('');

    this.help.ask(text, previous).subscribe({
      next: reply => {
        this.messages.update(messages => [...messages, { role: 'ia', content: reply }]);
        this.sending.set(false);
      },
      error: (failure: unknown) => {
        this.error.set(iaErrorMessage(failure));
        this.sending.set(false);
      }
    });
  }
}
