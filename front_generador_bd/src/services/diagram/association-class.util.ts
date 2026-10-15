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
  linkIds: [string, string];
}

/**
 * Detecta, para cada relación M:N, si existe una "clase asociativa" real
 * enlazada a ella: una clase conectada por DOS relaciones de tipo
 * 'association-class', una hacia cada extremo de la M:N.
 *
 * Devuelve un mapa id-de-relación-M:N -> clase/enlaces asociativos.
 */
export function findAssociationClassAttachments(
  relationships: RelationshipLike[]
): Map<string, AssociationClassAttachment> {
  const result = new Map<string, AssociationClassAttachment>();
  const mnRels = relationships.filter(r => isManyToManyLabels(r.labels));
  const assocLinks = relationships.filter(r => r.type === 'association-class');

  for (const mn of mnRels) {
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
 * en el par de relaciones 1:N que esos generadores ya saben interpretar
 * (misma forma que reconcileGeneratedJunctions() produce automáticamente),
 * preservando los atributos propios de la clase (p.ej. precioUnitario).
 *
 * No modifica el grafo visual ni lo que se persiste/exporta a XMI: se aplica
 * únicamente sobre una copia del JSON, justo antes de enviarlo a un generador.
 */
export function resolveAssociationClassesForGenerators<
  TClass extends { id: string },
  TRel extends RelationshipLike
>(dto: { classes: TClass[]; relationships: TRel[] }): { classes: TClass[]; relationships: TRel[] } {
  const attachments = findAssociationClassAttachments(dto.relationships);
  if (attachments.size === 0) return dto;

  const linkIdsToRemove = new Set<string>();
  const mnIdsToRemove = new Set<string>();
  const newRelationships: TRel[] = [];

  attachments.forEach((attachment, mnId) => {
    mnIdsToRemove.add(mnId);
    attachment.linkIds.forEach(id => linkIdsToRemove.add(id));

    const mn = dto.relationships.find(r => r.id === mnId)!;
    const leg1: RelationshipLike = {
      id: junctionLegId(mn.sourceId, attachment.classId),
      type: 'association',
      sourceId: mn.sourceId,
      targetId: attachment.classId,
      labels: ['1', '0..*']
    };
    const leg2: RelationshipLike = {
      id: junctionLegId(mn.targetId, attachment.classId),
      type: 'association',
      sourceId: mn.targetId,
      targetId: attachment.classId,
      labels: ['1', '0..*']
    };
    newRelationships.push(leg1 as TRel, leg2 as TRel);
  });

  const keptRelationships = dto.relationships.filter(
    r => !mnIdsToRemove.has(r.id) && !linkIdsToRemove.has(r.id)
  );

  return {
    classes: dto.classes,
    relationships: [...keptRelationships, ...newRelationships]
  };
}
