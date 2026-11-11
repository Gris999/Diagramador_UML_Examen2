import { Injectable, computed, signal } from '@angular/core';

/** Lo que se puede colocar con la paleta: una clase (común, abstracta, interfaz o enumeración) o uno de los tipos de relación. */
export type ToolType = 'class' | 'abstract-class' | 'interface' | 'enumeration' | 'association' | 'generalization' | 'aggregation' | 'composition' | 'dependency' | 'association-class';

export const TOOL_NAMES: Record<ToolType, string> = {
  class: 'la clase',
  'abstract-class': 'la clase abstracta',
  interface: 'la interfaz',
  enumeration: 'la enumeración',
  association: 'la asociación',
  generalization: 'la herencia',
  aggregation: 'la agregación',
  composition: 'la composición',
  dependency: 'la dependencia',
  'association-class': 'la clase asociativa'
};

/** Las herramientas que colocan una clase en el lienzo (el resto son relaciones). */
export const isClassTool = (tool: ToolType): tool is 'class' | 'abstract-class' | 'interface' | 'enumeration' =>
  tool === 'class' || tool === 'abstract-class' || tool === 'interface' || tool === 'enumeration';

export const isToolType = (value: unknown): value is ToolType => typeof value === 'string' && value in TOOL_NAMES;

/**
 * La herramienta elegida en la paleta. Se elige con un clic (sin mantener presionado ni arrastrar): para una clase, el siguiente clic en el
 * lienzo la coloca ahí; para una relación, se hace clic en la clase de origen y luego en la de destino. Con Esc, o volviendo a pulsar la
 * misma herramienta, se cancela.
 */
@Injectable({ providedIn: 'root' })
export class ToolService {
  readonly armed = signal<ToolType | null>(null);
  /** En una relación, cuántos extremos ya se eligieron (0 o 1). */
  readonly chosen = signal(0);

  /** Qué hacer ahora, para mostrarlo sobre el lienzo; vacío si no hay herramienta elegida. */
  readonly hint = computed(() => {
    const tool = this.armed();
    if (!tool) return '';
    const cancel = ' · Esc para cancelar';
    if (isClassTool(tool)) return `Haz clic en el lienzo donde quieras ${TOOL_NAMES[tool]}${cancel}`;
    if (tool === 'association-class') {
      return (this.chosen() === 0 ? 'Haz clic en una clase o en la línea de la asociación' : 'Ahora haz clic en la otra: la clase o la línea') + cancel;
    }
    return (this.chosen() === 0 ? `Haz clic en la clase de origen de ${TOOL_NAMES[tool]}` : 'Ahora haz clic en la clase de destino') + cancel;
  });

  /** Elige una herramienta (cambia la anterior, si había una). */
  arm(tool: ToolType): void {
    this.chosen.set(0);
    this.armed.set(tool);
  }

  /** Elige la herramienta, o la suelta si ya era la elegida. */
  toggle(tool: ToolType): void {
    if (this.armed() === tool) this.clear();
    else this.arm(tool);
  }

  clear(): void {
    this.armed.set(null);
    this.chosen.set(0);
  }
}
