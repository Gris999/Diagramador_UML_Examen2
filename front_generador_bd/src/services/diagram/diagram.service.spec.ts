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
});
