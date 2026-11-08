/** Primera letra del nombre en mayúscula, para el círculo de la persona. Sin nombre se usa «?». */
export function avatarInitial(name: string | undefined | null): string {
  const first = (name ?? '').trim().charAt(0);
  return first ? first.toLocaleUpperCase('es') : '?';
}

/**
 * Color propio de cada persona, siempre el mismo para el mismo nombre (se saca del texto, no se guarda). Saturación y claridad fijas:
 * la letra blanca se lee bien sobre cualquiera de los tonos.
 */
export function avatarColor(name: string | undefined | null): string {
  const text = (name ?? '').trim().toLocaleLowerCase('es');
  let hash = 0;
  for (let index = 0; index < text.length; index++) {
    hash = (hash * 31 + text.charCodeAt(index)) >>> 0;
  }
  return `hsl(${hash % 360} 52% 38%)`;
}
