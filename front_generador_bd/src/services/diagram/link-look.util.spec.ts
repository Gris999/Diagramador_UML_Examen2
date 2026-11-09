import {
  Point,
  Rect,
  Side,
  defaultLabels,
  endLabel,
  facingSide,
  isOldDefaultLabel,
  laneOf,
  laneOffset,
  orthogonalRoute,
  sideAnchor,
  umlRouter,
  umlSideAnchor,
  upgradeLabel
} from './link-look.util';

const box = (x: number, y: number, width = 180, height = 110): Rect => ({ x, y, width, height });

describe('facingSide', () => {
  it('uses the right and left sides for classes side by side', () => {
    expect(facingSide(box(0, 0), box(400, 20))).toBe('right');
    expect(facingSide(box(400, 20), box(0, 0))).toBe('left');
  });

  it('uses the bottom and top sides for classes one above the other', () => {
    expect(facingSide(box(0, 0), box(30, 300))).toBe('bottom');
    expect(facingSide(box(30, 300), box(0, 0))).toBe('top');
  });

  it('takes the axis with more distance between the classes when they are diagonal', () => {
    expect(facingSide(box(0, 0), box(500, 200))).toBe('right');
    expect(facingSide(box(0, 0), box(200, 500))).toBe('bottom');
    expect(facingSide(box(500, 200), box(0, 0))).toBe('left');
    expect(facingSide(box(200, 500), box(0, 0))).toBe('top');
  });

  it('still answers when the classes overlap (the axis where the centres are farther apart)', () => {
    expect(facingSide(box(0, 0), box(150, 10))).toBe('right');
    expect(facingSide(box(0, 0), box(10, 100))).toBe('bottom');
  });
});

describe('sideAnchor', () => {
  it('leaves from the middle of the side that faces the other class', () => {
    expect(sideAnchor(box(0, 0), box(500, 400))).toEqual({ x: 180, y: 55 });
    // Con x solapada (de 100 a 180) la relación sale por el medio de esa zona común, no por el centro de la clase.
    expect(sideAnchor(box(0, 0), box(100, 500))).toEqual({ x: 140, y: 110 });
    expect(sideAnchor(box(0, 0), box(500, 300))).toEqual({ x: 180, y: 55 });
  });

  it('puts both ends of the line at the middle of the shared band, so a line between classes that overlap is straight', () => {
    const a = box(0, 100);
    const b = box(400, 140);

    const from = sideAnchor(a, b);
    const to = sideAnchor(b, a);

    expect(from.y).toBe(to.y);
    expect(from.x).toBe(180);
    expect(to.x).toBe(400);
  });

  it('is also straight vertically when the classes overlap in x', () => {
    const a = box(100, 0);
    const b = box(160, 300);

    expect(sideAnchor(a, b).x).toBe(sideAnchor(b, a).x);
  });

  it('never goes to a corner of the class', () => {
    const tall = box(0, 0, 180, 40);
    const point = sideAnchor(tall, box(500, 30, 180, 400));

    expect(point.y).toBeGreaterThanOrEqual(10);
    expect(point.y).toBeLessThanOrEqual(30);
  });

  it('spreads several relationships between the same two classes along the side', () => {
    const a = box(0, 0);
    const b = box(500, 0);
    const ys = [0, 1, 2].map(lane => sideAnchor(a, b, lane, 3).y);

    expect(new Set(ys).size).toBe(3);
    expect(ys[1]).toBe(sideAnchor(a, b).y);
    expect(laneOffset(0, 1)).toBe(0);
  });
});

describe('laneOf', () => {
  it('gives each relationship a stable place whatever the order they come in', () => {
    const links = [{ id: 'b' }, { id: 'c' }, { id: 'a' }];

    expect(laneOf(links, links[2], l => l.id)).toEqual({ lane: 0, lanes: 3 });
    expect(laneOf(links, links[0], l => l.id)).toEqual({ lane: 1, lanes: 3 });
    expect(laneOf(links, links[1], l => l.id)).toEqual({ lane: 2, lanes: 3 });
  });
});

describe('orthogonalRoute', () => {
  const along = (from: Point, route: Point[], to: Point) => [from, ...route, to];
  const isOrthogonal = (points: Point[]) =>
    points.every((point, i) => i === 0 || Math.abs(point.x - points[i - 1].x) < 0.5 || Math.abs(point.y - points[i - 1].y) < 0.5);

  function check(a: Rect, b: Rect) {
    const sideA: Side = facingSide(a, b);
    const sideB: Side = facingSide(b, a);
    const from = sideAnchor(a, b);
    const to = sideAnchor(b, a);
    const route = orthogonalRoute(from, sideA, to, sideB, a, b);
    return { from, to, route, points: along(from, route, to), sideA, sideB };
  }

  it('is a straight line when the classes face each other at the same height', () => {
    expect(check(box(0, 100), box(400, 120)).route).toEqual([]);
    expect(check(box(0, 0), box(40, 300)).route).toEqual([]);
  });

  it('bends once, at the middle, when the classes face each other but are not aligned (a Z)', () => {
    const { route, from, to } = check(box(0, 0), box(500, 300));

    expect(route.length).toBe(2);
    expect(route[0].x).toBe((from.x + to.x) / 2);
    expect(route[1].x).toBe(route[0].x);
  });

  it('draws an L when the sides form a corner and there is room', () => {
    const from = { x: 180, y: 55 };
    const to = { x: 600, y: 300 };

    const route = orthogonalRoute(from, 'right', to, 'top', box(0, 0), box(510, 300));

    expect(route).toEqual([{ x: 600, y: 55 }]);
  });

  it('goes around when both ends leave by the same side (a C)', () => {
    const route = orthogonalRoute({ x: 180, y: 55 }, 'right', { x: 180, y: 355 }, 'right', box(0, 0), box(0, 300));

    expect(route.length).toBe(2);
    expect(route[0].x).toBeGreaterThan(180);
    expect(route[0].x).toBe(route[1].x);
  });

  it('gives the way round when one class is behind the other, keeping a straight stretch out of each class', () => {
    const a = box(300, 0);
    const b = box(0, 20);
    const route = orthogonalRoute({ x: 480, y: 55 }, 'right', { x: 0, y: 75 }, 'left', a, b);
    const points = along({ x: 480, y: 55 }, route, { x: 0, y: 75 });

    expect(isOrthogonal(points)).toBeTrue();
    expect(route[0].x).toBeGreaterThan(480);
    expect(route[route.length - 1].x).toBeLessThan(0);
  });

  it('only ever draws horizontal and vertical lines, whatever the layout', () => {
    const others: Rect[] = [];
    for (const x of [-400, -120, 0, 90, 300, 600]) for (const y of [-300, -60, 0, 50, 220, 500]) others.push(box(x, y));
    const origin = box(0, 0);
    for (const other of others) {
      if (other.x === 0 && other.y === 0) continue;
      const { points } = check(origin, other);
      expect(isOrthogonal(points)).withContext(`${other.x},${other.y}`).toBeTrue();
    }
  });

  it('leaves each class perpendicular to its side (the first stretch goes outwards)', () => {
    for (const other of [box(500, 300), box(-500, 300), box(30, 400), box(30, -400)]) {
      const { from, route, to, sideA } = check(box(0, 0), other);
      const next = route[0] ?? to;
      const outward = sideA === 'right' ? next.x - from.x : sideA === 'left' ? from.x - next.x : sideA === 'bottom' ? next.y - from.y : from.y - next.y;
      expect(outward).withContext(`${other.x},${other.y}`).toBeGreaterThan(0);
    }
  });

  it('keeps a stretch long enough for the multiplicity before the first bend', () => {
    const { from, route } = check(box(0, 0), box(300, 200));

    const firstLeg = Math.abs(route[0].x - from.x) + Math.abs(route[0].y - from.y);
    expect(firstLeg).toBeGreaterThanOrEqual(24);
  });
});

describe('the anchor and the router for JointJS', () => {
  function element(bounds: Rect, links: any[] = []) {
    const model: any = {
      graph: { getConnectedLinks: () => links },
      getBBox: () => ({ ...bounds, center: () => ({ x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height / 2 }) })
    };
    return model;
  }
  function link(source: any, target: any, id = 'l1') {
    return { id, get: () => 'association', getSourceElement: () => source, getTargetElement: () => target };
  }

  it('anchors on the side facing the other class', () => {
    const a = element(box(0, 0));
    const b = element(box(500, 0));
    const connection = link(a, b);
    a.graph = { getConnectedLinks: () => [connection] };

    const point = umlSideAnchor({ model: a }, null, null, null, 'source', { model: connection });

    expect(point.x).toBe(180);
  });

  it('leaves the anchor at the centre for a relationship from a class to itself, or with an end that is not a class', () => {
    const a = element(box(0, 0));

    const recursive = umlSideAnchor({ model: a }, null, null, null, 'source', { model: link(a, a) });
    const loose = umlSideAnchor({ model: a }, null, null, null, 'source', { model: link(a, null) });

    expect(recursive).toEqual({ x: 90, y: 55 });
    expect(loose).toEqual({ x: 90, y: 55 });
  });

  it('the router draws nothing when an end is not a class', () => {
    expect(umlRouter.call({ model: link(null, null) } as any, [])).toEqual([]);
  });

  it('the router uses the same sides as the anchors', () => {
    const a = element(box(0, 0));
    const b = element(box(500, 300));
    const connection = link(a, b);
    const view: any = { model: connection, sourceAnchor: { x: 180, y: 55 }, targetAnchor: { x: 500, y: 355 } };

    const route = umlRouter.call(view, []);

    expect(route.length).toBe(2);
  });
});

describe('multiplicity labels', () => {
  it('are centred and away from the border of the class, on the side of each end', () => {
    const [source, target] = defaultLabels('0..1', '1..*');

    expect(source.position.distance).toBeGreaterThanOrEqual(20);
    expect(target.position.distance).toBeLessThanOrEqual(-20);
    expect(source.attrs.text).toEqual(jasmine.objectContaining({ text: '0..1', textAnchor: 'middle', textVerticalAnchor: 'middle' }));
    expect(target.attrs.text.text).toBe('1..*');
  });

  it('keep the shape the editor and the exporters read (attrs.text.text)', () => {
    expect(endLabel('*', 'source').attrs.text.text).toBe('*');
    expect(endLabel('*', 'source').markup).toEqual([{ tagName: 'text', selector: 'text' }]);
  });

  it('recognise the old default position, which the class covered, and upgrade it keeping the text and the end', () => {
    const oldSource = { position: { distance: 20, offset: -10 }, attrs: { text: { text: '1', fill: '#333' } } };
    const oldTarget = { position: { distance: -20, offset: -10 }, attrs: { text: { text: '0..*', fill: '#333' } } };

    expect(isOldDefaultLabel(oldSource)).toBeTrue();
    expect(upgradeLabel(oldSource)).toEqual(endLabel('1', 'source'));
    expect(upgradeLabel(oldTarget)).toEqual(endLabel('0..*', 'target'));
  });

  it('respect a label that someone moved or that already has the new shape', () => {
    expect(isOldDefaultLabel({ position: { distance: 0.4, offset: 12 }, attrs: { text: { text: '1' } } })).toBeFalse();
    expect(isOldDefaultLabel(endLabel('1', 'source'))).toBeFalse();
    expect(isOldDefaultLabel(null)).toBeFalse();
  });
});
