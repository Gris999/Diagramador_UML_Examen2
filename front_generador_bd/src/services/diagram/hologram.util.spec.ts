import { Ghost, GHOST_WIDTH, planHologram, renderHologram } from './hologram.util';

const classes = [
  { id: 'c1', name: 'Cliente', position: { x: 100, y: 100 }, size: { width: 180, height: 120 } },
  { id: 'c2', name: 'Pedido', position: { x: 400, y: 300 }, size: { width: 160, height: 100 } }
];
const uml = { classes };

describe('planHologram', () => {
  it('draws nothing when there is nothing proposed or the proposal is not understood', () => {
    expect(planHologram(undefined, uml)).toEqual([]);
    expect(planHologram('texto', uml)).toEqual([]);
    expect(planHologram({}, uml)).toEqual([]);
    expect(planHologram({ classes: [null, 3, 'x'] }, uml)).toEqual([]);
  });

  it('puts a new class to the right of the diagram with its attributes and methods', () => {
    const [ghost] = planHologram({ classes: [{ name: 'Factura', attributes: [{ name: 'total', type: 'float' }], methods: [{ name: 'emitir' }] }] }, uml);

    expect(ghost.kind).toBe('new');
    const box = ghost as Extract<Ghost, { kind: 'new' }>;
    expect(box.title).toBe('Factura');
    expect(box.lines).toEqual(['+ total: float', '+ emitir()']);
    expect(box.x).toBeGreaterThan(400 + 160); // a la derecha de la clase más a la derecha
    expect(box.y).toBe(100); // a la altura de la clase más alta
    expect(box.width).toBe(GHOST_WIDTH);
  });

  it('stacks several new classes without overlapping them', () => {
    const plan = planHologram({ classes: [{ name: 'A', attributes: [{ name: 'x' }] }, { name: 'B', attributes: [{ name: 'y' }] }] }, uml) as Extract<Ghost, { kind: 'new' }>[];

    expect(plan.length).toBe(2);
    expect(plan[1].y).toBeGreaterThanOrEqual(plan[0].y + plan[0].height);
    expect(plan[1].x).toBe(plan[0].x);
  });

  it('starts a new column when the first one is full', () => {
    const many = Array.from({ length: 6 }, (_, n) => ({ name: `Clase${n}`, attributes: Array.from({ length: 7 }, (_, m) => ({ name: `a${m}` })) }));

    const plan = planHologram({ classes: many }, uml) as Extract<Ghost, { kind: 'new' }>[];

    expect(new Set(plan.map(ghost => ghost.x)).size).toBeGreaterThan(1);
  });

  it('shows what is added to a class that already exists under that class, found by id or by name', () => {
    const byId = planHologram({ classes: [{ id: 'c1', name: 'Cliente', attributes: [{ name: 'correo', type: 'String' }] }] }, uml)[0] as Extract<Ghost, { kind: 'edit' }>;
    const byName = planHologram({ classes: [{ name: 'cliente', attributes: [{ name: 'correo' }] }] }, uml)[0] as Extract<Ghost, { kind: 'edit' }>;

    expect(byId.kind).toBe('edit');
    expect(byId.lines).toEqual(['+ correo: String']);
    expect(byId.x).toBe(100);
    expect(byId.y).toBeGreaterThanOrEqual(100 + 120); // debajo de la clase
    expect(byName.kind).toBe('edit');
  });

  it('says what is removed and what is renamed inside a class', () => {
    const [ghost] = planHologram({ classes: [{ id: 'c1', name: 'Cliente', attributes: [{ name: 'edad', eliminar: true }, { name: 'nombreCompleto', originalName: 'nombre' }] }] }, uml) as Extract<Ghost, { kind: 'edit' }>[];

    expect(ghost.lines).toEqual(['− edad', 'nombre → nombreCompleto']);
  });

  it('draws nothing for an existing class whose edit has nothing to show, and a note when it only says it changed', () => {
    expect(planHologram({ classes: [{ id: 'c1', name: 'Cliente' }] }, uml)).toEqual([]);
    const [ghost] = planHologram({ classes: [{ id: 'c1', name: 'Cliente', editado: true }] }, uml) as Extract<Ghost, { kind: 'edit' }>[];
    expect(ghost.lines).toEqual(['(cambia)']);
  });

  it('surrounds the class that would be deleted, and ignores deleting what does not exist', () => {
    const plan = planHologram({ classes: [{ id: 'c2', name: 'Pedido', eliminar: true }, { name: 'Fantasma', eliminar: true }] }, uml);

    expect(plan.length).toBe(1);
    expect(plan[0]).toEqual(jasmine.objectContaining({ kind: 'remove', title: 'Pedido', x: 400, y: 300, width: 160, height: 100 }));
  });

  it('joins the two ends of a new relationship, whether they are existing or new classes', () => {
    const plan = planHologram({
      classes: [{ id: 'n1', name: 'Factura', attributes: [{ name: 'total' }] }],
      relationships: [{ sourceId: 'c1', targetId: 'n1', type: 'association' }, { sourceId: 'Pedido', targetId: 'Cliente', type: 'composition' }]
    }, uml);

    const links = plan.filter(ghost => ghost.kind === 'link') as Extract<Ghost, { kind: 'link' }>[];
    expect(links.length).toBe(2);
    expect(links[0].label).toBe('asociación');
    expect(links[0].from).toEqual({ x: 190, y: 160 }); // el centro de Cliente
    expect(links[1].label).toBe('composición');
    expect(links[1].from).toEqual({ x: 480, y: 350 }); // el centro de Pedido
  });

  it('skips a relationship whose end it cannot find', () => {
    expect(planHologram({ relationships: [{ sourceId: 'c1', targetId: 'no-existe', type: 'association' }] }, uml)).toEqual([]);
  });

  it('works on an empty diagram', () => {
    const [ghost] = planHologram({ classes: [{ name: 'Libro' }] }, { classes: [] }) as Extract<Ghost, { kind: 'new' }>[];

    expect(ghost.kind).toBe('new');
    expect(ghost.x).toBeGreaterThanOrEqual(0);
  });

  it('shortens a very long list of members', () => {
    const [ghost] = planHologram({ classes: [{ name: 'Grande', attributes: Array.from({ length: 20 }, (_, n) => ({ name: `a${n}` })) }] }, uml) as Extract<Ghost, { kind: 'new' }>[];

    expect(ghost.lines.length).toBe(8);
    expect(ghost.lines[7]).toContain('más');
  });
});

describe('renderHologram', () => {
  it('builds an SVG layer that ignores the pointer, with one group per drawing', () => {
    const plan = planHologram({
      classes: [{ name: 'Factura', attributes: [{ name: 'total' }] }, { id: 'c2', name: 'Pedido', eliminar: true }],
      relationships: [{ sourceId: 'c1', targetId: 'Factura', type: 'association' }]
    }, uml);

    const layer = renderHologram(plan);

    expect(layer.getAttribute('class')).toBe('hologram');
    expect(layer.getAttribute('pointer-events')).toBe('none');
    expect(layer.querySelectorAll('.hologram-new').length).toBe(1);
    expect(layer.querySelectorAll('.hologram-remove').length).toBe(1);
    expect(layer.querySelectorAll('.hologram-link').length).toBe(1);
    expect(layer.textContent).toContain('Factura');
    expect(layer.textContent).toContain('+ total');
    expect(layer.textContent).toContain('(se elimina)');
  });

  it('shows names as text, never as markup', () => {
    const layer = renderHologram(planHologram({ classes: [{ name: '<img src=x onerror=alert(1)>' }] }, uml));

    expect(layer.querySelector('img')).toBeNull();
    expect(layer.textContent).toContain('<img src=x onerror=alert(1)>');
  });
});
