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
});
