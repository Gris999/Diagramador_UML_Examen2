import { Injectable, signal } from '@angular/core';
import { P2PService } from './p2p.service';
import { DiagramApi } from './diagram-api';
import { BackupService } from '../exports/backup.service';

type Op = 
  | { t: 'add_class'; id: string; payload: any }
  | { t: 'edit_text'; id: string; field: 'name' | 'attributes' | 'methods'; value: string }
  | { t: 'move'; id: string; x: number; y: number }
  | { t: 'resize'; id: string; w: number; h: number }
  | { t: 'add_link'; id: string; sourceId: string; targetId: string; payload?: any }
  | { t: 'edit_label'; linkId: string; index: number; text: string }
  | { t: 'add_label'; linkId: string; index: number; label: any }
  | { t: 'del_label'; linkId: string; index: number }
  | { t: 'move_label'; linkId: string; index: number; position: { distance: number; offset?: number } }
  | { t: 'move_link'; id: string; sourceId: string; targetId: string }
  | { t: 'update_vertices'; id: string; vertices: any[] }
  | { t: 'delete'; id: string }
  | { t: 'request_full_state' }
  | { t: 'full_state'; payload: any }
  | { t: 'ia_status'; state: 'thinking' | 'idle'; by: string }
  | { t: 'ia_suggestion_applied'; eventId: number; index: number };

export type IaStatus = { state: 'thinking' | 'idle'; by: string };

// Si quien pidió algo a la IA se desconecta antes de terminar, los demás no
// deben ver "pensando…" para siempre.
const IA_THINKING_TIMEOUT_MS = 90_000;

@Injectable({ providedIn: 'root' })
export class CollaborationService {
  private api?: DiagramApi;
  private ready = false;
  private viaIa = false;
  private iaThinkingTimer?: ReturnType<typeof setTimeout>;

  /** Estado de la IA en la sala: quién le pidió algo y si está trabajando. */
  readonly iaStatus = signal<IaStatus>({ state: 'idle', by: '' });
  /** Ideas de la IA ya aplicadas por alguien (`eventId:índice`), compartido en vivo. */
  readonly appliedSuggestions = signal<ReadonlySet<string>>(new Set());
  constructor(
    private p2p: P2PService,
    private backup: BackupService
  ) {}

  registerDiagramApi(api: DiagramApi) {
    this.api = api;
  }

  init(roomId: string) {
    this.p2p.onData = (_: string | undefined, data: Op) => {
      if (this.handleIaSignal(data)) return;
      if (!this.api?.getGraph()) return;
      this.applyRemoteOp(data);
    };
    this.p2p.onReady = () => {
      if (!this.api?.getGraph()?.getCells()?.length) {
        this.broadcast({ t: 'request_full_state' });
      }
    };
    this.p2p.init(roomId);
    this.ready = true;
    setTimeout(() => {
      if (!this.api?.getGraph()?.getCells()?.length) {
        console.log('[Collab] Nadie respondió, cargo backup de BD...');
        this.backup.getBackup(roomId).subscribe({
          next: (snapshot) => {
            if (snapshot) this.api!.loadFromJson(snapshot, true);
          },
          error: (err) => console.error('[Collab] Error obteniendo backup', err)
        });
      }
    }, 3000);
  }

  broadcast(op: Op) {
    if (!this.ready) return;
    // Los cambios que la IA aplica a pedido de alguien viajan marcados para que
    // el servidor los registre como "IA, a pedido de X".
    this.p2p.sendToAll(this.viaIa ? { ...op, via_ia: true } : op);
  }

  /** Ejecuta `action` marcando como de la IA todas las operaciones que emita. */
  runAsIa<T>(action: () => T): T {
    this.viaIa = true;
    try {
      return action();
    } finally {
      this.viaIa = false;
    }
  }

  setIaStatus(state: IaStatus['state'], by: string): void {
    this.applyIaStatus({ state, by });
    this.broadcast({ t: 'ia_status', state, by });
  }

  markSuggestionApplied(eventId: number, index: number): void {
    this.addAppliedSuggestion(eventId, index);
    this.broadcast({ t: 'ia_suggestion_applied', eventId, index });
  }

  private handleIaSignal(op: Op): boolean {
    if (op?.t === 'ia_status') {
      this.applyIaStatus({ state: op.state === 'thinking' ? 'thinking' : 'idle', by: String(op.by ?? '') });
      return true;
    }
    if (op?.t === 'ia_suggestion_applied') {
      this.addAppliedSuggestion(op.eventId, op.index);
      return true;
    }
    return false;
  }

  private applyIaStatus(status: IaStatus): void {
    clearTimeout(this.iaThinkingTimer);
    this.iaStatus.set(status);
    if (status.state === 'thinking') {
      this.iaThinkingTimer = setTimeout(
        () => this.iaStatus.set({ state: 'idle', by: '' }),
        IA_THINKING_TIMEOUT_MS
      );
    }
  }

  private addAppliedSuggestion(eventId: number, index: number): void {
    this.appliedSuggestions.update(current => new Set(current).add(`${eventId}:${index}`));
  }

  closeSocketRTC() {
    this.p2p.closeSocketRTC();
    this.ready = false;
  }

  private applyRemoteOp(op: Op) {
    try {
      const graph = this.api!.getGraph();
      const joint = this.api!.getJoint();
      switch (op.t) {
        case 'add_class': {
          if (graph.getCell(op.id)) break;
          this.api!.createUmlClass({
            ...op.payload,
            id: op.id,
            pendingJunctionSync: !!op.payload?.generated
          }, true);
          break;
        }
        case 'edit_text': {
          const m = graph.getCell(op.id);
          if (!m) break;
          const map = {
            name: '.uml-class-name-text',
            attributes: '.uml-class-attrs-text',
            methods: '.uml-class-methods-text',
          } as const;

          m.attr(`${map[op.field]}/text`, op.value);
          m.set(op.field, op.value);
          if (!this.api || !this.api.getEdition) {
            console.warn('[Collab] API no soporta getEdition');
            break;
          }
          // 🔴 Forzar auto-resize en receptor
          this.api?.getEdition()?.scheduleAutoResize(m, this.api!.getPaper?.() ?? null);
          break;
        }


        case 'move': {
          const m = graph.getCell(op.id);
          if (!m) break;
          m.position(op.x, op.y);
          break;
        }
        case 'resize': {
          const m = graph.getCell(op.id);
          if (!m) break;
          m.resize(op.w, op.h);
          break;
        }
        case 'add_link': {
          if (graph.getCell(op.id)) break;

          const type = op.payload?.type || 'association';
          
          if (!this.api || !this.api.createTypedRelationship) {
            console.warn('[Collab] API no soporta createTypedRelationship');
            break;
          }
          // construir SIN agregar (remote=true)
          const link = this.api!.createTypedRelationship(op.sourceId, op.targetId, type, true);

          // setear ID, tipo y labels ANTES de insertar
          link.set('id', op.id);
          link.set('relationType', type);
          if (op.payload?.labels) link.set('labels', op.payload.labels);
          if (op.payload?.generated) link.set('generatedJunctionLeg', true);
          if (op.payload?.junctionOptOut) link.set('junctionOptOut', true);

          // agregar una única vez, marcado como remoto
          graph.addCell(link, { collab: true });

          if (op.payload?.generated) {
            const junction = graph.getCell(op.targetId);
            const generatedLegs = graph.getLinks?.().filter((candidate: any) =>
              candidate.get('generatedJunctionLeg') &&
              candidate.get('target')?.id === op.targetId
            ) || [];
            if (junction?.get?.('pendingJunctionSync') && generatedLegs.length >= 2) {
              junction.set('pendingJunctionSync', false, { silent: true });
            }
          }
          break;
        }

        case 'move_link': {
          const link = graph.getCell(op.id);
          if (!link) break;
          link.set('source', { id: op.sourceId }, { collab: true });
          link.set('target', { id: op.targetId }, { collab: true });
          break;
        }

        case 'update_vertices': {
          const link = graph.getCell(op.id);
          if (!link) break;
          link.set('vertices', op.vertices, { collab: true });
          break;
        }


        case 'add_label': {
          const link = graph.getCell(op.linkId);
          if (!link) break;

          // aseguramos markup para compatibilidad
          const label = {
            ...op.label,
            markup: op.label.markup || [{ tagName: 'text', selector: 'text' }]
          };

          link.insertLabel(op.index, label);
          link.set('labels', link.labels());
          link.trigger('change:labels', link, link.labels());
          break;
        }

        case 'edit_label': {
          const link = graph.getCell(op.linkId);
          if (!link) break;
          const labels = link.labels() || [];
          if (op.index < 0 || op.index >= labels.length) break;

          const lbl = labels[op.index];
          link.label(op.index, {
            ...lbl,
            attrs: { ...lbl.attrs, text: { ...lbl.attrs?.text, text: op.text } },
            markup: lbl.markup || [{ tagName: 'text', selector: 'text' }]
          });
          link.set('labels', link.labels());
          link.trigger('change:labels', link, link.labels());
          break;
        }

        case 'move_label': {
          const link = graph.getCell(op.linkId);
          if (!link) break;
          const labels = link.labels() || [];
          if (op.index < 0 || op.index >= labels.length) break;

          const lbl = labels[op.index];
          link.label(op.index, {
            ...lbl,
            position: op.position,
            markup: lbl.markup || [{ tagName: 'text', selector: 'text' }]
          });
          link.set('labels', link.labels());
          link.trigger('change:labels', link, link.labels());
          break;
        }

        case 'del_label': {
          const link = graph.getCell(op.linkId);
          if (!link) break;
          link.removeLabel(op.index);
          link.set('labels', link.labels()); 
          link.trigger('change:labels', link, link.labels());
          break;
        }


        case 'delete': {
          const m = graph.getCell(op.id);
          if (m) m.remove({ collab: true }); // <- importante para no re-emitir
          break;
        }

        case 'request_full_state': {
          const snapshot = this.api!.exportToJson();
          this.broadcast({ t: 'full_state', payload: snapshot });
          break;
        }

        case 'full_state': {
          if (this.api) {
            this.api!.loadFromJson(op.payload, false, true);
          }
          break;
        }


      }
    } catch (err) {
      console.error('[Collab] applyRemoteOp error', op, err);
    }
  }
}
