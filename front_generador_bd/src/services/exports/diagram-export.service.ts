import { Injectable } from '@angular/core';

export interface UmlClassDTO {
  id: string;
  name: string;
  attributes: { name: string; type: string }[];
  methods: { name: string; parameters?: string; returnType?: string }[];
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

        classes.push({
          id: cell.id,
          name: cell.get('name'),
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

  private parseAttributesFromText(text: string): { name: string; type: string }[] {
    if (!text) return [];
    return text.split('\n').map(line => {
      const [name, type] = line.split(':').map(s => s.trim());
      return { name: name || '', type: type || '' };
    });
  }

  private parseMethodsFromText(text: string): { name: string; parameters?: string; returnType?: string }[] {
    if (!text) return [];
    return text.split('\n').map(line => {
      const match = line.match(/^(\w+)\(([^)]*)\)(?::\s*(\w+))?/);
      if (match) {
        return {
          name: match[1],
          parameters: match[2] || '',
          returnType: match[3] || ''
        };
      }
      return { name: line.trim() };
    });
  }
}
