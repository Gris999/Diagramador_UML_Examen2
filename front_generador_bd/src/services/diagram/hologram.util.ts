/**
 * La vista previa («holograma») de lo que la IA haría: antes de que la persona diga que sí, el cambio propuesto se dibuja sobre el diagrama en trazo
 * punteado y sin tocarlo (no entra al grafo, así que no se sincroniza, ni se guarda, ni se exporta). Las clases nuevas aparecen a la derecha del
 * diagrama, lo que se agrega a una clase existente aparece bajo ella, lo que se elimina se rodea en rojo y las relaciones nuevas se dibujan unidas.
 *
 * `planHologram` es geometría pura (se prueba sin navegador); `renderHologram` arma el SVG que `DiagramService` pone sobre el lienzo.
 */

export type Point = { x: number; y: number };
type Rect = { x: number; y: number; width: number; height: number };

/** Lo que se necesita de una clase del diagrama (el JSON que ya exporta `DiagramExportService`). */
export type ExistingClass = { id?: string; name?: string; position?: Point; size?: { width: number; height: number } };

export type Ghost =
  | ({ kind: 'new'; title: string; lines: string[] } & Rect)
  | ({ kind: 'edit'; title: string; lines: string[] } & Rect)
  | ({ kind: 'remove'; title: string } & Rect)
  | { kind: 'link'; from: Point; to: Point; label: string };

export const GHOST_WIDTH = 190;
const HEADER_H = 26;
const LINE_H = 15;
const GAP = 30;
const MARGIN = 80;
const MAX_LINES = 8;
const COLUMN_HEIGHT = 520;

const RELATION_LABEL: Record<string, string> = {
  association: 'asociación',
  aggregation: 'agregación',
  composition: 'composición',
  generalization: 'herencia',
  inheritance: 'herencia',
  dependency: 'dependencia',
  realization: 'realización'
};

const isObject = (value: unknown): value is Record<string, any> => typeof value === 'object' && value !== null;
const text = (value: unknown): string => (typeof value === 'string' ? value.trim() : '');
const keyOf = (value: unknown): string => text(value).toLowerCase();

function memberLines(item: Record<string, any>): string[] {
  const lines: string[] = [];
  const add = (members: unknown, call: boolean) => {
    for (const member of Array.isArray(members) ? members : []) {
      if (!isObject(member) || !text(member['name'])) continue;
      const name = text(member['name']);
      if (member['eliminar'] === true) lines.push(`− ${name}`);
      else if (text(member['originalName'])) lines.push(`${text(member['originalName'])} → ${name}`);
      else lines.push(call ? `+ ${name}()` : `+ ${name}${text(member['type']) ? ': ' + text(member['type']) : ''}`);
    }
  };
  add(item['attributes'], false);
  add(item['methods'], true);
  return lines.length > MAX_LINES ? [...lines.slice(0, MAX_LINES - 1), `… y ${lines.length - MAX_LINES + 1} más`] : lines;
}

const heightFor = (lines: string[]) => HEADER_H + Math.max(lines.length, 1) * LINE_H + 8;
const center = (rect: Rect): Point => ({ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 });

/** Qué dibujar para el cambio `changes` (el mismo que se aplicaría con el «sí») sobre el diagrama `uml`. */
export function planHologram(changes: unknown, uml: { classes?: ExistingClass[] } | null | undefined): Ghost[] {
  if (!isObject(changes)) return [];
  const classes = Array.isArray(changes['classes']) ? changes['classes'] : [];
  const relationships = Array.isArray(changes['relationships']) ? changes['relationships'] : [];

  const existing: { id: string; name: string; rect: Rect }[] = [];
  for (const item of uml?.classes ?? []) {
    if (!item?.position || !item.size) continue;
    existing.push({ id: text(item.id), name: text(item.name), rect: { x: item.position.x, y: item.position.y, width: item.size.width, height: item.size.height } });
  }
  const find = (id: unknown, name: unknown) =>
    existing.find(c => (text(id) && c.id === text(id)) || (keyOf(name) && keyOf(c.name) === keyOf(name)));

  const rects = new Map<string, Rect>();
  for (const c of existing) {
    if (c.id) rects.set(c.id, c.rect);
    if (c.name) rects.set(keyOf(c.name), c.rect);
  }

  const ghosts: Ghost[] = [];
  const right = existing.length ? Math.max(...existing.map(c => c.rect.x + c.rect.width)) : -MARGIN + 40;
  const top = existing.length ? Math.min(...existing.map(c => c.rect.y)) : 40;
  let column = 0;
  let cursorY = top;

  for (const item of classes) {
    if (!isObject(item)) continue;
    const name = text(item['name']) || '(sin nombre)';
    const current = find(item['id'], item['name']);

    if (item['eliminar'] === true) {
      if (current) ghosts.push({ kind: 'remove', title: name, ...current.rect });
      continue;
    }

    const lines = memberLines(item);
    if (current) {
      // Una clase que ya existe: lo que cambia aparece bajo ella.
      const shown = lines.length ? lines : item['editado'] === true ? ['(cambia)'] : [];
      if (shown.length) {
        ghosts.push({
          kind: 'edit',
          title: name,
          lines: shown,
          x: current.rect.x,
          y: current.rect.y + current.rect.height + 10,
          width: Math.max(current.rect.width, 150),
          height: heightFor(shown)
        });
      }
      continue;
    }

    // Una clase nueva: a la derecha del diagrama, en columnas.
    const height = heightFor(lines);
    if (cursorY - top + height > COLUMN_HEIGHT && cursorY > top) {
      column += 1;
      cursorY = top;
    }
    const rect: Rect = { x: right + MARGIN + column * (GHOST_WIDTH + GAP), y: cursorY, width: GHOST_WIDTH, height };
    cursorY += height + GAP;
    ghosts.push({ kind: 'new', title: name, lines, ...rect });
    if (text(item['id'])) rects.set(text(item['id']), rect);
    rects.set(keyOf(name), rect);
  }

  for (const rel of relationships) {
    if (!isObject(rel) || rel['eliminar'] === true) continue;
    const from = rects.get(text(rel['sourceId'])) ?? rects.get(keyOf(rel['sourceId']));
    const to = rects.get(text(rel['targetId'])) ?? rects.get(keyOf(rel['targetId']));
    if (!from || !to || from === to) continue;
    ghosts.push({ kind: 'link', from: center(from), to: center(to), label: RELATION_LABEL[keyOf(rel['type'])] ?? text(rel['type']) });
  }
  return ghosts;
}

const COLORS = { new: '#a855f7', edit: '#f59e0b', remove: '#ef4444', link: '#a855f7' } as const;
const SYMBOL = { new: '＋ ', edit: '✎ ', remove: '✕ ' } as const;

/** El SVG de la vista previa; va dentro del `viewport` del lienzo, así sigue al zoom y al desplazamiento. */
export function renderHologram(ghosts: Ghost[], doc: Document = document): SVGGElement {
  const ns = 'http://www.w3.org/2000/svg';
  const make = <K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number>, content?: string): SVGElementTagNameMap[K] => {
    const node = doc.createElementNS(ns, tag);
    for (const [name, value] of Object.entries(attrs)) node.setAttribute(name, String(value));
    if (content !== undefined) node.textContent = content;
    return node;
  };

  const layer = make('g', { class: 'hologram', 'pointer-events': 'none' });
  for (const ghost of ghosts) {
    const group = make('g', { class: `hologram-${ghost.kind}` });
    group.appendChild(make('animate', { attributeName: 'opacity', values: '0.6;1;0.6', dur: '2.6s', repeatCount: 'indefinite' }));
    const color = COLORS[ghost.kind];

    if (ghost.kind === 'link') {
      group.appendChild(make('line', { x1: ghost.from.x, y1: ghost.from.y, x2: ghost.to.x, y2: ghost.to.y, stroke: color, 'stroke-width': 2, 'stroke-dasharray': '7 5' }));
      group.appendChild(make('text', {
        x: (ghost.from.x + ghost.to.x) / 2,
        y: (ghost.from.y + ghost.to.y) / 2 - 6,
        fill: color,
        'font-size': 11,
        'text-anchor': 'middle'
      }, ghost.label));
    } else {
      group.appendChild(make('rect', {
        x: ghost.x,
        y: ghost.y,
        width: ghost.width,
        height: ghost.height,
        rx: 4,
        fill: ghost.kind === 'remove' ? 'none' : color,
        'fill-opacity': 0.14,
        stroke: color,
        'stroke-width': 1.8,
        'stroke-dasharray': '7 4'
      }));
      group.appendChild(make('text', { x: ghost.x + 8, y: ghost.kind === 'remove' ? ghost.y - 6 : ghost.y + 17, fill: color, 'font-size': 12, 'font-weight': 700 },
        SYMBOL[ghost.kind] + ghost.title + (ghost.kind === 'remove' ? ' (se elimina)' : '')));
      if (ghost.kind !== 'remove') {
        ghost.lines.forEach((line, index) => {
          group.appendChild(make('text', { x: ghost.x + 10, y: ghost.y + HEADER_H + (index + 1) * LINE_H - 4, fill: color, 'font-size': 11 }, line));
        });
      }
    }
    layer.appendChild(group);
  }
  return layer;
}
