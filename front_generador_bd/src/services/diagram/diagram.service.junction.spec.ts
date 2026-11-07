import { DiagramService } from './diagram.service';

// Mismo patrón de mocks mínimos usado en diagram.service.spec.ts: JointJS real
// no se instancia en estos tests, se sustituye por clases equivalentes con
// solo la superficie que createUmlClass/createTypedRelationship necesitan.
//
// Clase asociativa UML (como en StarUML y Enterprise Architect): la asociación M:N se queda DIRECTA entre sus
// dos clases, con sus multiplicidades, y desde el medio de esa línea sale un conector punteado, sin
// multiplicidad, hacia la clase asociativa (aquí `Curso_Estudiante`).
describe('DiagramService: clase asociativa de una asociación M:N', () => {
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
    isLink() { return false; }
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
    isLink() { return true; }
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

  const generatedClasses = (graph: FakeGraph) => graph.getElements().filter((e: any) => e.get('generatedJunction'));
  const dashedLinks = (graph: FakeGraph) => graph.getLinks().filter((l: any) => l.get('relationType') === 'association-class');

  // Caso 1: A 0..* <-> 0..* B -> la asociación sigue directa y aparece una clase asociativa unida por un punteado.
  it('caso 1: la M:N queda directa y recibe una clase asociativa con un conector punteado desde su medio', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    const mn = addManyToManyLink(service, estudiante.id, curso.id);

    (service as any).persist();

    // La asociación M:N sigue existiendo entre Estudiante y Curso, con sus multiplicidades.
    expect(graph.getCell(mn.id)).toBe(mn);
    expect(mn.get('source')).toEqual({ id: estudiante.id });
    expect(mn.get('target')).toEqual({ id: curso.id });
    expect((mn.get('labels') || []).map((l: any) => l.attrs.text.text)).toEqual(['0..*', '0..*']);

    const classes = generatedClasses(graph);
    expect(classes.length).toBe(1);
    expect(classes[0].get('name')).toBe('Curso_Estudiante'); // orden alfabético determinista
    expect(classes[0].get('attributes')).toBe('id: int');

    // Un único conector punteado, de la clase asociativa al MEDIO de la línea M:N, sin multiplicidad.
    const dashed = dashedLinks(graph);
    expect(dashed.length).toBe(1);
    expect(dashed[0].get('source')).toEqual({ id: classes[0].id });
    expect(dashed[0].get('target')).toEqual({ id: mn.id });
    expect(dashed[0].get('labels')).toEqual([]);
    expect(dashed[0].get('generatedJunctionLeg')).toBe(true);

    // Ya no se inventan relaciones 1:N: la única asociación es la M:N.
    expect(graph.getLinks().filter((l: any) => (l.get('relationType') || 'association') === 'association')).toEqual([mn]);
  });

  // Caso 2: volver a reconciliar (persist() se dispara con cualquier cambio del grafo) no duplica nada.
  it('caso 2: reconciliar varias veces seguidas no duplica la clase asociativa ni su conector', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    addManyToManyLink(service, estudiante.id, curso.id);

    (service as any).persist();
    (service as any).persist();
    (service as any).persist();

    expect(generatedClasses(graph).length).toBe(1);
    expect(dashedLinks(graph).length).toBe(1);
  });

  // Caso 3: borrar la clase asociativa generada deja la M:N directa, sin clase, y no se vuelve a crear sola.
  it('caso 3: borrar la clase asociativa generada deja la M:N directa y no se regenera', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    const mn = addManyToManyLink(service, estudiante.id, curso.id);
    (service as any).persist();

    const clase = generatedClasses(graph)[0];
    clase.remove();
    // el listener graph.on('remove') del servicio avisa de la clase que se quitó
    (service as any).onGeneratedCellRemoved(clase);
    (service as any).persist();
    (service as any).persist();

    expect(generatedClasses(graph).length).toBe(0);
    expect(dashedLinks(graph).length).toBe(0);
    expect(graph.getCell(mn.id)).toBe(mn);
    expect(mn.get('junctionOptOut')).toBe(true);
  });

  // Caso 3b: si se borra la asociación M:N, la clase asociativa generada y su conector desaparecen con ella.
  it('caso 3b: borrar la asociación M:N retira la clase asociativa generada y su conector', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    const mn = addManyToManyLink(service, estudiante.id, curso.id);
    (service as any).persist();
    expect(generatedClasses(graph).length).toBe(1);

    mn.remove();
    (service as any).persist();

    expect(generatedClasses(graph).length).toBe(0);
    expect(dashedLinks(graph).length).toBe(0);
    expect(graph.getElements().map((e: any) => e.get('name')).sort()).toEqual(['Curso', 'Estudiante']);
  });

  // Caso 4: si la relación deja de ser M:N (se edita la multiplicidad), la clase asociativa generada se retira.
  it('caso 4: editar la relación para que deje de ser M:N retira la clase asociativa generada', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    const link = addManyToManyLink(service, estudiante.id, curso.id);
    (service as any).persist();
    expect(generatedClasses(graph).length).toBe(1);

    link.set('labels', [
      { attrs: { text: { text: '1' } } },
      { attrs: { text: { text: '0..*' } } }
    ]);
    (service as any).persist();

    expect(generatedClasses(graph).length).toBe(0);
    expect(dashedLinks(graph).length).toBe(0);
    expect(graph.getLinks()).toEqual([link]); // la relación 1:N sigue, intacta
    expect(link.get('junctionOptOut')).toBeFalsy();
  });

  it('una relación que nunca fue M:N no genera clase asociativa', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    const link = addManyToManyLink(service, estudiante.id, curso.id);
    link.set('labels', [
      { attrs: { text: { text: '1' } } },
      { attrs: { text: { text: '0..*' } } }
    ]);

    (service as any).persist();

    expect(generatedClasses(graph).length).toBe(0);
    expect(graph.getLinks()).toEqual([link]);
  });

  it('el nombre y el id de la clase asociativa son deterministas para el mismo link sin importar cuál lado es source', () => {
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

    const claseAB = generatedClasses((serviceAB as any).graph)[0];
    const claseBA = generatedClasses((serviceBA as any).graph)[0];
    expect(claseAB.id).toBe(claseBA.id);
    expect(claseAB.get('name')).toBe(claseBA.get('name'));
  });

  it('no genera clase asociativa para una generalización (herencia) aunque tenga labels con "*"', () => {
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

    expect(generatedClasses(graph).length).toBe(0);
    expect(graph.getLinks()).toEqual([link]);
  });

  it('no genera clase asociativa para agregación, composición ni dependencia aunque ambas multiplicidades sean many', () => {
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

      expect(generatedClasses(graph).length).withContext(relationType).toBe(0);
      expect(graph.getLinks()).withContext(relationType).toEqual([link]);
    }
  });

  it('mantiene separadas asociaciones M:N paralelas con ids y nombres deterministas', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const estudiante = makeClass(service, 'estudiante-1', 'Estudiante');
    const curso = makeClass(service, 'curso-1', 'Curso');
    const mnB = addManyToManyLink(service, estudiante.id, curso.id, { id: 'rel-b' });
    const mnA = addManyToManyLink(service, estudiante.id, curso.id, { id: 'rel-a' });

    (service as any).persist();

    const clases = generatedClasses(graph).sort((a: any, b: any) => a.id.localeCompare(b.id));
    expect(clases.length).toBe(2);
    expect(clases.map((e: any) => e.get('name')).sort()).toEqual(['Curso_Estudiante', 'Curso_Estudiante_2']);
    expect(clases.map((e: any) => e.id).sort())
      .toEqual([
        'junction:curso-1:estudiante-1:rel-a',
        'junction:curso-1:estudiante-1:rel-b'
      ]);
    // cada clase cuelga de SU asociación
    const destinos = dashedLinks(graph).map((l: any) => l.get('target').id).sort();
    expect(destinos).toEqual([mnA.id, mnB.id].sort());
  });

  it('una asociación M:N reflexiva recibe una sola clase asociativa unida al medio de su lazo', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const persona = makeClass(service, 'persona-1', 'Persona');
    const mn = addManyToManyLink(service, persona.id, persona.id, { id: 'rel-reflexiva' });

    (service as any).persist();

    const clase = generatedClasses(graph)[0];
    expect(clase.get('name')).toBe('Persona_Persona');
    expect(dashedLinks(graph).length).toBe(1);
    expect(dashedLinks(graph)[0].get('target')).toEqual({ id: mn.id });
    expect(graph.getCell(mn.id)).toBe(mn);
  });

  // Regresión del bug de recarga: loadFromJson() crea primero TODAS las clases y luego TODAS las relaciones.
  // Sin suspender la reconciliación durante la carga, la limpieza se adelantaba a la creación del conector.
  // El conector punteado apunta a OTRA relación: debe crearse después de ella aunque el respaldo lo traiga antes.
  it('recargar un respaldo con la clase asociativa ya guardada no la elimina a mitad de la carga ni la duplica', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const backup = {
      classes: [
        { id: 'estudiante-1', name: 'Estudiante', attributes: [], methods: [], position: { x: 100, y: 100 } },
        { id: 'curso-1', name: 'Curso', attributes: [], methods: [], position: { x: 380, y: 100 } },
        {
          id: 'junction:curso-1:estudiante-1:rel-1',
          name: 'Curso_Estudiante',
          attributes: [],
          methods: [],
          position: { x: 240, y: 270 },
          generated: true,
          junctionOrigin: { id: 'rel-1', type: 'association', sourceId: 'estudiante-1', targetId: 'curso-1', labels: ['0..*', '0..*'], vertices: [] }
        }
      ],
      relationships: [
        // el punteado viene ANTES que la asociación a la que apunta
        { id: 'assoc-class-link:rel-1', type: 'association-class', sourceId: 'junction:curso-1:estudiante-1:rel-1', targetId: 'rel-1', labels: [], generated: true },
        { id: 'rel-1', type: 'association', sourceId: 'estudiante-1', targetId: 'curso-1', labels: ['0..*', '0..*'] }
      ]
    };

    service.loadFromJson(backup, true, false);
    service.loadFromJson(backup, true, false);
    service.loadFromJson(backup, true, false);

    expect(generatedClasses(graph).length).toBe(1);
    expect(generatedClasses(graph)[0].id).toBe('junction:curso-1:estudiante-1:rel-1');
    expect(dashedLinks(graph).length).toBe(1);
    expect(graph.getLinks().filter((l: any) => l.id === 'rel-1').length).toBe(1);
    expect(graph.getElements().map((e: any) => e.get('name')).sort())
      .toEqual(['Curso', 'Curso_Estudiante', 'Estudiante']);
  });

  // Los respaldos guardados antes de este cambio traen la forma anterior: clase intermedia + dos relaciones 1:N
  // y sin la M:N. Se migran solos: vuelve la M:N original, se retiran las dos patas y la clase queda como asociativa.
  it('un respaldo con la forma anterior (clase intermedia y dos relaciones 1:N) se migra a clase asociativa', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const backup = {
      classes: [
        { id: 'estudiante-1', name: 'Estudiante', attributes: [], methods: [], position: { x: 100, y: 100 } },
        { id: 'curso-1', name: 'Curso', attributes: [], methods: [], position: { x: 380, y: 100 } },
        {
          id: 'junction:curso-1:estudiante-1:rel-1',
          name: 'Curso_Estudiante',
          attributes: [{ name: 'id', type: 'int' }],
          methods: [],
          position: { x: 240, y: 270 },
          generated: true,
          junctionOrigin: { id: 'rel-1', type: 'association', sourceId: 'estudiante-1', targetId: 'curso-1', labels: ['0..*', '0..*'], vertices: [{ x: 210, y: 160 }] }
        }
      ],
      relationships: [
        { id: 'junction-link:junction:curso-1:estudiante-1:rel-1:source', type: 'association', sourceId: 'estudiante-1', targetId: 'junction:curso-1:estudiante-1:rel-1', labels: ['1', '0..*'], generated: true },
        { id: 'junction-link:junction:curso-1:estudiante-1:rel-1:target', type: 'association', sourceId: 'curso-1', targetId: 'junction:curso-1:estudiante-1:rel-1', labels: ['1', '0..*'], generated: true }
      ]
    };

    service.loadFromJson(backup, true, false);
    (service as any).persist();

    // vuelve la asociación M:N original, con su id, sus multiplicidades y sus vértices
    const mn = graph.getCell('rel-1');
    expect(mn).toBeTruthy();
    expect(mn.get('source')).toEqual({ id: 'estudiante-1' });
    expect(mn.get('target')).toEqual({ id: 'curso-1' });
    expect((mn.get('labels') || []).map((l: any) => l.attrs.text.text)).toEqual(['0..*', '0..*']);
    expect(mn.get('vertices')).toEqual([{ x: 210, y: 160 }]);
    expect(mn.get('junctionOptOut')).toBeFalsy();
    // la clase se conserva (mismo id) y las dos patas 1:N ya no están
    expect(generatedClasses(graph).map((c: any) => c.id)).toEqual(['junction:curso-1:estudiante-1:rel-1']);
    expect(graph.getLinks().filter((l: any) => (l.get('relationType') || 'association') === 'association')).toEqual([mn]);
    // y cuelga del medio de la M:N con su conector punteado
    expect(dashedLinks(graph).length).toBe(1);
    expect(dashedLinks(graph)[0].get('target')).toEqual({ id: 'rel-1' });
  });

  it('difunde la metadata de una clase asociativa generada al crear la clase', () => {
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

  // Clase asociativa dibujada por la persona: la clase Detalle ya cuelga, con un punteado, del medio de la M:N
  // entre Venta y Producto. No se agrega otra clase automática.
  it('una M:N con una clase asociativa ya enlazada por la persona permanece como está, sin clase automática', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const venta = makeClass(service, 'venta-1', 'Venta');
    const producto = makeClass(service, 'producto-1', 'Producto');
    const detalle = makeClass(service, 'detalle-1', 'Detalle');
    const mn = addManyToManyLink(service, venta.id, producto.id, { id: 'rel-vp' });
    const punteado = new FakeLink({ relationType: 'association-class', source: { id: detalle.id }, target: { id: mn.id }, labels: [] });
    graph.addCell(punteado);

    (service as any).persist();
    (service as any).persist();

    expect(generatedClasses(graph).length).toBe(0);
    expect(graph.getCell(mn.id)).toBe(mn);
    expect(dashedLinks(graph)).toEqual([punteado]);
    expect(graph.getElements().map((e: any) => e.get('name')).sort()).toEqual(['Detalle', 'Producto', 'Venta']);
  });

  // Compatibilidad: la forma anterior de la clase asociativa dibujada a mano (dos punteados, uno a cada clase).
  it('la forma anterior con dos punteados hacia las dos clases sigue contando como clase asociativa enlazada', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const venta = makeClass(service, 'venta-1', 'Venta');
    const producto = makeClass(service, 'producto-1', 'Producto');
    const detalle = makeClass(service, 'detalle-1', 'Detalle');
    const l1 = new FakeLink({ relationType: 'association-class', source: { id: detalle.id }, target: { id: venta.id }, labels: [] });
    const l2 = new FakeLink({ relationType: 'association-class', source: { id: detalle.id }, target: { id: producto.id }, labels: [] });
    graph.addCell(l1);
    graph.addCell(l2);
    const mn = addManyToManyLink(service, venta.id, producto.id);

    (service as any).persist();

    expect(generatedClasses(graph).length).toBe(0);
    expect(graph.getCell(mn.id)).toBe(mn);
    expect(dashedLinks(graph).length).toBe(2);
  });

  it('un conector punteado cuya asociación se borró se retira (no queda colgando)', () => {
    const service = createService();
    const graph = (service as any).graph as FakeGraph;
    const venta = makeClass(service, 'venta-1', 'Venta');
    const producto = makeClass(service, 'producto-1', 'Producto');
    const detalle = makeClass(service, 'detalle-1', 'Detalle');
    const mn = addManyToManyLink(service, venta.id, producto.id, { id: 'rel-vp' });
    graph.addCell(new FakeLink({ relationType: 'association-class', source: { id: detalle.id }, target: { id: mn.id }, labels: [] }));
    (service as any).persist();

    mn.remove();
    (service as any).persist();

    expect(dashedLinks(graph).length).toBe(0);
    expect(graph.getElements().map((e: any) => e.get('name')).sort()).toEqual(['Detalle', 'Producto', 'Venta']);
  });
});
