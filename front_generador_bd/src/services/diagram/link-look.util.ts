/**
 * Cómo se dibuja una relación entre dos clases: por qué lado sale de cada una, por dónde pasa y dónde van las multiplicidades.
 *
 * Todo es geometría pura (sin JointJS) para poder probarla. `diagram.service` la conecta al lienzo con `umlSideAnchor` (el ancla de cada
 * extremo) y con las etiquetas que crea cada relación.
 */

export type Rect = { x: number; y: number; width: number; height: number };
export type Point = { x: number; y: number };
export type Side = 'top' | 'right' | 'bottom' | 'left';

/** Margen para que la línea no salga pegada a una esquina de la clase. */
const CORNER_MARGIN = 10;
/** Separación entre dos relaciones que unen las mismas clases, para que no se dibujen una encima de la otra. */
const LANE_STEP = 26;

const rightOf = (r: Rect) => r.x + r.width;
const bottomOf = (r: Rect) => r.y + r.height;
const centerX = (r: Rect) => r.x + r.width / 2;
const centerY = (r: Rect) => r.y + r.height / 2;

/** Cuánto se solapan dos intervalos (negativo si hay un hueco entre ellos). */
const overlap = (aStart: number, aEnd: number, bStart: number, bEnd: number) => Math.min(aEnd, bEnd) - Math.max(aStart, bStart);

/**
 * El lado de `own` por el que debe salir una relación hacia `other`: el que mira a la otra clase.
 * - Una al lado de la otra (se solapan en vertical): lados izquierdo y derecho.
 * - Una encima de la otra (se solapan en horizontal): lados de arriba y de abajo.
 * - En diagonal: el eje donde hay más distancia entre las clases.
 * Se recalcula cada vez que se mueve una clase, así que la relación siempre toma el camino más corto.
 */
export function facingSide(own: Rect, other: Rect): Side {
  const horizontalOverlap = overlap(own.x, rightOf(own), other.x, rightOf(other));
  const verticalOverlap = overlap(own.y, bottomOf(own), other.y, bottomOf(other));
  const dx = centerX(other) - centerX(own);
  const dy = centerY(other) - centerY(own);

  const horizontal = (): Side => (dx >= 0 ? 'right' : 'left');
  const vertical = (): Side => (dy >= 0 ? 'bottom' : 'top');

  if (horizontalOverlap > 0 && verticalOverlap > 0) {
    // Clases encimadas: se elige el eje en el que están más lejos los centros.
    return Math.abs(dx) / Math.max(own.width, 1) >= Math.abs(dy) / Math.max(own.height, 1) ? horizontal() : vertical();
  }
  if (verticalOverlap > 0) return horizontal();
  if (horizontalOverlap > 0) return vertical();
  const gapX = Math.max(other.x - rightOf(own), own.x - rightOf(other));
  const gapY = Math.max(other.y - bottomOf(own), own.y - bottomOf(other));
  return gapX >= gapY ? horizontal() : vertical();
}

/** Desplazamiento, a lo largo del lado, de la relación número `lane` de `lanes` que unen las mismas dos clases. */
export function laneOffset(lane: number, lanes: number): number {
  return lanes > 1 ? (lane - (lanes - 1) / 2) * LANE_STEP : 0;
}

/**
 * El punto del borde de `own` donde empieza (o termina) una relación hacia `other`.
 * Si las clases se solapan en el eje del lado, el punto cae en el medio de esa zona común: así las dos puntas de la relación quedan
 * enfrentadas y la línea sale recta en vez de hacer un escalón. Con varias relaciones entre las mismas clases se reparten a lo largo del lado.
 */
export function sideAnchor(own: Rect, other: Rect, lane = 0, lanes = 1): Point {
  const side = facingSide(own, other);
  const shift = laneOffset(lane, lanes);
  const clamp = (value: number, from: number, to: number) => Math.min(Math.max(value, from + CORNER_MARGIN), Math.max(from + CORNER_MARGIN, to - CORNER_MARGIN));

  if (side === 'left' || side === 'right') {
    const common = overlap(own.y, bottomOf(own), other.y, bottomOf(other));
    const base = common > 0 ? Math.max(own.y, other.y) + common / 2 : centerY(own);
    return { x: side === 'right' ? rightOf(own) : own.x, y: clamp(base + shift, own.y, bottomOf(own)) };
  }
  const common = overlap(own.x, rightOf(own), other.x, rightOf(other));
  const base = common > 0 ? Math.max(own.x, other.x) + common / 2 : centerX(own);
  return { x: clamp(base + shift, own.x, rightOf(own)), y: side === 'bottom' ? bottomOf(own) : own.y };
}

/** Lugar de una relación entre las que unen las mismas dos clases (en orden estable) y cuántas son. */
export function laneOf<T>(links: T[], mine: T, idOf: (link: T) => string): { lane: number; lanes: number } {
  const ordered = [...links].sort((a, b) => idOf(a).localeCompare(idOf(b)));
  const index = ordered.indexOf(mine);
  return { lane: index < 0 ? 0 : index, lanes: Math.max(ordered.length, 1) };
}

/**
 * El ancla de un extremo de relación para JointJS (`defaultAnchor` del lienzo). Con una sola clase en juego (relación recursiva, o un
 * extremo que aún no está conectado) deja el ancla en el centro, como siempre.
 */
export function umlSideAnchor(endView: any, _magnet: unknown, _reference: unknown, _args: unknown, endType: 'source' | 'target', linkView: any): any {
  const own = endView?.model;
  const bbox = own?.getBBox?.();
  const center = bbox?.center?.();
  const link = linkView?.model;
  const other = link && (endType === 'source' ? link.getTargetElement?.() : link.getSourceElement?.());
  if (!own || !bbox || !center || !other || other === own) return center;

  const pair = (own.graph?.getConnectedLinks?.(own) ?? []).filter((candidate: any) => {
    if ((candidate.get?.('relationType') ?? 'association') === 'association-class') return false;
    const a = candidate.getSourceElement?.();
    const b = candidate.getTargetElement?.();
    return (a === own && b === other) || (a === other && b === own);
  });
  const { lane, lanes } = laneOf(pair, link, (candidate: any) => String(candidate.id));
  const point = sideAnchor(toRect(bbox), toRect(other.getBBox()), lane, lanes);
  center.x = point.x;
  center.y = point.y;
  return center;
}

const toRect = (bbox: any): Rect => ({ x: bbox.x, y: bbox.y, width: bbox.width, height: bbox.height });

// ---- ruteo ortogonal ---------------------------------------------------------------------------------------------------

/** Tramo recto mínimo al salir de una clase (cabe la multiplicidad) y distancia a la que se rodea una clase cuando hay que dar la vuelta. */
export const ROUTE_PADDING = 30;
/** Un tramo más corto que esto no se dibuja: se prefiere otro camino. */
const MIN_LEG = 24;

const NORMAL: Record<Side, Point> = { right: { x: 1, y: 0 }, left: { x: -1, y: 0 }, bottom: { x: 0, y: 1 }, top: { x: 0, y: -1 } };
const OPPOSITE: Record<Side, Side> = { right: 'left', left: 'right', top: 'bottom', bottom: 'top' };
const isHorizontal = (side: Side) => side === 'left' || side === 'right';
const same = (a: Point, b: Point) => Math.abs(a.x - b.x) < 0.5 && Math.abs(a.y - b.y) < 0.5;
/** Cuánto avanza `to` respecto de `from` en la dirección de salida del lado `side`. */
const ahead = (from: Point, to: Point, side: Side) => (to.x - from.x) * NORMAL[side].x + (to.y - from.y) * NORMAL[side].y;

/** Quita los puntos repetidos y los que están en medio de una recta, para que solo queden las esquinas. */
function corners(points: Point[]): Point[] {
  const kept: Point[] = [];
  for (const point of points) {
    if (kept.length && same(kept[kept.length - 1], point)) continue;
    kept.push(point);
  }
  return kept.filter((point, index) => {
    if (index === 0 || index === kept.length - 1) return true;
    const before = kept[index - 1];
    const after = kept[index + 1];
    const straightX = Math.abs(before.x - point.x) < 0.5 && Math.abs(point.x - after.x) < 0.5;
    const straightY = Math.abs(before.y - point.y) < 0.5 && Math.abs(point.y - after.y) < 0.5;
    return !(straightX || straightY);
  });
}

/**
 * Las esquinas del camino ortogonal (solo líneas horizontales y verticales) entre dos puntos de borde, sin contar los extremos.
 * Cada extremo sale perpendicular a su lado, y el camino tiene las menos esquinas posibles:
 * - lados enfrentados: recta, o una «Z» que dobla a mitad de camino;
 * - lados que forman una esquina: una «L»;
 * - mismo lado: una «C» que rodea las dos clases;
 * - si el camino directo no cabe (clases encimadas o una detrás de otra), da la vuelta dejando `padding` de espacio.
 */
export function orthogonalRoute(from: Point, fromSide: Side, to: Point, toSide: Side, fromRect: Rect, toRect: Rect, padding = ROUTE_PADDING): Point[] {
  const out = (point: Point, side: Side, distance: number): Point => ({ x: point.x + NORMAL[side].x * distance, y: point.y + NORMAL[side].y * distance });
  const horizontalFrom = isHorizontal(fromSide);
  const horizontalTo = isHorizontal(toSide);

  if (horizontalFrom === horizontalTo) {
    if (toSide === OPPOSITE[fromSide] && ahead(from, to, fromSide) >= 2 * MIN_LEG) {
      // Enfrentados y con sitio entre las dos clases: recta o «Z».
      if (horizontalFrom) {
        if (Math.abs(from.y - to.y) < 1) return [];
        const middle = (from.x + to.x) / 2;
        return corners([{ x: middle, y: from.y }, { x: middle, y: to.y }]);
      }
      if (Math.abs(from.x - to.x) < 1) return [];
      const middle = (from.y + to.y) / 2;
      return corners([{ x: from.x, y: middle }, { x: to.x, y: middle }]);
    }
    if (toSide === fromSide) {
      // Mismo lado: una «C» más allá de las dos clases.
      if (horizontalFrom) {
        const x = fromSide === 'right' ? Math.max(from.x, to.x) + padding : Math.min(from.x, to.x) - padding;
        return corners([{ x, y: from.y }, { x, y: to.y }]);
      }
      const y = fromSide === 'bottom' ? Math.max(from.y, to.y) + padding : Math.min(from.y, to.y) - padding;
      return corners([{ x: from.x, y }, { x: to.x, y }]);
    }
    // Enfrentados pero una clase detrás de la otra: se sale de las dos y se da la vuelta por arriba o por abajo (o por los lados).
    const start = out(from, fromSide, padding);
    const end = out(to, toSide, padding);
    if (horizontalFrom) {
      const above = Math.min(fromRect.y, toRect.y) - padding;
      const below = Math.max(fromRect.y + fromRect.height, toRect.y + toRect.height) + padding;
      const y = Math.abs(from.y - above) + Math.abs(to.y - above) <= Math.abs(from.y - below) + Math.abs(to.y - below) ? above : below;
      return corners([start, { x: start.x, y }, { x: end.x, y }, end]);
    }
    const before = Math.min(fromRect.x, toRect.x) - padding;
    const after = Math.max(fromRect.x + fromRect.width, toRect.x + toRect.width) + padding;
    const x = Math.abs(from.x - before) + Math.abs(to.x - before) <= Math.abs(from.x - after) + Math.abs(to.x - after) ? before : after;
    return corners([start, { x, y: start.y }, { x, y: end.y }, end]);
  }

  // Lados que forman una esquina: una «L» si la esquina queda fuera de las dos clases.
  const corner: Point = horizontalFrom ? { x: to.x, y: from.y } : { x: from.x, y: to.y };
  if (ahead(from, corner, fromSide) >= MIN_LEG && ahead(to, corner, toSide) >= MIN_LEG) return [corner];

  // No cabe: se sale de las dos con un tramo recto y se unen con un escalón.
  const start = out(from, fromSide, padding);
  const end = out(to, toSide, padding);
  const bend: Point = horizontalFrom ? { x: start.x, y: end.y } : { x: end.x, y: start.y };
  return corners([start, bend, end]);
}

/**
 * El ruteo de las relaciones para JointJS (`defaultRouter` del lienzo): usa los mismos lados que `umlSideAnchor`, así que la línea sale
 * siempre por el lado que mira a la otra clase. Sin dos clases distintas en los extremos no dibuja esquinas. Una línea que la persona movió
 * a mano (con vértices) se dibuja por ellos.
 */
export function umlRouter(this: any, vertices: unknown): Point[] {
  // Si la persona movió la línea a mano (hay vértices guardados), se respeta tal cual; doble clic en la línea la devuelve al trazado automático.
  if (Array.isArray(vertices) && vertices.length > 0) return vertices.map((vertex: Point) => ({ x: vertex.x, y: vertex.y }));
  const linkView = this;
  const link = linkView?.model;
  const source = link?.getSourceElement?.();
  const target = link?.getTargetElement?.();
  const from = linkView?.sourceAnchor;
  const to = linkView?.targetAnchor;
  if (!source || !target || source === target || !from || !to) return [];
  const sourceRect = toRect(source.getBBox());
  const targetRect = toRect(target.getBBox());
  return orthogonalRoute({ x: from.x, y: from.y }, facingSide(sourceRect, targetRect), { x: to.x, y: to.y }, facingSide(targetRect, sourceRect), sourceRect, targetRect);
}

// ---- multiplicidades -----------------------------------------------------------------------------------------------

/** Qué tan lejos del extremo (a lo largo de la línea) y de qué lado de ella va el texto de la multiplicidad. */
export const LABEL_DISTANCE = 24;
export const LABEL_OFFSET = -14;

/**
 * La multiplicidad de un extremo. El texto va centrado en su punto, a un lado de la línea y lejos del borde de la clase: así no queda tapado
 * por la clase ni encima de la línea, sin importar hacia dónde sale la relación.
 */
export function endLabel(text: string, end: 'source' | 'target'): any {
  return {
    position: { distance: end === 'source' ? LABEL_DISTANCE : -LABEL_DISTANCE, offset: LABEL_OFFSET },
    attrs: { text: { text, fill: '#333', fontSize: 12, textAnchor: 'middle', textVerticalAnchor: 'middle' } },
    markup: [{ tagName: 'text', selector: 'text' }]
  };
}

/** Las dos multiplicidades de una relación nueva. */
export function defaultLabels(sourceText = '0..1', targetText = '1..*'): any[] {
  return [endLabel(sourceText, 'source'), endLabel(targetText, 'target')];
}

/**
 * ¿Es una multiplicidad hecha con el formato anterior (texto pegado a la clase, que la tapaba) y que nadie movió? Solo esas se actualizan:
 * si alguien la acomodó a mano se respeta.
 */
export function isOldDefaultLabel(label: any): boolean {
  const position = label?.position;
  const old = position && (position.distance === 20 || position.distance === -20) && position.offset === -10;
  return !!old && !label?.attrs?.text?.textAnchor;
}

/** La misma multiplicidad en el formato nuevo (conserva el texto y el extremo). */
export function upgradeLabel(label: any): any {
  const text = label?.attrs?.text?.text ?? '';
  return endLabel(text, (label?.position?.distance ?? 20) < 0 ? 'target' : 'source');
}
