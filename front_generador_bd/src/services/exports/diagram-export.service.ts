import { Injectable } from '@angular/core';
import { ClassKind, Visibility, isCodeEntity, kindOf, parseAttributeLine, parseMethodLine } from '../diagram/uml-notation.util';

export interface UmlClassDTO {
  id: string;
  name: string;
  /** Solo viaja cuando no es una clase común: «abstract», «interface» o «enumeration». */
  kind?: ClassKind;
  attributes: { name: string; type: string; visibility?: Visibility }[];
  methods: { name: string; parameters?: string; returnType?: string; visibility?: Visibility }[];
  position: { x: number; y: number };
  size: { width: number; height: number };
  // true = entidad intermedia generada automáticamente para una asociación M:N.
  // Los generadores backend no necesitan leer este campo (lo ignoran como
  // cualquier campo desconocido): la clase ya llega como una clase regular con
  // sus propias relaciones 1:N, así que se genera correctamente sin cambios.
  generated?: boolean;
  junctionOrigin?: {
    id: string;
    type: string;
    sourceId: string;
    targetId: string;
    labels: any[];
    vertices: { x: number; y: number }[];
  };
}

export interface UmlRelationshipDTO {
  id: string;
  type: string;              // association | aggregation | generalization | etc.
  sourceId: string;
  targetId: string;
  labels?: string[];
  vertices?: { x: number; y: number }[];
  // true = es una de las 2 relaciones 1:N generadas automáticamente hacia una
  // entidad intermedia M:N (ver UmlClassDTO.generated).
  generated?: boolean;
  // Impide que una M:N restaurada después de editar una pata vuelva a
  // materializarse automáticamente como junction en la siguiente mutación.
  junctionOptOut?: boolean;
}

export interface UmlExportDTO {
  classes: UmlClassDTO[];
  relationships: UmlRelationshipDTO[];
}

@Injectable({ providedIn: 'root' })
export class DiagramExportService {
  /**
   * Exporta el grafo a un JSON limpio y usable para el backend
   */
  export(graph: any): UmlExportDTO {
    const classes: UmlClassDTO[] = [];
    const relationships: UmlRelationshipDTO[] = [];

    graph.getCells().forEach((cell: any) => {
      if (cell.isElement?.()) {
        const rawAttrs = cell.get('attributes');
        const rawMeths = cell.get('methods');

        const attributes = Array.isArray(rawAttrs)
          ? rawAttrs
          : this.parseAttributesFromText(rawAttrs);

        const methods = Array.isArray(rawMeths)
          ? rawMeths
          : this.parseMethodsFromText(rawMeths);

        const kind = kindOf(cell.get('kind'));

        classes.push({
          id: cell.id,
          name: cell.get('name'),
          ...(kind !== 'class' ? { kind } : {}),
          attributes,
          methods,
          position: cell.position(),  // 👈 posición
          size: cell.size(),          // 👈 tamaño
          ...(cell.get('generatedJunction') ? { generated: true } : {}),
          ...(cell.get('junctionOrigin') ? { junctionOrigin: cell.get('junctionOrigin') } : {})
        });
      } else if (cell.isLink?.()) {
        const sourceId = cell.get('source')?.id;
        const targetId = cell.get('target')?.id;
        // Una relación sin clase en alguno de sus extremos no es una relación UML: no se guarda, no se comparte ni se exporta.
        if (!sourceId || !targetId) return;
        relationships.push({
          id: cell.id,
          type: cell.get('relationType') || 'association',
          sourceId,
          targetId,
          labels: (cell.get('labels') || []).map((lbl: any) => lbl.attrs?.text?.text),
          vertices: cell.get('vertices') || [],
          ...(cell.get('generatedJunctionLeg') ? { generated: true } : {}),
          ...(cell.get('junctionOptOut') ? { junctionOptOut: true } : {})
        });
      }
    });

    return { classes, relationships };
  }

  // ========= Helpers privados =========

  private parseAttributesFromText(text: string): { name: string; type: string; visibility?: Visibility }[] {
    if (!text) return [];
    return text.split('\n').map(line => parseAttributeLine(line));
  }

  private parseMethodsFromText(text: string): { name: string; parameters?: string; returnType?: string; visibility?: Visibility }[] {
    if (!text) return [];
    return text.split('\n').map(line => parseMethodLine(line));
  }

  /**
   * El diagrama tal como lo necesitan los generadores de código (SQL, Spring Boot, Flutter): las interfaces y las enumeraciones no son
   * tablas ni entidades, así que se quitan junto con las relaciones que las tocan. Las clases abstractas sí se generan.
   */
  forCode(dto: UmlExportDTO): UmlExportDTO {
    const dropped = new Set(dto.classes.filter(c => !isCodeEntity(c.kind)).map(c => c.id));
    if (dropped.size === 0) return dto;
    return {
      classes: dto.classes.filter(c => !dropped.has(c.id)),
      relationships: dto.relationships.filter(r => !dropped.has(r.sourceId) && !dropped.has(r.targetId))
    };
  }
}
