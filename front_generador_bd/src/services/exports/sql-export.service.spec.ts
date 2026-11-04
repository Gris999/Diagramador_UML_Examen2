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

// Relaciones recursivas y repetidas: una tabla no puede tener dos columnas ni dos restricciones con el mismo nombre,
// y la columna que guarda una clave foránea debe ser del mismo tipo que la clave que referencia.
describe('SqlExportService: relaciones recursivas, repetidas y tipo de la clave foránea', () => {
  const service = new SqlExportService();
  const count = (text: string, needle: string) => text.split(needle).length - 1;

  it('una asociación recursiva 1:N agrega una columna padre_id que referencia a la propia tabla', () => {
    const sql = service.exportToSql({
      classes: [{ id: 'emp', name: 'Empleado', attributes: [{ name: 'id', type: 'int' }, { name: 'nombre', type: 'String' }] }],
      relationships: [{ id: 'r1', sourceId: 'emp', targetId: 'emp', type: 'association', labels: ['0..1', '0..*'] }]
    }, 'test_db');

    expect(sql).toContain('ADD COLUMN padre_id INT');
    expect(sql).toContain('FOREIGN KEY (padre_id) REFERENCES Empleado(id)');
    expect(sql).not.toContain('empleado_id');
  });

  it('dos relaciones entre las mismas tablas no repiten la columna ni la restricción', () => {
    const sql = service.exportToSql({
      classes: [
        { id: 'aer', name: 'Aeropuerto', attributes: [{ name: 'id', type: 'int' }] },
        { id: 'vue', name: 'Vuelo', attributes: [{ name: 'id', type: 'int' }] }
      ],
      relationships: [
        { id: 'r1', sourceId: 'aer', targetId: 'vue', type: 'association', labels: ['1', '0..*'] },
        { id: 'r2', sourceId: 'aer', targetId: 'vue', type: 'association', labels: ['1', '0..*'] }
      ]
    }, 'test_db');

    expect(count(sql, 'ADD COLUMN aeropuerto_id ')).toBe(1);
    expect(count(sql, 'ADD COLUMN aeropuerto_2_id ')).toBe(1);
    expect(sql).toContain('ADD CONSTRAINT fk_vuelo_aeropuerto FOREIGN KEY');
    expect(sql).toContain('ADD CONSTRAINT fk_vuelo_aeropuerto_2 FOREIGN KEY');
  });

  it('una M:N recursiva cruda crea la tabla intermedia con las columnas origen_id y destino_id', () => {
    const sql = service.exportToSql({
      classes: [{ id: 'per', name: 'Persona', attributes: [{ name: 'id', type: 'int' }] }],
      relationships: [{ id: 'r1', sourceId: 'per', targetId: 'per', type: 'association', labels: ['*', '*'] }]
    }, 'test_db');

    expect(sql).toContain('CREATE TABLE Persona_Persona');
    expect(sql).toContain('origen_id INT NOT NULL');
    expect(sql).toContain('destino_id INT NOT NULL');
    expect(sql).toContain('PRIMARY KEY (origen_id, destino_id)');
    expect(sql).toContain('FOREIGN KEY (origen_id) REFERENCES Persona(id)');
    expect(sql).toContain('FOREIGN KEY (destino_id) REFERENCES Persona(id)');
  });

  it('las dos relaciones que llegan a la clase asociativa de una M:N recursiva dan dos columnas distintas', () => {
    const sql = service.exportToSql({
      classes: [
        { id: 'per', name: 'Persona', attributes: [{ name: 'id', type: 'int' }] },
        { id: 'j', name: 'Persona_Persona', attributes: [{ name: 'id', type: 'int' }] }
      ],
      relationships: [
        { id: 'l1', sourceId: 'per', targetId: 'j', type: 'association', labels: ['1', '0..*'] },
        { id: 'l2', sourceId: 'per', targetId: 'j', type: 'association', labels: ['1', '0..*'] }
      ]
    }, 'test_db');

    expect(count(sql, 'ADD COLUMN persona_id ')).toBe(1);
    expect(count(sql, 'ADD COLUMN persona_2_id ')).toBe(1);
  });

  it('la columna de la clave foránea es del mismo tipo que la clave que referencia', () => {
    const sql = service.exportToSql({
      classes: [
        { id: 'usu', name: 'Usuario', attributes: [{ name: 'codigo', type: 'String' }] },
        { id: 'ped', name: 'Pedido', attributes: [{ name: 'id', type: 'int' }] },
        { id: 'pro', name: 'Producto', attributes: [] }
      ],
      relationships: [
        { id: 'r1', sourceId: 'usu', targetId: 'ped', type: 'association', labels: ['1', '0..*'] },
        { id: 'r2', sourceId: 'pro', targetId: 'ped', type: 'association', labels: ['1', '0..*'] }
      ]
    }, 'test_db');

    expect(sql).toContain('ADD COLUMN usuario_id VARCHAR(255)');
    expect(sql).toContain('ADD COLUMN producto_id UUID'); // una tabla sin atributos tiene `id UUID PRIMARY KEY`
  });
});
