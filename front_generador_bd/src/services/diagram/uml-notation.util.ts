/**
 * Notación UML 2.5 de una clase: su tipo (clase, clase abstracta, interfaz, enumeración) y la visibilidad de cada atributo y método.
 *
 * Los atributos y métodos de una clase se guardan como texto, una línea por miembro («+ nombre: String», «- calcular(x): int»). Aquí se
 * convierten en datos (y al revés) en un solo lugar, para que el lienzo, el respaldo, la colaboración, XMI y los generadores lean lo mismo.
 */

export type ClassKind = 'class' | 'abstract' | 'interface' | 'enumeration';
export type Visibility = '+' | '-' | '#' | '~';

export const CLASS_KINDS: readonly ClassKind[] = ['class', 'abstract', 'interface', 'enumeration'];
export const VISIBILITIES: readonly Visibility[] = ['+', '-', '#', '~'];

export const isClassKind = (value: unknown): value is ClassKind => typeof value === 'string' && (CLASS_KINDS as readonly string[]).includes(value);

/** El tipo de una clase; lo que no se reconoce es una clase común. */
export const kindOf = (value: unknown): ClassKind => (isClassKind(value) ? value : 'class');

/** El estereotipo que se dibuja sobre el nombre (vacío para una clase común o abstracta: la abstracta va con el nombre en cursiva). */
export const stereotypeOf = (kind: unknown): string => {
  const k = kindOf(kind);
  return k === 'interface' ? '«interface»' : k === 'enumeration' ? '«enumeration»' : '';
};

/** El texto que se ve en el compartimento del nombre: el estereotipo en su propia línea y debajo el nombre. */
export const nameDisplay = (name: string, kind: unknown): string => {
  const stereotype = stereotypeOf(kind);
  return stereotype ? `${stereotype}\n${name}` : name;
};

/** Las clases que no son tablas ni entidades: los generadores de código no las convierten en nada. */
export const isCodeEntity = (kind: unknown): boolean => {
  const k = kindOf(kind);
  return k === 'class' || k === 'abstract';
};

export interface AttributeData {
  name: string;
  type?: string;
  visibility?: Visibility;
}

export interface MethodData {
  name: string;
  parameters?: string;
  returnType?: string;
  visibility?: Visibility;
}

/** Separa el signo de visibilidad que pueda llevar al comienzo una línea («+ nombre» → «+» y «nombre»). */
export function splitVisibility(line: string): { visibility?: Visibility; text: string } {
  const match = /^\s*([+\-#~])\s*(.*)$/.exec(line ?? '');
  return match ? { visibility: match[1] as Visibility, text: match[2] } : { text: (line ?? '').trim() };
}

/** El signo de visibilidad con su espacio («+ »), o nada si no tiene. */
export const visibilityPrefix = (visibility?: Visibility): string => (visibility && VISIBILITIES.includes(visibility) ? `${visibility} ` : '');
const prefix = visibilityPrefix;

/** Una línea de atributo: «+ nombre: tipo». Una literal de enumeración (sin tipo) es solo el nombre. */
export function attributeToLine(attribute: AttributeData): string {
  const type = attribute.type;
  return `${prefix(attribute.visibility)}${attribute.name}${type === undefined || type === null || type === '' ? '' : `: ${type}`}`;
}

export function parseAttributeLine(line: string): Required<Pick<AttributeData, 'name' | 'type'>> & { visibility?: Visibility } {
  const { visibility, text } = splitVisibility(line);
  const [name, ...rest] = text.split(':');
  return { name: (name ?? '').trim(), type: rest.join(':').trim(), ...(visibility ? { visibility } : {}) };
}

/** Una línea de método: «+ calcular(x): int;». */
export function methodToLine(method: MethodData): string {
  const params = method.parameters ? `(${method.parameters})` : '()';
  const returnType = method.returnType ? `: ${method.returnType}` : '';
  return `${prefix(method.visibility)}${method.name}${params}${returnType};`;
}

export function parseMethodLine(line: string): MethodData {
  const { visibility, text } = splitVisibility(line);
  const match = /^(\w+)\(([^)]*)\)(?::\s*(\w+))?/.exec(text);
  if (match) {
    return { name: match[1], parameters: match[2] || '', returnType: match[3] || '', ...(visibility ? { visibility } : {}) };
  }
  return { name: text, ...(visibility ? { visibility } : {}) };
}

/** Los atributos o métodos de una clase, como las líneas de texto que se dibujan (acepta datos o texto ya armado). */
export const attributesToText = (attributes: unknown): string =>
  Array.isArray(attributes) ? attributes.map(a => attributeToLine(a as AttributeData)).join('\n') : ((attributes as string) || '');

export const methodsToText = (methods: unknown): string =>
  Array.isArray(methods) ? methods.map(m => methodToLine(m as MethodData)).join('\n') : ((methods as string) || '');

/**
 * Cuando la IA (o una edición) devuelve los atributos o métodos de una clase sin visibilidad, conserva la que ya tenían en el lienzo:
 * lo que la IA no menciona no se pierde.
 */
export function keepVisibility<T extends { name: string; visibility?: Visibility }>(
  incoming: unknown,
  previousText: string | undefined,
  parseLine: (line: string) => { name: string; visibility?: Visibility }
): unknown {
  if (!Array.isArray(incoming)) return incoming;
  const known = new Map<string, Visibility>();
  for (const line of (previousText || '').split('\n')) {
    const member = parseLine(line);
    if (member.name && member.visibility) known.set(member.name, member.visibility);
  }
  return (incoming as T[]).map(member => (member?.visibility || !known.has(member?.name) ? member : { ...member, visibility: known.get(member.name) }));
}
