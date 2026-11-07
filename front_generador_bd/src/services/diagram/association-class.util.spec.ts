import { findAssociationClassAttachments, resolveAssociationClassesForGenerators } from './association-class.util';

describe('association-class.util', () => {
  const mnVentaProducto = {
    id: 'rel-mn',
    type: 'association',
    sourceId: 'venta-1',
    targetId: 'producto-1',
    labels: ['*', '1..*']
  };
  const linkDetalleVenta = {
    id: 'link-detalle-venta',
    type: 'association-class',
    sourceId: 'detalle-1',
    targetId: 'venta-1',
    labels: []
  };
  const linkDetalleProducto = {
    id: 'link-detalle-producto',
    type: 'association-class',
    sourceId: 'detalle-1',
    targetId: 'producto-1',
    labels: []
  };

  describe('findAssociationClassAttachments', () => {
    it('detecta una clase asociativa enlazada a ambos extremos de una M:N', () => {
      const attachments = findAssociationClassAttachments([
        mnVentaProducto, linkDetalleVenta, linkDetalleProducto
      ]);

      expect(attachments.size).toBe(1);
      expect(attachments.get('rel-mn')).toEqual({
        classId: 'detalle-1',
        linkIds: ['link-detalle-venta', 'link-detalle-producto']
      });
    });

    it('no detecta nada si solo hay un enlace de clase asociativa (falta el segundo extremo)', () => {
      const attachments = findAssociationClassAttachments([mnVentaProducto, linkDetalleVenta]);
      expect(attachments.size).toBe(0);
    });

    it('no detecta nada si los dos enlaces van a clases distintas', () => {
      const otroLink = { ...linkDetalleProducto, id: 'link-otro', sourceId: 'otra-clase' };
      const attachments = findAssociationClassAttachments([mnVentaProducto, linkDetalleVenta, otroLink]);
      expect(attachments.size).toBe(0);
    });

    it('no confunde una clase asociativa cuando el link apunta a uno de los propios extremos de la M:N', () => {
      // Caso patológico: un link 'association-class' entre los dos extremos
      // de la M:N (Venta-Producto), no hacia una tercera clase real.
      const linkVentaProducto = { id: 'link-vp', type: 'association-class', sourceId: 'venta-1', targetId: 'producto-1', labels: [] };
      const attachments = findAssociationClassAttachments([mnVentaProducto, linkVentaProducto, linkDetalleProducto]);
      expect(attachments.size).toBe(0);
    });

    it('ignora relaciones que no son M:N (una sola M:N real en la lista)', () => {
      const unoAUno = { id: 'rel-1a1', type: 'association', sourceId: 'cliente-1', targetId: 'venta-1', labels: ['1', '0..*'] };
      const attachments = findAssociationClassAttachments([
        unoAUno, mnVentaProducto, linkDetalleVenta, linkDetalleProducto
      ]);
      expect(attachments.size).toBe(1);
      expect(attachments.has('rel-mn')).toBeTrue();
    });
  });

  describe('resolveAssociationClassesForGenerators', () => {
    it('reemplaza la M:N + clase asociativa por 2 relaciones 1:N, preservando los atributos de la clase', () => {
      const dto = {
        classes: [
          { id: 'venta-1', name: 'Venta' },
          { id: 'producto-1', name: 'Producto' },
          { id: 'detalle-1', name: 'Detalle', attributes: [{ name: 'entidad', type: 'int' }, { name: 'precioUnitario', type: 'double' }] }
        ],
        relationships: [mnVentaProducto, linkDetalleVenta, linkDetalleProducto]
      };

      const result = resolveAssociationClassesForGenerators(dto);

      // Las clases no cambian (Detalle conserva sus atributos reales).
      expect(result.classes).toBe(dto.classes);
      expect((result.classes[2] as any).attributes).toEqual([
        { name: 'entidad', type: 'int' }, { name: 'precioUnitario', type: 'double' }
      ]);

      // La M:N original y los 2 enlaces de clase asociativa desaparecen del payload de generadores.
      expect(result.relationships.find(r => r.id === 'rel-mn')).toBeUndefined();
      expect(result.relationships.find(r => r.type === 'association-class')).toBeUndefined();

      // En su lugar, exactamente 2 relaciones 1:N hacia la clase asociativa.
      const toDetalle = result.relationships.filter(r => r.targetId === 'detalle-1');
      expect(toDetalle.length).toBe(2);
      expect(toDetalle.map(r => r.sourceId).sort()).toEqual(['producto-1', 'venta-1']);
      toDetalle.forEach(r => expect(r.labels).toEqual(['1', '0..*']));
    });

    it('no modifica nada si no hay ninguna clase asociativa enlazada (compatibilidad con M:N normales)', () => {
      const dto = {
        classes: [{ id: 'a', name: 'A' }, { id: 'b', name: 'B' }],
        relationships: [{ id: 'r1', type: 'association', sourceId: 'a', targetId: 'b', labels: ['0..*', '0..*'] }]
      };

      const result = resolveAssociationClassesForGenerators(dto);
      expect(result).toBe(dto); // misma referencia: early-return sin transformar
    });

    it('deja intactas otras relaciones no relacionadas con la M:N resuelta', () => {
      const otraRel = { id: 'rel-otra', type: 'association', sourceId: 'cliente-1', targetId: 'venta-1', labels: ['1', '0..*'] };
      const dto = {
        classes: [
          { id: 'venta-1', name: 'Venta' }, { id: 'producto-1', name: 'Producto' },
          { id: 'detalle-1', name: 'Detalle', attributes: [] }, { id: 'cliente-1', name: 'Cliente' }
        ],
        relationships: [otraRel, mnVentaProducto, linkDetalleVenta, linkDetalleProducto]
      };

      const result = resolveAssociationClassesForGenerators(dto);
      expect(result.relationships.find(r => r.id === 'rel-otra')).toEqual(otraRel);
      expect(result.relationships.length).toBe(3); // otraRel + 2 patas nuevas
    });
  });
});

// Notación UML (StarUML, Enterprise Architect): la M:N queda directa y desde el medio de su línea sale UN conector
// punteado hacia la clase asociativa; el otro extremo del conector es la propia relación, no una clase.
describe('association-class.util: conector punteado al medio de la línea M:N', () => {
  const mn = { id: 'rel-mn', type: 'association', sourceId: 'estudiante-1', targetId: 'curso-1', labels: ['*', '*'] };
  const punteado = { id: 'assoc-class-link:rel-mn', type: 'association-class', sourceId: 'curso-estudiante', targetId: 'rel-mn', labels: [] };

  it('detecta la clase asociativa cuyo conector punteado apunta a la propia relación M:N', () => {
    const attachments = findAssociationClassAttachments([mn, punteado]);

    expect(attachments.size).toBe(1);
    expect(attachments.get('rel-mn')).toEqual({ classId: 'curso-estudiante', linkIds: ['assoc-class-link:rel-mn'] });
  });

  it('también lo detecta si el conector está dibujado en sentido contrario (de la relación a la clase)', () => {
    const alReves = { ...punteado, sourceId: 'rel-mn', targetId: 'curso-estudiante' };

    expect(findAssociationClassAttachments([mn, alReves]).get('rel-mn')?.classId).toBe('curso-estudiante');
  });

  it('un conector punteado hacia una asociación que no es M:N no cuenta como clase asociativa de M:N', () => {
    const unoAMuchos = { id: 'rel-1n', type: 'association', sourceId: 'a', targetId: 'b', labels: ['1', '0..*'] };
    const alUnoAMuchos = { id: 'p', type: 'association-class', sourceId: 'c', targetId: 'rel-1n', labels: [] };

    expect(findAssociationClassAttachments([unoAMuchos, alUnoAMuchos]).size).toBe(0);
  });

  it('para los generadores la M:N con su clase asociativa pasa a dos relaciones 1:N y desaparecen los conectores punteados', () => {
    const dto = {
      classes: [
        { id: 'estudiante-1', name: 'Estudiante' },
        { id: 'curso-1', name: 'Curso' },
        { id: 'curso-estudiante', name: 'Curso_Estudiante', attributes: [{ name: 'nota', type: 'double' }], generated: true }
      ],
      relationships: [mn, punteado]
    };

    const result = resolveAssociationClassesForGenerators(dto);

    expect(result.relationships.find(r => r.id === 'rel-mn')).toBeUndefined();
    expect(result.relationships.find(r => r.type === 'association-class')).toBeUndefined();
    expect(result.relationships.map(r => [r.sourceId, r.targetId, ...(r.labels || [])]).sort()).toEqual([
      ['curso-1', 'curso-estudiante', '1', '0..*'],
      ['estudiante-1', 'curso-estudiante', '1', '0..*']
    ]);
    expect((result.classes[2] as any).attributes).toEqual([{ name: 'nota', type: 'double' }]);
  });

  it('una M:N reflexiva produce dos relaciones distintas (ids únicos) hacia la clase asociativa', () => {
    const reflexiva = { id: 'rel-amigos', type: 'association', sourceId: 'persona-1', targetId: 'persona-1', labels: ['*', '*'] };
    const conector = { id: 'assoc-class-link:rel-amigos', type: 'association-class', sourceId: 'persona-persona', targetId: 'rel-amigos', labels: [] };
    const dto = {
      classes: [{ id: 'persona-1', name: 'Persona' }, { id: 'persona-persona', name: 'Persona_Persona', generated: true }],
      relationships: [reflexiva, conector]
    };

    const result = resolveAssociationClassesForGenerators(dto);

    expect(result.relationships.length).toBe(2);
    expect(new Set(result.relationships.map(r => r.id)).size).toBe(2);
    result.relationships.forEach(r => {
      expect(r.sourceId).toBe('persona-1');
      expect(r.targetId).toBe('persona-persona');
    });
  });

  it('los generadores no reciben conectores punteados aunque no haya M:N que resolver (uno de sus extremos puede ser una relación)', () => {
    const unoAMuchos = { id: 'rel-1n', type: 'association', sourceId: 'a', targetId: 'b', labels: ['1', '0..*'] };
    const colgado = { id: 'p', type: 'association-class', sourceId: 'c', targetId: 'rel-1n', labels: [] };
    const dto = { classes: [{ id: 'a' }, { id: 'b' }, { id: 'c' }], relationships: [unoAMuchos, colgado] };

    const result = resolveAssociationClassesForGenerators(dto);

    expect(result.relationships).toEqual([unoAMuchos]);
  });

  it('con onlyGenerated solo se resuelven las clases que la herramienta generó; la que dibujó la persona se deja como está', () => {
    const otraMn = { id: 'rel-vp', type: 'association', sourceId: 'venta-1', targetId: 'producto-1', labels: ['*', '*'] };
    const conectorDeLaPersona = { id: 'p-persona', type: 'association-class', sourceId: 'detalle-1', targetId: 'rel-vp', labels: [] };
    const dto = {
      classes: [
        { id: 'estudiante-1' }, { id: 'curso-1' }, { id: 'curso-estudiante', generated: true },
        { id: 'venta-1' }, { id: 'producto-1' }, { id: 'detalle-1' }
      ],
      relationships: [mn, punteado, otraMn, conectorDeLaPersona]
    };

    const result = resolveAssociationClassesForGenerators(dto, { onlyGenerated: true });

    // la generada se expandió...
    expect(result.relationships.find(r => r.id === 'rel-mn')).toBeUndefined();
    expect(result.relationships.find(r => r.id === 'assoc-class-link:rel-mn')).toBeUndefined();
    // ...y la de la persona sigue con su M:N y su conector
    expect(result.relationships.find(r => r.id === 'rel-vp')).toEqual(otraMn);
    expect(result.relationships.find(r => r.id === 'p-persona')).toEqual(conectorDeLaPersona);
  });
});
