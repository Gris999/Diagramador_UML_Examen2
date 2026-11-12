import { inject, Injectable } from '@angular/core';
import { catchError, finalize, map, Observable, retry, switchMap, tap, throwError, timer } from 'rxjs';
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
        // Preguntar y revisar nunca tocan el diagrama, aunque el servidor mande cambios. En el chat único (`auto`) solo se aplica lo que la
        // persona autorizó («sí») o pidió aplicar directamente: una propuesta, una respuesta o un historial no traen nada que aplicar.
        if ((mode !== 'change' && mode !== 'auto') || !response.changes) return response;
        if (mode === 'auto' && response.intent !== 'confirm' && response.intent !== 'change') return response;
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

  /** Muestra sobre el diagrama, como vista previa, lo que la IA propone; no cambia nada hasta que la persona diga que sí. */
  showPreview(changes: unknown): void {
    this.diagram.showHologram(changes);
  }

  /** Quita la vista previa (la persona aplicó o descartó la propuesta). */
  clearPreview(): void {
    this.diagram.clearHologram();
  }

  /**
   * Aplica una idea de la IA a nombre de quien la aplica. Primero la reserva en
   * el servidor (así nadie más la aplica a la vez); cuando el cambio llega al
   * diagrama la confirma, y si no llega a aplicarse la libera. Una reserva que
   * nadie confirma ni libera (por ejemplo, se cerró la pestaña) vence sola.
   */
  applySuggestion(roomId: string, eventId: number, index: number, prompt: string): Observable<string> {
    return this.chat.claimSuggestion(roomId, eventId, index).pipe(
      switchMap(() =>
        this.request(roomId, 'change', prompt).pipe(
          tap(response => {
            if (response.cancelled) this.release(roomId, eventId, index);
            else this.confirm(roomId, eventId, index);
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
    this.withRetries(this.chat.releaseSuggestion(roomId, eventId, index)).subscribe({ error: () => undefined });
  }

  private confirm(roomId: string, eventId: number, index: number): void {
    this.withRetries(this.chat.confirmSuggestion(roomId, eventId, index)).subscribe({ error: () => undefined });
  }

  /** Un fallo de red no debe dejar la idea reservada o sin confirmar: se reintenta un par de veces. */
  private withRetries<T>(request: Observable<T>): Observable<T> {
    return request.pipe(retry({ count: 2, delay: () => timer(1000) }));
  }

  private confirmDeletions(count: number): boolean {
    if (typeof window === 'undefined') return false;
    return window.confirm(
      `La IA quiere eliminar ${count} elemento${count === 1 ? '' : 's'} del diagrama. ¿Aplicar el cambio?`
    );
  }

  private applyChanges(changes: unknown): void {
    this.collab.runAsIa(() => this.diagram.loadFromJson(this.withSafeIds(changes), true));
  }

  /**
   * Los ids que el modelo local inventa para sus clases nuevas («c2», «c3»…) tienen la forma del id interno que Backbone le da a cada celda de JointJS
   * (`cid`): `graph.getCell('c2')` devuelve otra celda y la clase nueva no se agrega. Una clase nueva con un id así recibe uno propio, y las relaciones
   * del mismo cambio lo siguen. Una clase que ya está en el diagrama conserva el suyo.
   */
  private withSafeIds(changes: unknown): unknown {
    const source = changes as { classes?: any[]; relationships?: any[] } | null;
    if (!source || !Array.isArray(source.classes)) return changes;
    const existing = new Set<string>(((this.diagram.exportToJson() as any)?.classes ?? []).map((cls: any) => cls?.id));
    const renamed = new Map<string, string>();
    const classes = source.classes.map(cls => {
      const id = cls?.id;
      if (typeof id !== 'string' || !/^c\d+$/.test(id) || existing.has(id)) return cls;
      const fresh = renamed.get(id) ?? crypto.randomUUID();
      renamed.set(id, fresh);
      return { ...cls, id: fresh };
    });
    if (renamed.size === 0) return changes;
    const relationships = Array.isArray(source.relationships)
      ? source.relationships.map(rel => ({ ...rel, sourceId: renamed.get(rel?.sourceId) ?? rel?.sourceId, targetId: renamed.get(rel?.targetId) ?? rel?.targetId }))
      : source.relationships;
    return { ...source, classes, relationships };
  }
}
