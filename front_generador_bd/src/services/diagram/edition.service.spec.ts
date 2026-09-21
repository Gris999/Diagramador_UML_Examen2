import { EditionService } from './edition.service';

describe('EditionService UML class auto-size', () => {
  function textNode(width: number, height: number = 20): SVGTextContentElement {
    return {
      querySelectorAll: () => [],
      getComputedTextLength: () => width,
      getBBox: () => ({ width, height })
    } as any;
  }

  function createHarness(widths: {
    name: number;
    attributes: number;
    methods: number;
    currentWidth?: number;
  }) {
    const service = new EditionService({} as any, {} as any);
    let size = { width: widths.currentWidth ?? 180, height: 110 };
    const position = { x: 75, y: 90 };
    const attrs = new Map<string, any>();
    const nodes: Record<string, SVGTextContentElement> = {
      '.uml-class-name-text': textNode(widths.name),
      '.uml-class-attrs-text': textNode(widths.attributes),
      '.uml-class-methods-text': textNode(widths.methods)
    };
    const model = {
      isElement: () => true,
      get: (property: string) => property === 'size' ? size : undefined,
      size: () => size,
      position: () => position,
      resize: jasmine.createSpy('resize').and.callFake((width: number, height: number) => {
        size = { width, height };
      }),
      attr: jasmine.createSpy('attr').and.callFake((path: string | object, value?: any) => {
        if (typeof path === 'string') attrs.set(path, value);
      }),
      portProp: jasmine.createSpy('portProp')
    };
    const paper = {
      findViewByModel: () => ({
        findBySelector: (selector: string) => [nodes[selector]]
      })
    };

    return { service, model, paper, attrs, position, getSize: () => size };
  }

  it('preserves the normal width for short class content', () => {
    const harness = createHarness({ name: 70, attributes: 100, methods: 120 });
    const before = { ...harness.position };

    harness.service.autoResizeUmlClass(harness.model, harness.paper);

    expect(harness.getSize()).toEqual({ width: 180, height: 110 });
    expect(harness.attrs.get('.uml-class-attrs-text/textWrap/width')).toBe(160);
    expect(harness.attrs.get('.uml-class-methods-text/textWrap/width')).toBe(160);
    expect(harness.position).toEqual(before);
  });

  it('grows width for a long method and keeps textWrap and position aligned', () => {
    const harness = createHarness({ name: 70, attributes: 100, methods: 260 });
    const before = { ...harness.position };

    harness.service.autoResizeUmlClass(harness.model, harness.paper);

    expect(harness.getSize().width).toBe(280);
    expect(harness.attrs.get('.uml-class-attrs-text/textWrap/width')).toBe(260);
    expect(harness.attrs.get('.uml-class-methods-text/textWrap/width')).toBe(260);
    expect(harness.position).toEqual(before);
  });

  it('grows width for a long attribute without shrinking an existing class', () => {
    const growing = createHarness({ name: 70, attributes: 240, methods: 100 });
    const alreadyWide = createHarness({
      name: 70,
      attributes: 240,
      methods: 100,
      currentWidth: 320
    });

    growing.service.autoResizeUmlClass(growing.model, growing.paper);
    alreadyWide.service.autoResizeUmlClass(alreadyWide.model, alreadyWide.paper);

    expect(growing.getSize().width).toBe(260);
    expect(growing.attrs.get('.uml-class-attrs-text/textWrap/width')).toBe(240);
    expect(alreadyWide.getSize().width).toBe(320);
  });
});
