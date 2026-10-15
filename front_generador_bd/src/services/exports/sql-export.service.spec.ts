import { SqlExportService } from './sql-export.service';

describe('SqlExportService: entidad intermedia visual para M:N', () => {
  // Caso 5: cuando el frontend ya envía la M:N reemplazada por una clase
  // intermedia real + 2 relaciones 1:N (en vez de una relación con '*' en
  // ambos extremos), el exportador SQL no debe activar también su propia
  // detección M:N: debe tratar la clase intermedia como una clase normal y
  // generar sus 2 FKs vía la rama 1:N ya existente, sin duplicar la tabla.
  it('no duplica la tabla intermedia cuando la M:N ya llega pre-dividida en 2 relaciones 1:N', () => {
    const service = new SqlExportService();
    const uml = {
      classes: [
        { id: 'cls_1', name: 'Estudiante', attributes: [{ name: 'id', type: 'Integer' }, { name: 'nombre', type: 'String' }] },
        { id: 'cls_2', name: 'Curso', attributes: [{ name: 'id', type: 'Integer' }, { name: 'nombre', type: 'String' }] },
        { id: 'cls_3', name: 'Curso_Estudiante', attributes: [], generated: true }
      ],
      relationships: [
        { sourceId: 'cls_1', targetId: 'cls_3', type: 'association', labels: ['1', '0..*'], generated: true },
        { sourceId: 'cls_2', targetId: 'cls_3', type: 'association', labels: ['1', '0..*'], generated: true }
      ]
    };

    const sql = service.exportToSql(uml, 'test_db');

    const createTableOccurrences = (sql.match(/CREATE TABLE Curso_Estudiante/g) || []).length;
    expect(createTableOccurrences).toBe(1);
    expect(sql).toContain('estudiante_id');
    expect(sql).toContain('curso_id');
  });

  // Referencia: la misma relación, pero cruda (labels con '*' en ambos
  // extremos, sin clase intermedia previa), sigue generando su propia tabla
  // intermedia vía la rama M:N existente -- comportamiento sin cambios.
  it('sigue generando la tabla intermedia por su propia detección M:N cuando la relación llega cruda', () => {
    const service = new SqlExportService();
    const uml = {
      classes: [
        { id: 'cls_1', name: 'Estudiante', attributes: [{ name: 'id', type: 'Integer' }] },
        { id: 'cls_2', name: 'Curso', attributes: [{ name: 'id', type: 'Integer' }] }
      ],
      relationships: [
        { sourceId: 'cls_1', targetId: 'cls_2', type: 'association', labels: ['0..*', '0..*'] }
      ]
    };

    const sql = service.exportToSql(uml, 'test_db');

    expect(sql).toContain('CREATE TABLE Estudiante_Curso');
    expect((sql.match(/CREATE TABLE/g) || []).length).toBe(3); // Estudiante + Curso + join table
  });
});
