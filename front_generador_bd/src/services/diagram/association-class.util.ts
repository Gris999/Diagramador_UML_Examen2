import { isManyToManyLabels, junctionLegId } from './junction-naming.util';

// Representación mínima y agnóstica de framework de una relación, común entre
// las celdas JointJS del grafo en vivo (via adaptador) y los DTO planos que
// se exportan a JSON.
export interface RelationshipLike {
  id: string;
  type: string;
  sourceId: string;
  targetId: string;
  labels?: Array<string | undefined | null>;
}

export interface AssociationClassAttachment {
  classId: string;
  /** Conectores punteados que unen la clase con la asociación: uno en la notación UML, dos en la forma anterior. */
  linkIds: string[];
}

/**
 * Detecta, para cada relación M:N, si existe una "clase asociativa" real
 * enlazada a ella. Hay dos formas:
 *
 *  - Notación UML (StarUML, Enterprise Architect): UN conector punteado
 *    'association-class' que va de la clase al MEDIO de la línea M:N, es decir,
 *    su otro extremo es la propia relación (su id), no una clase.
 *  - Forma anterior de esta herramienta: una clase conectada por DOS conectores
 *    punteados, uno hacia cada extremo de la M:N.
 *
 * Devuelve un mapa id-de-relación-M:N -> clase/conectores asociativos.
 */
export function findAssociationClassAttachments(
  relationships: RelationshipLike[]
): Map<string, AssociationClassAttachment> {
  const result = new Map<string, AssociationClassAttachment>();
  const mnRels = relationships.filter(r => isManyToManyLabels(r.labels));
  const assocLinks = relationships.filter(r => r.type === 'association-class');

  for (const mn of mnRels) {
    // Notación UML: el conector punteado apunta a la propia asociación.
    const toLine = assocLinks.find(l =>
      (l.targetId === mn.id && l.sourceId !== mn.id) || (l.sourceId === mn.id && l.targetId !== mn.id)
    );
    if (toLine) {
      const classId = toLine.targetId === mn.id ? toLine.sourceId : toLine.targetId;
      result.set(mn.id, { classId, linkIds: [toLine.id] });
      continue;
    }

    // Forma anterior: dos conectores, uno hacia cada extremo de la M:N.
    const linksToSource = assocLinks.filter(l => l.sourceId === mn.sourceId || l.targetId === mn.sourceId);
    const linksToTarget = assocLinks.filter(l => l.sourceId === mn.targetId || l.targetId === mn.targetId);

    let found = false;
    for (const l1 of linksToSource) {
      if (found) break;
      const classFromL1 = l1.sourceId === mn.sourceId ? l1.targetId : l1.sourceId;
      for (const l2 of linksToTarget) {
        if (l2.id === l1.id) continue;
        const classFromL2 = l2.sourceId === mn.targetId ? l2.targetId : l2.sourceId;
        if (
          classFromL1 === classFromL2 &&
          classFromL1 !== mn.sourceId &&
          classFromL1 !== mn.targetId
        ) {
          result.set(mn.id, { classId: classFromL1, linkIds: [l1.id, l2.id] });
          found = true;
          break;
        }
      }
    }
  }
  return result;
}

/**
 * Transforma, SOLO para el payload que reciben los generadores (SQL/Spring/
 * Flutter), cada relación M:N que tiene una clase asociativa real enlazada
 * en el par de relaciones 1:N que esos generadores ya saben interpretar,
 * preservando los atributos propios de la clase (p.ej. precioUnitario).
 * También retira del payload todos los conectores 'association-class': los
 * generadores no los usan y uno de sus extremos puede ser una relación, no una clase.
 *
 * No modifica el grafo visual ni lo que se persiste: se aplica únicamente sobre
 * una copia del JSON, justo antes de enviarlo a un generador.
 *
 * Con `onlyGenerated` solo se resuelven las clases asociativas que la herramienta
 * generó sola (marcadas `generated`); las que dibujó la persona se dejan como están.
 */
export function resolveAssociationClassesForGenerators<
  TClass extends { id: string; generated?: boolean },
  TRel extends RelationshipLike
>(
  dto: { classes: TClass[]; relationships: TRel[] },
  options: { onlyGenerated?: boolean } = {}
): { classes: TClass[]; relationships: TRel[] } {
  const generatedClassIds = new Set(dto.classes.filter(c => c.generated).map(c => c.id));
  const attachments = new Map(
    [...findAssociationClassAttachments(dto.relationships)]
      .filter(([, attachment]) => !options.onlyGenerated || generatedClassIds.has(attachment.classId))
  );
  const hasConnectors = dto.relationships.some(r => r.type === 'association-class');
  if (attachments.size === 0 && !hasConnectors) return dto;

  const mnIdsToRemove = new Set<string>(attachments.keys());
  const newRelationships: TRel[] = [];

  attachments.forEach((attachment, mnId) => {
    const mn = dto.relationships.find(r => r.id === mnId)!;
    const leg1: RelationshipLike = {
      id: junctionLegId(mn.sourceId, attachment.classId, 'source'),
      type: 'association',
      sourceId: mn.sourceId,
      targetId: attachment.classId,
      labels: ['1', '0..*']
    };
    const leg2: RelationshipLike = {
      id: junctionLegId(mn.targetId, attachment.classId, 'target'),
      type: 'association',
      sourceId: mn.targetId,
      targetId: attachment.classId,
      labels: ['1', '0..*']
    };
    newRelationships.push(leg1 as TRel, leg2 as TRel);
  });

  // Los conectores punteados se quitan siempre; con `onlyGenerated`, los de las clases que dibujó la
  // persona se dejan donde están para que quien consume el JSON decida (el intercambio XMI los filtra).
  const keptRelationships = dto.relationships.filter(r => {
    if (mnIdsToRemove.has(r.id)) return false;
    if (r.type !== 'association-class') return true;
    return !!options.onlyGenerated && !isConnectorOfResolved(r, attachments);
  });

  return {
    classes: dto.classes,
    relationships: [...keptRelationships, ...newRelationships]
  };
}

function isConnectorOfResolved(
  connector: RelationshipLike,
  attachments: Map<string, AssociationClassAttachment>
): boolean {
  for (const attachment of attachments.values()) {
    if (attachment.linkIds.includes(connector.id)) return true;
  }
  return false;
}
