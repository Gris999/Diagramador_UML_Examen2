import { DiagramService } from './diagram.service';

describe('DiagramService AI edit regressions', () => {
  function createService(): DiagramService {
    return new DiagramService(
      { scheduleAutoResize: jasmine.createSpy('scheduleAutoResize') } as any,
      { broadcast: jasmine.createSpy('broadcast') } as any,
      {} as any,
      {} as any,
      {} as any
    );
  }

  function createCanvasElement(id: string, initial: { name: string; attributes?: string; methods?: string }) {
    const state: any = { attributes: '', methods: '', ...initial };
    return {
      id,
      isElement: () => true,
      get: (prop: string) => state[prop],
      set: (prop: string, value: any) => { state[prop] = value; }
    };
  }

  // Sustituto mínimo de joint.dia.Link: solo lo que createTypedRelationship necesita
  // (constructor con atributos iniciales + get/set), sin depender de JointJS real.
  class FakeLink {
    id: string;
    private state: any;
    constructor(attrs: any) {
      this.id = attrs.id || `link-${Math.random().toString(36).slice(2)}`;
      this.state = { ...attrs };
    }
    set(prop: string, value: any) { this.state[prop] = value; }
    get(prop: string) { return this.state[prop]; }
  }

  it('preserves untouched attributes when the AI edits one attribute', () => {
    const service = createService();

    const result = (service as any).mergeAttributes(
      'id: number\nname: string\nemail: string',
      '',
      [{ originalName: 'name', name: 'fullName', type: 'string' }],
      [
        { name: 'id', type: 'number' },
        { name: 'name', type: 'string' },
        { name: 'email', type: 'string' }
      ]
    );

    expect(result).toBe('id: number\nfullName: string\nemail: string');
  });

  it('preserves untouched methods when the AI edits one method', () => {
    const service = createService();

    const result = (service as any).mergeMethods(
      'getId(): number;\nsetName(name: string): void;\narchive(): void;',
      '',
      [{ originalName: 'setName', name: 'rename', parameters: 'value: string', returnType: 'void' }],
      [
        { name: 'getId', returnType: 'number' },
        { name: 'setName', parameters: 'name: string', returnType: 'void' },
        { name: 'archive', returnType: 'void' }
      ]
    );

    expect(result).toBe(
      'getId(): number;\nrename(value: string): void;\narchive(): void;'
    );
  });

  it('does not directly broadcast when deleting a selected cell', () => {
    const service = createService();
    const broadcast = (service as any).collab.broadcast as jasmine.Spy;
    const remove = jasmine.createSpy('remove');
    (service as any).selectedCell = { id: 'class-1', remove };

    service.deleteSelected();

    expect(remove).toHaveBeenCalledTimes(1);
    expect(broadcast).not.toHaveBeenCalled();
  });

  it('deletes only the relationship in the requested direction', () => {
    const service = createService();
    const remove = jasmine.createSpy('remove');
    const source = { id: 'customer', isElement: () => true, get: () => 'Customer' };
    const target = { id: 'order', isElement: () => true, get: () => 'Order' };
    const link = {
      id: 'customer-order',
      get: (property: string) => {
        if (property === 'source') return { id: 'customer' };
        if (property === 'target') return { id: 'order' };
        if (property === 'relationType') return 'association';
        return undefined;
      },
      remove
    };
    (service as any).graph = {
      getCells: () => [source, target],
      getLinks: () => [link]
    };

    (service as any).handleDeleteOperation({
      relationships: [{ sourceId: 'Order', targetId: 'Customer', type: 'association', eliminar: true }]
    });
    expect(remove).not.toHaveBeenCalled();

    (service as any).handleDeleteOperation({
      relationships: [{ sourceId: 'Customer', targetId: 'Order', type: 'association', eliminar: true }]
    });
    expect(remove).toHaveBeenCalledTimes(1);
  });

  it('matches an edited class to its original by ID, not by array position, leaving other classes intact', () => {
    const service = createService();

    // original.classes = full diagram (2 classes); editado.classes = only the SECOND one.
    // A buggy index-based match (original.classes[0] <-> editado.classes[0]) would apply
    // the edited attribute change to ClassA instead of ClassB.
    const classAElement = createCanvasElement('class-1', { name: 'ClassA', attributes: 'id: number' });
    const classBElement = createCanvasElement('class-2', { name: 'ClassB', attributes: 'id: number' });

    (service as any).graph = {
      getCells: () => [classAElement, classBElement]
    };

    const originalClasses = [
      { id: 'class-1', name: 'ClassA', attributes: [{ name: 'id', type: 'number' }], methods: [] },
      { id: 'class-2', name: 'ClassB', attributes: [{ name: 'id', type: 'number' }], methods: [] }
    ];

    const editedClasses = [
      {
        id: 'class-2',
        attributes: [{ originalName: 'id', name: 'code', type: 'string', editado: true }],
        editado: true
      }
    ];

    (service as any).handleEditOperation({
      original: { classes: originalClasses, relationships: [] },
      editado: { classes: editedClasses, relationships: [] }
    });

    expect(classBElement.get('attributes')).toBe('code: string');
    expect(classAElement.get('attributes')).toBe('id: number');
    expect(classAElement.get('name')).toBe('ClassA');
  });

  it('renames an edited class that keeps the same ID', () => {
    const service = createService();

    const classElement = createCanvasElement('class-9', { name: 'Old' });
    (service as any).graph = {
      getCells: () => [classElement]
    };

    (service as any).handleEditOperation({
      original: { classes: [{ id: 'class-9', name: 'Old', attributes: [], methods: [] }], relationships: [] },
      editado: { classes: [{ id: 'class-9', name: 'New', editado: true }], relationships: [] }
    });

    expect(classElement.get('name')).toBe('New');
  });

  it('creates a relationship required by an AI edit exactly once in the graph, without a duplicate broadcast', () => {
    const service = createService();
    const broadcast = (service as any).collab.broadcast as jasmine.Spy;
    (service as any).joint = { dia: { Link: FakeLink } };

    // Dos clases A y B ya existen en el canvas, sin relación entre ellas.
    const classAElement = createCanvasElement('canvas-a', { name: 'ClassA' });
    const classBElement = createCanvasElement('canvas-b', { name: 'ClassB' });

    const links: any[] = [];
    const addCellCalls: Array<{ cell: any; opts: any }> = [];
    (service as any).graph = {
      getCells: () => [classAElement, classBElement],
      getLinks: () => links,
      addCell: (cell: any, opts?: any) => {
        links.push(cell);
        addCellCalls.push({ cell, opts });
      }
    };

    const originalClasses = [
      { id: 'orig-a', name: 'ClassA' },
      { id: 'orig-b', name: 'ClassB' }
    ];
    // La relación aparece en el "original" (contrato del prompt de edición) pero
    // no existe aún ninguna relación real entre A y B en el graph/canvas.
    const originalRelationships = [
      { id: 'rel-new', type: 'association', sourceId: 'orig-a', targetId: 'orig-b', labels: [] }
    ];
    const editedRelation = {
      id: 'rel-new',
      type: 'association',
      sourceId: 'orig-a',
      targetId: 'orig-b',
      labels: ['1', '0..*'],
      editado: true
    };

    (service as any).updateRelationship(editedRelation, originalRelationships, originalClasses);

    // Se agrega exactamente una vez al graph (antes del fix, createTypedRelationship(..., true)
    // nunca llamaba a graph.addCell y la relación no quedaba insertada).
    expect(links.length).toBe(1);
    expect(addCellCalls.length).toBe(1);

    const [createdLink] = links;
    expect(createdLink.get('source')).toEqual({ id: 'canvas-a' });
    expect(createdLink.get('target')).toEqual({ id: 'canvas-b' });
    expect(createdLink.get('relationType')).toBe('association');
    // Multiplicidades/labels de la edición se conservan en el link creado.
    expect(createdLink.get('labels').map((l: any) => l.attrs.text.text)).toEqual(['1', '0..*']);

    // { collab: true } evita que graph.on('add', ...) dispare su propio broadcast 'add_link'.
    expect(addCellCalls[0].opts).toEqual({ collab: true });

    // Un único broadcast de creación (add_link) — ninguno duplicado por el listener
    // automático graph.on('add', ...), que emitiría un add_link extra de no ser por collab:true.
    // Ningún move_link debe enviarse para la creación de una nueva relación.
    const addLinkBroadcasts = broadcast.calls.allArgs().filter(([msg]: any[]) => msg.t === 'add_link');
    const moveLinkBroadcasts = broadcast.calls.allArgs().filter(([msg]: any[]) => msg.t === 'move_link');
    expect(addLinkBroadcasts.length).toBe(1);
    expect(moveLinkBroadcasts.length).toBe(0);
    expect(addLinkBroadcasts[0][0]).toEqual({
      t: 'add_link',
      id: createdLink.id,
      sourceId: 'canvas-a',
      targetId: 'canvas-b',
      payload: {
        type: 'association',
        labels: createdLink.get('labels')
      }
    });
    expect(addLinkBroadcasts[0][0].id).toBe(createdLink.id);
    expect(addLinkBroadcasts[0][0].sourceId).toBe('canvas-a');
    expect(addLinkBroadcasts[0][0].targetId).toBe('canvas-b');
    expect(addLinkBroadcasts[0][0].payload.type).toBe('association');
    expect(addLinkBroadcasts[0][0].payload.labels.map((l: any) => l.attrs.text.text)).toEqual(['1', '0..*']);
  });

  class FakeUMLClass {
    id: string;
    private state: any;
    constructor(opts: any) {
      this.id = opts.id || 'new';
      this.state = {
        position: { x: 0, y: 0 },
        size: { width: 180, height: 110 },
        ...opts
      };
    }
    set(k: any, v: any) {
      this.state[k] = v;
      if (k === 'id') this.id = v;
    }
    get(k: any) { return this.state[k]; }
    listeners: any = {};
    on(evt: string, cb: any) { this.listeners[evt] = cb; }
    trigger(evt: string) { if (this.listeners[evt]) this.listeners[evt](); }
    position(x?: number, y?: number) {
      if (x !== undefined && y !== undefined) {
        this.state.position = { x, y };
      }
      return this.state.position;
    }
    size() { return this.state.size; }
    resize(width: number, height: number) {
      this.state.size = { width, height };
    }
    addPort() {}
    toFront() {}
    isElement() { return true; }
  }

  class FakeGraph {
    cells: any[] = [];
    addCellCalls: Array<{cell: any, opts: any}> = [];
    getCells() { return this.cells; }
    getElements() { return this.cells.filter(c => c.isElement && c.isElement()); }
    getLinks() { return this.cells.filter(c => !c.isElement || !c.isElement()); }
    getCell(id: string) { return this.cells.find(c => c.id === id || c.get('id') === id); }
    addCell(cell: any, opts?: any) {
      this.cells.push(cell);
      this.addCellCalls.push({ cell, opts });
    }
    on() {}
    off() {}
  }

  it('loadFromJson local load broadcasts add_class normally', () => {
    const service = createService();
    const broadcast = (service as any).collab.broadcast as jasmine.Spy;
    (service as any).joint = {
      shapes: { custom: { UMLClass: FakeUMLClass } }
    };

    const graph = new FakeGraph();
    (service as any).graph = graph;
    (service as any).edition = { scheduleAutoResize: () => {} };

    const json = {
      classes: [{ id: 'c1', name: 'LocalClass' }],
      relationships: []
    };

    service.loadFromJson(json, false, false);

    const addClassBroadcasts = broadcast.calls.allArgs().filter(([msg]: any[]) => msg.t === 'add_class');
    expect(addClassBroadcasts.length).toBe(1);
    expect(addClassBroadcasts[0][0].id).toBe('c1');
    expect(graph.addCellCalls.length).toBe(1);
    expect(graph.addCellCalls[0].cell.get('name')).toBe('LocalClass');
  });

  it('updates an existing AI snapshot class without moving or duplicating it', () => {
    const service = createService();
    const graph = new FakeGraph();
    const producto = new FakeUMLClass({
      id: 'producto-1',
      name: 'Producto',
      position: { x: 125, y: 210 },
      size: { width: 220, height: 140 },
      attributes: 'id: int\nnombre: string',
      methods: 'buscar(): Producto;'
    });
    graph.cells.push(producto);
    (service as any).graph = graph;

    service.loadFromJson({
      classes: [{
        id: 'producto-1',
        name: 'Producto',
        attributes: [
          { name: 'id', type: 'int' },
          { name: 'nombre', type: 'string' },
          { name: 'precio', type: 'decimal' }
        ],
        methods: [{
          name: 'actualizarPrecio',
          parameters: 'valor: decimal',
          returnType: 'void'
        }]
      }],
      relationships: []
    }, true);

    expect(graph.getElements()).toEqual([producto]);
    expect(producto.id).toBe('producto-1');
    expect(producto.position()).toEqual({ x: 125, y: 210 });
    expect(producto.get('attributes').split('\n')).toEqual([
      'id: int',
      'nombre: string',
      'precio: decimal'
    ]);
    expect(producto.get('methods')).toBe(
      'actualizarPrecio(valor: decimal): void;'
    );
  });

  it('restores explicit storage layout and content on the same class identity', () => {
    const service = createService();
    const graph = new FakeGraph();
    const storedClass = new FakeUMLClass({
      id: 'stored-1',
      name: 'Draft',
      position: { x: 10, y: 20 },
      size: { width: 180, height: 110 },
      attributes: 'legacy: string',
      methods: ''
    });
    graph.cells.push(storedClass);
    (service as any).graph = graph;

    service.loadFromJson({
      classes: [{
        id: 'stored-1',
        name: 'Producto',
        position: { x: 320, y: 180 },
        size: { width: 260, height: 190 },
        attributes: [{ name: 'id', type: 'int' }],
        methods: [{ name: 'guardar', returnType: 'void' }]
      }],
      relationships: []
    }, true);

    expect(graph.getElements()).toEqual([storedClass]);
    expect(storedClass.id).toBe('stored-1');
    expect(storedClass.get('name')).toBe('Producto');
    expect(storedClass.get('attributes')).toBe('id: int');
    expect(storedClass.get('methods')).toBe('guardar(): void;');
    expect(storedClass.position()).toEqual({ x: 320, y: 180 });
    expect(storedClass.size()).toEqual({ width: 260, height: 190 });
  });

  it('loadFromJson remote/full_state load does NOT broadcast add_class or duplicate relationship', () => {
    const service = createService();
    const broadcast = (service as any).collab.broadcast as jasmine.Spy;
    (service as any).joint = {
      shapes: { custom: { UMLClass: FakeUMLClass } },
      dia: { Link: FakeLink }
    };

    const graph = new FakeGraph();
    (service as any).graph = graph;
    (service as any).edition = { scheduleAutoResize: () => {} };

    const json = {
      classes: [{ id: 'c2', name: 'RemoteClass' }],
      relationships: [
        { id: 'r1', type: 'association', sourceId: 'c2', targetId: 'c2', labels: [] }
      ]
    };

    service.loadFromJson(json, false, true);

    const addClassBroadcasts = broadcast.calls.allArgs().filter(([msg]: any[]) => msg.t === 'add_class');
    expect(addClassBroadcasts.length).toBe(0);

    const addLinkBroadcasts = broadcast.calls.allArgs().filter(([msg]: any[]) => msg.t === 'add_link');
    expect(addLinkBroadcasts.length).toBe(0);

    const relAddCellCall = graph.addCellCalls.find(call => call.cell.get('id') === 'r1');
    expect(relAddCellCall).toBeTruthy();
    expect(relAddCellCall!.opts).toEqual({ collab: true });
  });
  describe('DiagramApi registration and wrappers', () => {
    let service: any;
    let collabSpy: any;
    let api: any;
    let graph: FakeGraph;
    let broadcast: jasmine.Spy;

    beforeEach(async () => {
      service = createService();
      broadcast = (service as any).collab.broadcast;
      collabSpy = service.collab;
      collabSpy.init = jasmine.createSpy('init');

      collabSpy.registerDiagramApi = jasmine.createSpy('registerDiagramApi').and.callFake((registeredApi: any) => {
        api = registeredApi;
      });

      service.joint = {
        shapes: { custom: { UMLClass: FakeUMLClass } },
        dia: { Link: FakeLink }
      };
      graph = new FakeGraph();
      service.graph = graph;
      service.edition = { scheduleAutoResize: jasmine.createSpy('scheduleAutoResize'), updatePorts: jasmine.createSpy('updatePorts') };
      service.paper = { mock: 'paper' };
      service.exportService = { export: jasmine.createSpy('export') };

      spyOn(localStorage, 'getItem').and.returnValue(null);
      spyOn(localStorage, 'setItem').and.callFake(() => {});

      const el = document.createElement('div');
      try {
        await service.initialize(el, 'test-room');
      } catch (e) {}
    });

    it('A) registered createUmlClass forwards remote=true so remote add_class does not rebroadcast', () => {
      broadcast.calls.reset();
      api.createUmlClass({ id: 'c1', name: 'Test' }, true);
      const addClassBroadcasts = broadcast.calls.allArgs().filter(([msg]: any[]) => msg.t === 'add_class');
      expect(addClassBroadcasts.length).toBe(0);
    });

    it('B) registered loadFromJson forwards (false, true), and remote full_state does not rebroadcast', () => {
      broadcast.calls.reset();
      const json = { classes: [{ id: 'c2', name: 'Test2' }], relationships: [] };
      api.loadFromJson(json, false, true);
      const addClassBroadcasts = broadcast.calls.allArgs().filter(([msg]: any[]) => msg.t === 'add_class');
      expect(addClassBroadcasts.length).toBe(0);
    });

    it('C) registered loadFromJson forwards isStorageLoad=true for backup restoration', () => {
      spyOn(service, 'loadFromJson').and.callThrough();
      const json = { classes: [], relationships: [] };
      api.loadFromJson(json, true);
      expect(service.loadFromJson).toHaveBeenCalledWith(json, true, false);
    });

    it('D) verify scheduleAutoResize receives (model, paper) when attributes change', () => {
      const cls = api.createUmlClass({ id: 'c3' }, true);
      // Trigger the listener we set in createUmlClass
      if (cls.trigger) {
        cls.trigger('change:attrs');
      }
      expect(service.edition.scheduleAutoResize).toHaveBeenCalledWith(cls, service.paper);
    });
  });
});
