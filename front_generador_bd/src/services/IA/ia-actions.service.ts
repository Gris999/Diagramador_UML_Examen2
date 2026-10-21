import { inject, Injectable } from '@angular/core';
import { map, Observable, tap } from 'rxjs';
import { CollaborationService } from '../colaboration/collaboration.service';
import { IdentityService } from '../colaboration/identity.service';
import { DiagramService } from '../diagram/diagram.service';
import { IaChatMode, IaChatResponse, IaChatService } from './ia-chat.service';

/**
 * Orquesta lo que la IA hace en la sala. La IA nunca actúa sola: cada llamada
 * nace de un pedido explícito de una persona, y sus cambios se aplican en el
 * navegador de esa persona por la misma ruta que la edición manual, de modo
 * que se propagan a todos y quedan registrados "IA, a pedido de X".
 */
@Injectable({ providedIn: 'root' })
export class IaActionsService {
  private readonly chat = inject(IaChatService);
  private readonly diagram = inject(DiagramService);
  private readonly collab = inject(CollaborationService);
  private readonly identity = inject(IdentityService);

  request(roomId: string, mode: IaChatMode, message: string): Observable<IaChatResponse> {
    const requester = this.identity.getIdentity().name;
    this.collab.setIaStatus('thinking', requester);

    return this.chat.send(roomId, mode, message, this.diagram.exportToJson()).pipe(
      tap({
        next: response => {
          if (mode === 'change' && response.changes) this.applyChanges(response.changes);
        },
        // Se avisa a la sala que la IA terminó, haya salido bien o mal.
        error: () => this.collab.setIaStatus('idle', ''),
        complete: () => this.collab.setIaStatus('idle', '')
      })
    );
  }

  /** Aplica una idea de la IA (a nombre de quien la aplica) y la marca como aplicada. */
  applySuggestion(roomId: string, eventId: number, index: number, prompt: string): Observable<string> {
    return this.request(roomId, 'change', prompt).pipe(
      tap(() => this.collab.markSuggestionApplied(eventId, index)),
      map(response => response.reply)
    );
  }

  private applyChanges(changes: unknown): void {
    this.collab.runAsIa(() => this.diagram.loadFromJson(changes, true));
  }
}
