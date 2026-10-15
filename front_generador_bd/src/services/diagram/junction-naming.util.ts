// Utilidades puras (sin dependencia de JointJS) para detectar relaciones
// muchos-a-muchos y calcular identificadores/nombres deterministas para la
// entidad intermedia visual que las representa en el canvas.
//
// El nombre/id se deriva siempre por orden alfabético de nombre/id de clase,
// nunca por cuál de las dos clases es "source" o "target" en la relación, para
// que invertir el sentido en que se dibujó la asociación no cambie el resultado.

export function isManyMultiplicity(label: string | undefined | null): boolean {
  return !!label && label.includes('*');
}

export function isManyToManyLabels(labels: Array<string | undefined | null> | undefined): boolean {
  if (!labels || labels.length < 2) return false;
  return isManyMultiplicity(labels[0]) && isManyMultiplicity(labels[1]);
}

export function junctionElementId(classIdA: string, classIdB: string): string {
  const [first, second] = [classIdA, classIdB].sort();
  return `junction:${first}:${second}`;
}

export function junctionLegId(originClassId: string, junctionId: string): string {
  return `junction-link:${originClassId}:${junctionId}`;
}

export function junctionDisplayName(nameA: string, nameB: string): string {
  const [first, second] = [nameA || '', nameB || ''].sort((a, b) => a.localeCompare(b));
  return `${first}_${second}`;
}
