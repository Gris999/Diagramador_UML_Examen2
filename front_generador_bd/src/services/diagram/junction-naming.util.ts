// Utilidades puras (sin dependencia de JointJS) para detectar relaciones
// muchos-a-muchos y calcular identificadores/nombres deterministas para la
// clase asociativa que las acompaña en el canvas.
//
// El nombre/id se deriva por orden alfabético de nombre/id de clase. El id de
// la clase incluye además el id de la relación original, y el del conector
// punteado sale del id de esa relación, para conservar paralelas y asociaciones
// reflexivas.

export function isManyMultiplicity(label: string | undefined | null): boolean {
  return !!label && label.includes('*');
}

export function isManyToManyLabels(labels: Array<string | undefined | null> | undefined): boolean {
  if (!labels || labels.length < 2) return false;
  return isManyMultiplicity(labels[0]) && isManyMultiplicity(labels[1]);
}

export function junctionElementId(classIdA: string, classIdB: string, relationshipId: string): string {
  const [first, second] = [classIdA, classIdB].sort();
  return `junction:${first}:${second}:${relationshipId}`;
}

export function junctionLegId(
  originClassId: string,
  junctionId: string,
  role?: 'source' | 'target'
): string {
  if (role) return `junction-link:${junctionId}:${role}`;
  return `junction-link:${originClassId}:${junctionId}`;
}

export function junctionDisplayName(nameA: string, nameB: string): string {
  const [first, second] = [nameA || '', nameB || ''].sort((a, b) => a.localeCompare(b));
  return `${first}_${second}`;
}

/** Id del conector punteado que une la clase asociativa generada con el medio de su asociación M:N. */
export function associationClassLinkId(manyToManyLinkId: string): string {
  return `assoc-class-link:${manyToManyLinkId}`;
}
