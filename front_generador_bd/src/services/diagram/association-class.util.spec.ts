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
