import { DiagramExportService } from './diagram-export.service';

describe('DiagramExportService', () => {
  const service = new DiagramExportService();

  function element(id: string) {
    const state: Record<string, unknown> = { name: id, attributes: [], methods: [] };
    return {
      id,
      isElement: () => true,
      isLink: () => false,
      get: (key: string) => state[key],
      position: () => ({ x: 0, y: 0 }),
      size: () => ({ width: 100, height: 60 })
    };
  }

  function link(id: string, source?: string, target?: string) {
    const state: Record<string, unknown> = {
      source: source ? { id: source } : { x: 10, y: 10 },
      target: target ? { id: target } : { x: 50, y: 50 },
      relationType: 'association',
      labels: []
    };
    return { id, isElement: () => false, isLink: () => true, get: (key: string) => state[key] };
  }

  const graphOf = (...cells: unknown[]) => ({ getCells: () => cells });

  function classOf(id: string, fields: Record<string, unknown>) {
    const state: Record<string, unknown> = { name: id, attributes: '', methods: '', ...fields };
    return { id, isElement: () => true, isLink: () => false, get: (key: string) => state[key], position: () => ({ x: 0, y: 0 }), size: () => ({ width: 100, height: 60 }) };
  }

  it('exports the classes and the relationships that join two of them', () => {
    const dto = service.export(graphOf(element('A'), element('B'), link('l1', 'A', 'B')));

    expect(dto.classes.map(c => c.id)).toEqual(['A', 'B']);
    expect(dto.relationships.map(r => [r.id, r.sourceId, r.targetId])).toEqual([['l1', 'A', 'B']]);
  });

  it('leaves out a relationship that has no class at its target, so it is never saved, shared or exported', () => {
    const dto = service.export(graphOf(element('A'), link('suelta', 'A', undefined)));

    expect(dto.relationships).toEqual([]);
  });

  it('leaves out a relationship that has no class at its origin', () => {
    const dto = service.export(graphOf(element('B'), link('suelta', undefined, 'B')));

    expect(dto.relationships).toEqual([]);
  });

  it('keeps the complete relationships when another one is loose', () => {
    const dto = service.export(graphOf(element('A'), element('B'), link('l1', 'A', 'B'), link('suelta', 'A', undefined)));

    expect(dto.relationships.map(r => r.id)).toEqual(['l1']);
  });

  describe('UML 2.5 notation', () => {
    it('reads the visibility of each attribute and method from its line', () => {
      const dto = service.export(graphOf(classOf('A', { attributes: '- saldo: double\n# nombre: string\nid: int', methods: '+ pagar(monto: double): bool;\ncrear();' })));

      expect(dto.classes[0].attributes).toEqual([
        { name: 'saldo', type: 'double', visibility: '-' },
        { name: 'nombre', type: 'string', visibility: '#' },
        { name: 'id', type: 'int' }
      ]);
      expect(dto.classes[0].methods).toEqual([
        { name: 'pagar', parameters: 'monto: double', returnType: 'bool', visibility: '+' },
        { name: 'crear', parameters: '', returnType: '' }
      ]);
    });

    it('only sends the kind when the class is not a plain class', () => {
      const dto = service.export(graphOf(classOf('A', {}), classOf('B', { kind: 'class' }), classOf('C', { kind: 'abstract' }), classOf('D', { kind: 'interface' }), classOf('E', { kind: 'enumeration' })));

      expect(dto.classes.map(c => c.kind)).toEqual([undefined, undefined, 'abstract', 'interface', 'enumeration']);
    });

    it('leaves interfaces and enumerations out of what the code generators receive, with the relationships that touch them', () => {
      const dto = service.export(graphOf(
        classOf('Cliente', {}), classOf('Base', { kind: 'abstract' }), classOf('Pagable', { kind: 'interface' }), classOf('Estado', { kind: 'enumeration' }),
        link('l1', 'Cliente', 'Base'), link('l2', 'Cliente', 'Pagable'), link('l3', 'Cliente', 'Estado')));

      const forCode = service.forCode(dto);

      expect(forCode.classes.map(c => c.id)).toEqual(['Cliente', 'Base']);
      expect(forCode.relationships.map(r => r.id)).toEqual(['l1']);
    });

    it('returns the same diagram when everything is a class that can be generated', () => {
      const dto = service.export(graphOf(classOf('A', {}), classOf('B', { kind: 'abstract' }), link('l1', 'A', 'B')));

      expect(service.forCode(dto)).toBe(dto);
    });
  });
});
