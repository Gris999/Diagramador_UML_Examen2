import { DiagramService } from './diagram.service';

// Mismo patrón de mocks mínimos usado en diagram.service.spec.ts: JointJS real
// no se instancia en estos tests, se sustituye por clases equivalentes con
// solo la superficie que createUmlClass/createTypedRelationship necesitan.
describe('DiagramService: entidad intermedia visual para asociaciones M:N', () => {
  class FakeUMLClass {
    id: string;
    private state: any;
    constructor(opts: any) {
      this.id = opts.id || `class-${Math.random().toString(36).slice(2)}`;
      this.state = { position: { x: 0, y: 0 }, size: { width: 180, height: 110 }, ...opts };
    }
    set(k: any, v: any) { this.state[k] = v; if (k === 'id') this.id = v; }
    get(k: any) { return this.state[k]; }
    on() {}
    position(x?: number, y?: number) {
      if (x !== undefined && y !== undefined) this.state.position = { x, y };
      return this.state.position;
    }
    size() { return this.state.size; }
    resize(w: number, h: number) { this.state.size = { width: w, height: h }; }
    addPort() {}
    toFront() {}
    isElement() { return true; }
    remove() { (this as any)._graph?.removeCell(this); }
  }

  class FakeLink {
    id: string;
    private state: any;
    private removed = false;
    constructor(attrs: any) {
      this.id = attrs.id || `link-${Math.random().toString(36).slice(2)}`;
      this.state = { labels: [], ...attrs };
    }
    set(k: any, v: any) { this.state[k] = v; if (k === 'id') this.id = v; }
    get(k: any) { return this.state[k]; }
    isElement() { return false; }
    remove() { this.removed = true; (this as any)._graph?.removeCell(this); }
    isRemoved() { return this.removed; }
  }

  class FakeGraph {
    cells: any[] = [];
    getCells() { return this.cells; }
    getElements() { return this.cells.filter(c => c.isElement && c.isElement()); }
    getLinks() { return this.cells.filter(c => !c.isElement || !c.isElement()); }
    getCell(id: string) { return this.cells.find(c => c.id === id || c.get('id') === id); }
    addCell(cell: any) {
      (cell as any)._graph = this;
      this.cells.push(cell);
    }
    removeCell(cell: any) {
      this.cells = this.cells.filter(c => c !== cell);
    }
    on() {}
    off() {}
  }

  function createService(): DiagramService {
    const service = new DiagramService(
      { scheduleAutoResize: () => {}, updatePorts: () => {} } as any,
      { broadcast: jasmine.createSpy('broadcast') } as any,
      { export: () => ({ classes: [], relationships: [] }) } as any,
      {} as any,
      {} as any
    );
    (service as any).joint = {
      shapes: { custom: { UMLClass: FakeUMLClass } },
      dia: { Link: FakeLink }
    };
    const graph = new FakeGraph();
    (service as any).graph = graph;
    // persist() escribe en localStorage y agenda backend backup; en estos
    // tests unitarios solo interesa el efecto sobre el grafo, así que se
    // neutraliza el resto de persist() para no depender de localStorage/backend.
    spyOn(service as any, 'scheduleBackendBackup');
    return service;
  }

  function addManyToManyLink(
    service: DiagramService,
    sourceId: string,
    targetId: string,
    options: { id?: string; vertices?: Array<{ x: number; y: number }> } = {}
  ) {
    const graph = (service as any).graph as FakeGraph;
    const link = new FakeLink({
      id: options.id,
      relationType: 'association',
      source: { id: sourceId },
      target: { id: targetId },
      vertices: options.vertices || [],
      labels: [
        { attrs: { text: { text: '0..*' } } },
        { attrs: { text: { text: '0..*' } } }
      ]
    });
    graph.addCell(link);
    return link;
  }

  function makeClass(service: DiagramService, id: string, name: string) {
    const graph = (service as any).graph as FakeGraph;
    const el = new FakeUMLClass({ id, name });
    graph.addCell(el);
    return el;
  }

  // Caso 1: A 0..* <-> 0..* B -> aparece exactamente una entidad intermedia.
  it('caso 1: transforma una asociación M:N en una entidad intermedia + 2 relaciones 1:N', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    addManyToManyLink(service, estudiante.id, curso.id);

    (service as any).persist();

    const junctions = graph.getElements().filter((e: any) => e.get('generatedJunction'));
    expect(junctions.length).toBe(1);
    expect(junctions[0].get('name')).toBe('Curso_Estudiante'); // orden alfabético determinista
    expect(junctions[0].get('attributes')).toBe('id: int');

    const mtomLinksRemaining = graph.getLinks().filter((l: any) => {
      const labels = (l.get('labels') || []).map((x: any) => x.attrs?.text?.text);
      return labels[0]?.includes('*') && labels[1]?.includes('*');
    });
    expect(mtomLinksRemaining.length).toBe(0); // la relación M:N original ya no existe

    const legs = graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg'));
    expect(legs.length).toBe(2);
    const legTargets = legs.map((l: any) => l.get('target').id).sort();
    expect(legTargets).toEqual([junctions[0].id, junctions[0].id]);
    const legSources = legs.map((l: any) => l.get('source').id).sort();
    expect(legSources).toEqual([curso.id, estudiante.id].sort());
  });

  // Caso 2: volver a renderizar/recargar (persist() se dispara varias veces,
  // como ocurre con el listener graph.on('add remove change', persist)) no
  // debe duplicar la entidad intermedia ni sus relaciones.
  it('caso 2: reconciliar varias veces seguidas no duplica la entidad ni sus relaciones', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    addManyToManyLink(service, estudiante.id, curso.id);

    (service as any).persist();
    (service as any).persist();
    (service as any).persist();

    expect(graph.getElements().filter((e: any) => e.get('generatedJunction')).length).toBe(1);
    expect(graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg')).length).toBe(2);
  });

  // Caso 3: eliminar la relación M:N (aquí: eliminar una de las 2 relaciones
  // generadas, la única forma de "tocar" la M:N una vez transformada) hace
  // desaparecer la entidad intermedia generada, sin dejar la otra pata huérfana.
  it('caso 3: eliminar una relación generada retira también la entidad intermedia y la otra pata', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    addManyToManyLink(service, estudiante.id, curso.id);
    (service as any).persist();

    const junction = graph.getElements().find((e: any) => e.get('generatedJunction'));
    expect(junction).toBeTruthy();
    const [legA] = graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg'));

    legA.remove();
    (service as any).persist();

    expect(graph.getElements().filter((e: any) => e.get('generatedJunction')).length).toBe(0);
    expect(graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg')).length).toBe(0);
  });

  // Caso 4: si el usuario "degrada" la relación (deja de ser M:N en ambos
  // extremos) antes de que exista una entidad intermedia materializada, nunca
  // se crea ninguna -> no queda huérfana.
  it('caso 4: una relación editada para dejar de ser M:N no genera entidad intermedia', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    const link = addManyToManyLink(service, estudiante.id, curso.id);

    // El usuario cambia la cardinalidad a 1:N antes de que se reconcilie.
    link.set('labels', [
      { attrs: { text: { text: '1' } } },
      { attrs: { text: { text: '0..*' } } }
    ]);

    (service as any).persist();

    expect(graph.getElements().filter((e: any) => e.get('generatedJunction')).length).toBe(0);
    expect(graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg')).length).toBe(0);
    expect(graph.getLinks().length).toBe(1); // la relación 1:N original sigue existiendo, intacta
  });

  it('el nombre y el id de la entidad intermedia son deterministas para el mismo link sin importar cuál lado es source', () => {
    const serviceAB = createService();
    const a1 = makeClass(serviceAB, 'a-1', 'Alumno');
    const b1 = makeClass(serviceAB, 'b-1', 'Materia');
    addManyToManyLink(serviceAB, a1.id, b1.id, { id: 'rel-alumno-materia' });
    (serviceAB as any).persist();

    const serviceBA = createService();
    const a2 = makeClass(serviceBA, 'a-1', 'Alumno');
    const b2 = makeClass(serviceBA, 'b-1', 'Materia');
    addManyToManyLink(serviceBA, b2.id, a2.id, { id: 'rel-alumno-materia' }); // orden invertido
    (serviceBA as any).persist();

    const graphAB = (serviceAB as any).graph as FakeGraph;
    const graphBA = (serviceBA as any).graph as FakeGraph;
    const junctionAB = graphAB.getElements().find((e: any) => e.get('generatedJunction'));
    const junctionBA = graphBA.getElements().find((e: any) => e.get('generatedJunction'));

    expect(junctionAB.id).toBe(junctionBA.id);
    expect(junctionAB.get('name')).toBe(junctionBA.get('name'));
  });

  it('no transforma una generalización (herencia) aunque tenga labels con "*"', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const base = makeClass(service, 'base-1', 'Persona');
    const sub = makeClass(service, 'sub-1', 'Empleado');
    const link = new FakeLink({
      relationType: 'generalization',
      source: { id: sub.id },
      target: { id: base.id },
      labels: [
        { attrs: { text: { text: '*' } } },
        { attrs: { text: { text: '*' } } }
      ]
    });
    graph.addCell(link);

    (service as any).persist();

    expect(graph.getElements().filter((e: any) => e.get('generatedJunction')).length).toBe(0);
    expect(graph.getLinks().length).toBe(1);
    expect(graph.getLinks()[0]).toBe(link);
  });

  it('no transforma agregación, composición ni dependencia aunque ambas multiplicidades sean many', () => {
    for (const relationType of ['aggregation', 'composition', 'dependency']) {
      const service = createService();
      const graph = (service as any).graph as FakeGraph;
      const source = makeClass(service, `${relationType}-source`, 'Source');
      const target = makeClass(service, `${relationType}-target`, 'Target');
      const link = new FakeLink({
        id: `${relationType}-link`,
        relationType,
        source: { id: source.id },
        target: { id: target.id },
        labels: [
          { attrs: { text: { text: '*' } } },
          { attrs: { text: { text: '*' } } }
        ]
      });
      graph.addCell(link);

      (service as any).persist();

      expect(graph.getElements().filter((e: any) => e.get('generatedJunction')).length)
        .withContext(relationType).toBe(0);
      expect(graph.getLinks()).withContext(relationType).toEqual([link]);
    }
  });

  it('mantiene separadas asociaciones M:N paralelas con ids y nombres deterministas', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    addManyToManyLink(service, estudiante.id, curso.id, { id: 'rel-b' });
    addManyToManyLink(service, estudiante.id, curso.id, { id: 'rel-a' });

    (service as any).persist();

    const junctions = graph.getElements()
      .filter((e: any) => e.get('generatedJunction'))
      .sort((a: any, b: any) => a.id.localeCompare(b.id));
    expect(junctions.length).toBe(2);
    expect(junctions.map((e: any) => e.get('name')).sort())
      .toEqual(['Curso_Estudiante', 'Curso_Estudiante_2']);
    expect(junctions.map((e: any) => e.id).sort())
      .toEqual([
        'junction:curso-1:estudiante-1:rel-a',
        'junction:curso-1:estudiante-1:rel-b'
      ]);
    expect(graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg')).length).toBe(4);
  });

  it('crea dos patas distintas para una asociación M:N reflexiva', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const persona = makeClass(service, 'persona-1', 'Persona');
    addManyToManyLink(service, persona.id, persona.id, { id: 'rel-reflexiva' });

    (service as any).persist();

    const junction = graph.getElements().find((e: any) => e.get('generatedJunction'));
    const legs = graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg'));
    expect(junction).toBeTruthy();
    expect(junction.get('name')).toBe('Persona_Persona');
    expect(legs.length).toBe(2);
    expect(new Set(legs.map((l: any) => l.id)).size).toBe(2);
  });

  // Regresión del bug de recarga: loadFromJson() crea primero TODAS las
  // clases y luego TODAS las relaciones (dos bucles separados). Sin la
  // suspensión de reconcileGeneratedJunctions() durante el lote, justo
  // después de crear la clase intermedia (con 0 relaciones todavía, porque
  // las relaciones se cargan en el siguiente bucle) la limpieza de huérfanos
  // la borraba antes de que sus 2 patas llegaran a crearse.
  it('recargar un backup con una junction ya persistida no la elimina a mitad de la carga', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const backup = {
      classes: [
        { id: 'estudiante-1', name: 'Estudiante', attributes: [], methods: [], position: { x: 100, y: 100 } },
        { id: 'curso-1', name: 'Curso', attributes: [], methods: [], position: { x: 380, y: 100 } },
        {
          id: 'junction:curso-1:estudiante-1',
          name: 'Curso_Estudiante',
          attributes: [],
          methods: [],
          position: { x: 240, y: 270 },
          generated: true
        }
      ],
      relationships: [
        {
          id: 'junction-link:estudiante-1:junction:curso-1:estudiante-1',
          type: 'association',
          sourceId: 'estudiante-1',
          targetId: 'junction:curso-1:estudiante-1',
          labels: ['1', '0..*'],
          generated: true
        },
        {
          id: 'junction-link:curso-1:junction:curso-1:estudiante-1',
          type: 'association',
          sourceId: 'curso-1',
          targetId: 'junction:curso-1:estudiante-1',
          labels: ['1', '0..*'],
          generated: true
        }
      ]
    };

    service.loadFromJson(backup, true, false);

    const junctions = graph.getElements().filter((e: any) => e.get('generatedJunction'));
    expect(junctions.length).toBe(1);
    expect(junctions[0].id).toBe('junction:curso-1:estudiante-1');
    expect(graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg')).length).toBe(2);
    expect(graph.getElements().map((e: any) => e.get('name')).sort())
      .toEqual(['Curso', 'Curso_Estudiante', 'Estudiante']);
  });

  it('recargar el mismo backup varias veces seguidas no duplica la junction', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const backup = {
      classes: [
        { id: 'estudiante-1', name: 'Estudiante', attributes: [], methods: [], position: { x: 100, y: 100 } },
        { id: 'curso-1', name: 'Curso', attributes: [], methods: [], position: { x: 380, y: 100 } },
        { id: 'junction:curso-1:estudiante-1', name: 'Curso_Estudiante', attributes: [], methods: [], position: { x: 240, y: 270 }, generated: true }
      ],
      relationships: [
        { id: 'junction-link:estudiante-1:junction:curso-1:estudiante-1', type: 'association', sourceId: 'estudiante-1', targetId: 'junction:curso-1:estudiante-1', labels: ['1', '0..*'], generated: true },
        { id: 'junction-link:curso-1:junction:curso-1:estudiante-1', type: 'association', sourceId: 'curso-1', targetId: 'junction:curso-1:estudiante-1', labels: ['1', '0..*'], generated: true }
      ]
    };

    service.loadFromJson(backup, true, false);
    service.loadFromJson(backup, true, false);
    service.loadFromJson(backup, true, false);

    expect(graph.getElements().filter((e: any) => e.get('generatedJunction')).length).toBe(1);
    expect(graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg')).length).toBe(2);
  });

  // Bug 2: degradar una pata ya generada (editar su multiplicidad para que
  // el lado hacia la junction deje de ser "muchos") debe desarmar la
  // junction; volver a crear una M:N válida debe regenerarla sin duplicar.
  it('editar una pata generada restaura la asociación original antes de retirar la junction', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    const original = addManyToManyLink(service, estudiante.id, curso.id, {
      id: 'rel-original',
      vertices: [{ x: 210, y: 160 }]
    });
    (service as any).persist();

    expect(graph.getElements().filter((e: any) => e.get('generatedJunction')).length).toBe(1);

    // Degradar: el usuario edita una de las 2 patas generadas para que el
    // lado hacia la junction deje de ser "muchos".
    const legs = graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg'));
    legs[0].set('labels', [
      { attrs: { text: { text: '1' } } },
      { attrs: { text: { text: '1' } } }
    ]);
    (service as any).persist();

    expect(graph.getElements().filter((e: any) => e.get('generatedJunction')).length).toBe(0);
    expect(graph.getLinks().filter((l: any) => l.get('generatedJunctionLeg')).length).toBe(0);
    expect(graph.getElements().map((e: any) => e.get('name')).sort()).toEqual(['Curso', 'Estudiante']);
    const restored = graph.getLinks().find((l: any) => l.id === original.id);
    expect(restored).toBeTruthy();
    expect(restored.get('relationType')).toBe('association');
    expect(restored.get('source')).toEqual({ id: estudiante.id });
    expect(restored.get('target')).toEqual({ id: curso.id });
    expect((restored.get('labels') || []).map((label: any) => label.attrs.text.text))
      .toEqual(['0..*', '0..*']);
    expect(restored.get('vertices')).toEqual([{ x: 210, y: 160 }]);
  });

  it('difunde la metadata de una junction generada al crear la clase', () => {
    const service = createService();
    const collab = (service as any).collab;
    const junctionOrigin = {
      id: 'rel-origin',
      type: 'association',
      sourceId: 'a',
      targetId: 'b',
      labels: [],
      vertices: []
    };

    service.createUmlClass({
      id: 'junction:a:b:rel-origin',
      name: 'A_B',
      attributes: [{ name: 'id', type: 'int' }],
      methods: [],
      position: { x: 0, y: 0 },
      generated: true,
      junctionOrigin
    } as any);

    expect(collab.broadcast).toHaveBeenCalledWith(jasmine.objectContaining({
      t: 'add_class',
      id: 'junction:a:b:rel-origin',
      payload: jasmine.objectContaining({ generated: true, junctionOrigin })
    }));
  });

  // Clase asociativa: si Detalle ya está enlazada a Venta y a Producto por
  // conectores 'association-class' ANTES de que se dibuje la M:N entre
  // Venta y Producto, la M:N debe permanecer directa (no reemplazarse por
  // una entidad intermedia auto-generada).
  it('una M:N con clase asociativa ya enlazada permanece directa, sin auto-junction', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const venta = makeClass(service, 'venta-1', 'Venta');
    const producto = makeClass(service, 'producto-1', 'Producto');
    const detalle = makeClass(service, 'detalle-1', 'Detalle');

    // Enlaces de clase asociativa creados ANTES que la M:N.
    const l1 = new FakeLink({ relationType: 'association-class', source: { id: detalle.id }, target: { id: venta.id }, labels: [] });
    const l2 = new FakeLink({ relationType: 'association-class', source: { id: detalle.id }, target: { id: producto.id }, labels: [] });
    graph.addCell(l1);
    graph.addCell(l2);
    (service as any).persist();

    // Ahora la M:N directa entre Venta y Producto.
    const mn = addManyToManyLink(service, venta.id, producto.id);
    (service as any).persist();

    // No debe haberse creado ninguna entidad intermedia auto-generada.
    expect(graph.getElements().filter((e: any) => e.get('generatedJunction')).length).toBe(0);
    // La relación M:N original sigue viva y directa entre Venta y Producto.
    expect(graph.getLinks().find((l: any) => l === mn)).toBeTruthy();
    expect(mn.get('source').id).toBe(venta.id);
    expect(mn.get('target').id).toBe(producto.id);
    // Detalle sigue existiendo como clase normal, con sus 2 conectores punteados.
    expect(graph.getElements().map((e: any) => e.get('name')).sort()).toEqual(['Detalle', 'Producto', 'Venta']);
    expect(graph.getLinks().filter((l: any) => l.get('relationType') === 'association-class').length).toBe(2);
  });

  it('sin clase asociativa enlazada, la M:N se sigue auto-transformando como antes (compatibilidad)', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const venta = makeClass(service, 'venta-1', 'Venta');
    const producto = makeClass(service, 'producto-1', 'Producto');
    makeClass(service, 'detalle-1', 'Detalle'); // clase presente pero SIN enlaces association-class

    addManyToManyLink(service, venta.id, producto.id);
    (service as any).persist();

    expect(graph.getElements().filter((e: any) => e.get('generatedJunction')).length).toBe(1);
  });
});
