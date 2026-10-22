import { inject, Injectable } from '@angular/core';
import { catchError, finalize, map, Observable, switchMap, tap, throwError } from 'rxjs';
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
    const requestId = this.collab.startIaRequest(this.identity.getIdentity().name);

    return this.chat.send(roomId, mode, message, this.diagram.exportToJson()).pipe(
      map(response => {
        if (mode !== 'change' || !response.changes) return response;
        // El modelo lee el diagrama, que puede traer texto malicioso: antes de
        // aplicar un cambio que elimina cosas se le pide confirmación a la persona.
        const deletions = response.destructive ?? 0;
        if (deletions > 0 && !this.confirmDeletions(deletions)) {
          return {
            ...response,
            changes: undefined,
            cancelled: true,
            reply: 'Cancelaste el cambio: no se modificó el diagrama.'
          };
        }
        this.applyChanges(response.changes);
        return response;
      }),
      // Se avisa a la sala que la IA terminó, haya salido bien o mal.
      finalize(() => this.collab.finishIaRequest(requestId))
    );
  }

  /**
   * Aplica una idea de la IA a nombre de quien la aplica. Primero la reserva en
   * el servidor (así nadie más la aplica a la vez y queda marcada para todos);
   * si el cambio no llega a aplicarse, la libera.
   */
  applySuggestion(roomId: string, eventId: number, index: number, prompt: string): Observable<string> {
    return this.chat.claimSuggestion(roomId, eventId, index).pipe(
      switchMap(() =>
        this.request(roomId, 'change', prompt).pipe(
          tap(response => {
            if (response.cancelled) this.release(roomId, eventId, index);
          }),
          catchError(error => {
            this.release(roomId, eventId, index);
            return throwError(() => error);
          })
        )
      ),
      map(response => response.reply)
    );
  }

  private release(roomId: string, eventId: number, index: number): void {
    this.chat.releaseSuggestion(roomId, eventId, index).subscribe({ error: () => undefined });
  }

  private confirmDeletions(count: number): boolean {
    if (typeof window === 'undefined') return false;
    return window.confirm(
      `La IA quiere eliminar ${count} elemento${count === 1 ? '' : 's'} del diagrama. ¿Aplicar el cambio?`
    );
  }

  private applyChanges(changes: unknown): void {
    this.collab.runAsIa(() => this.diagram.loadFromJson(changes, true));
  }
}
