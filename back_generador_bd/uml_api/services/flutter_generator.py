import json
import os
from pathlib import Path
import unicodedata

class FlutterCRUDGenerator:
    def __init__(self, uml_json):
        self.uml_json = uml_json
        self.classes = uml_json.get('classes', [])
        self.relationships = uml_json.get('relationships', [])
        self.parsed_relationships = self._parse_relationships()

    def _parse_relationships(self):
      """Convierte relaciones UML en vínculos lógicos entre clases - MISMA LÓGICA QUE ProjectGenerator.java"""
      relations_map = {cls['id']: cls['name'] for cls in self.classes}
      parsed = []
      
      # Detectar relaciones ManyToMany para crear entidades intermedias
      many_to_many_relations = []

      for rel in self.relationships:
          src = relations_map.get(rel.get('sourceId'))
          tgt = relations_map.get(rel.get('targetId'))
          if not src or not tgt:
              continue
          
          rtype = rel.get("type", "").lower()
          labels = rel.get("labels", [])

          if rtype == "generalization":
              parsed.append({"from": src, "to": tgt, "kind": "inherits"})
          elif rtype in ["association", "aggregation", "composition", "dependency"]:
              # 1) Normalizar etiquetas (vacías -> valores por defecto)
              raw_source = labels[0].strip() if len(labels) > 0 and labels[0] else ""
              raw_target = labels[1].strip() if len(labels) > 1 and labels[1] else ""
              
              # Por defecto: source tiene multiplicidad *, target tiene multiplicidad 1
              source_card = raw_source if raw_source else "*"
              target_card = raw_target if raw_target else "1"
              
              # 2) Regla por defecto para dependency SIN multiplicidades
              if rtype == "dependency":
                  no_multis = (not raw_source and not raw_target)
                  if no_multis:
                      # Por defecto: muchos dependientes (*) apuntan a un principal (1)
                      source_card = "*"
                      target_card = "1"
              
              # 3) Detectar "many"
              source_is_many = "*" in source_card
              target_is_many = "*" in target_card
              
              # Prevenir que dependency sea tratado como 1..1
              if rtype == "dependency" and not source_is_many and not target_is_many:
                  source_is_many = True
                  target_is_many = False
              
              # 4) Aplicar lógica según multiplicidades (igual que ProjectGenerator.java)
              if source_is_many and target_is_many:
                  # *..* => ManyToMany - se generará entidad intermedia
                  first_entity = src if src < tgt else tgt
                  second_entity = tgt if src < tgt else src
                  intermediate_name = first_entity + second_entity
                  
                  many_to_many_relations.append({
                      "from": src,
                      "to": tgt,
                      "intermediate": intermediate_name,
                      "first": first_entity,
                      "second": second_entity
                  })
                  
                  # Agregar relaciones OneToMany desde ambas entidades originales hacia la intermedia
                  parsed.append({"from": src, "to": intermediate_name, "kind": "one_to_many"})
                  parsed.append({"from": tgt, "to": intermediate_name, "kind": "one_to_many"})
              elif source_is_many and not target_is_many:
                  # source *..1 target => Source tiene ManyToOne hacia Target
                  parsed.append({"from": src, "to": tgt, "kind": "many_to_one"})
              elif not source_is_many and not target_is_many:
                  # 1..1 => OneToOne
                  is_composition = rtype == "composition"
                  parsed.append({"from": src, "to": tgt, "kind": "one_to_one", "composition": is_composition})
              elif not source_is_many and target_is_many:
                  # source 1..* target => Source tiene OneToMany hacia Target
                  parsed.append({"from": src, "to": tgt, "kind": "one_to_many"})
              
              # === Lado INVERSO (Target) ===
              if not target_is_many and source_is_many:
                  # source *..1 target => Target tiene OneToMany hacia Source (relación inversa)
                  parsed.append({"from": tgt, "to": src, "kind": "one_to_many"})
              elif target_is_many and not source_is_many:
                  # source 1..* target => Target tiene ManyToOne hacia Source (relación inversa)
                  parsed.append({"from": tgt, "to": src, "kind": "many_to_one"})

      return parsed
        
    def generate_project(self, output_dir="generated_flutter_app"):
        """Genera el proyecto Flutter completo"""
        base_path = Path(output_dir)
        
        # Crear estructura de carpetas
        self._create_folder_structure(base_path)
        
        # Generar archivos base
        self._generate_pubspec(base_path)
        self._generate_config(base_path)
        
        # Detectar entidades intermedias de ManyToMany
        intermediate_entities = self._detect_intermediate_entities()
        original_classes = self.classes
        original_relationships = self.parsed_relationships

        # Las clases intermedias solo se agregan temporalmente para que las vistas
        # de detalle de las entidades originales puedan resolver sus relaciones.
        # Sus archivos se generan exclusivamente con los generadores especializados.
        temporary_classes = []
        temporary_relationships = []
        for intermediate in intermediate_entities:
            intermediate_name = intermediate['name']
            temporary_classes.append({
                'id': f'intermediate_{intermediate_name}',
                'name': intermediate_name,
                'attributes': [{'name': 'id', 'type': 'Long'}],
                'is_intermediate': True,
            })
            for entity_name in (
                intermediate['first_entity'],
                intermediate['second_entity'],
            ):
                temporary_relationships.append({
                    "from": intermediate_name,
                    "to": entity_name,
                    "kind": "many_to_one",
                })

        self.classes = [*original_classes, *temporary_classes]
        self.parsed_relationships = [
            *original_relationships,
            *temporary_relationships,
        ]

        try:
            # Generar modelos, servicios y vistas solo para las clases UML originales.
            for clase in original_classes:
                self._generate_model(base_path, clase)
                self._generate_service(base_path, clase)
                self._generate_list_view(base_path, clase)
                self._generate_form_view(base_path, clase)
                self._generate_detail_view(base_path, clase)

            # Generar las entidades intermedias exactamente una vez.
            for intermediate in intermediate_entities:
                self._generate_intermediate_model(base_path, intermediate)
                self._generate_intermediate_service(base_path, intermediate)
                self._generate_intermediate_list_view(base_path, intermediate)
                self._generate_intermediate_form_view(base_path, intermediate)
                self._generate_intermediate_detail_view(base_path, intermediate)

            # Generar la infraestructura del asistente (solo entidades UML
            # originales; las entidades intermedias M:N quedan fuera del P0).
            self._generate_app_schema(base_path, original_classes)
            self._generate_business_command(base_path)
            self._generate_entity_service_adapter(base_path)
            self._generate_command_parser(base_path)
            self._generate_command_validator(base_path)
            self._generate_entity_service_registry(base_path, original_classes)
            self._generate_command_router(base_path)
            self._generate_voice_input_controller(base_path)
            self._generate_assistant_view(base_path)
            self._generate_assistant_tests(base_path, original_classes)

            self._generate_main(base_path, intermediate_entities)
            self._generate_widget_test(base_path)
            self._generate_routes(base_path)
            self._generate_database_helper(base_path)
        finally:
            # Reutilizar la misma instancia debe producir el mismo proyecto sin
            # acumular clases o relaciones sintéticas.
            self.classes = original_classes
            self.parsed_relationships = original_relationships
        
        print(f"✅ Proyecto Flutter generado en: {output_dir}")
        
    def _detect_intermediate_entities(self):
        """Detecta entidades intermedias generadas por relaciones ManyToMany"""
        intermediate_entities = []
        processed = set()
        
        for rel in self.relationships:
            if rel.get("type", "").lower() not in ["association", "aggregation", "composition", "dependency"]:
                continue
            
            src = next((c['name'] for c in self.classes if c['id'] == rel.get('sourceId')), None)
            tgt = next((c['name'] for c in self.classes if c['id'] == rel.get('targetId')), None)
            
            if not src or not tgt:
                continue
            
            labels = rel.get("labels", [])
            source_card = labels[0].strip() if len(labels) > 0 else ""
            target_card = labels[1].strip() if len(labels) > 1 else ""
            
            source_is_many = "*" in source_card
            target_is_many = "*" in target_card
            
            if source_is_many and target_is_many:
                # Ordenar alfabéticamente para consistencia
                first_entity = src if src < tgt else tgt
                second_entity = tgt if src < tgt else src
                intermediate_name = first_entity + second_entity
                
                # Evitar duplicados
                if intermediate_name in processed:
                    continue
                processed.add(intermediate_name)
                
                intermediate_entities.append({
                    "name": intermediate_name,
                    "first_entity": first_entity,
                    "second_entity": second_entity
                })
        
        return intermediate_entities
    
    def _create_folder_structure(self, base_path):
        """Crea la estructura de carpetas del proyecto"""
        folders = [
            'lib/database',
            'lib/models',
            'lib/services',
            'lib/views',
            'lib/widgets',
            'lib/assistant',
            'test',
            'test/assistant',
        ]
        for folder in folders:
            (base_path / folder).mkdir(parents=True, exist_ok=True)
    
    def _generate_pubspec(self, base_path):
        """Genera el archivo pubspec.yaml"""
        content = """name: generated_crud_app
description: Aplicación Flutter generada automáticamente con CRUDs
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.12.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.2
  http: ^1.1.0
  provider: ^6.0.5
  sqflite: ^2.4.4
  path: ^1.9.1
  speech_to_text: ^7.5.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^2.0.0

flutter:
  uses-material-design: true
"""
        with open(base_path / 'pubspec.yaml', "w", encoding="utf-8") as f:
          f.write(self._sanitize(content))    
    def _map_sqlite_type(self, uml_type):
        """Mapea tipos UML a columnas SQLite. Date/String->TEXT, int/Long->INTEGER, double->REAL, bool->INTEGER"""
        type_map = {
            'string': 'TEXT',
            'String': 'TEXT',
            'int': 'INTEGER',
            'Int': 'INTEGER',
            'Long': 'INTEGER',
            'double': 'REAL',
            'Double': 'REAL',
            'bool': 'INTEGER',
            'Boolean': 'INTEGER',
            'Date': 'TEXT',
            'DateTime': 'TEXT',
        }
        return type_map.get(uml_type, 'TEXT')

    def _generate_database_helper(self, base_path):
        create_tables = []
        bool_columns_map = {}

        for clase in self.classes:
            table_name = self._to_snake_case(clase['name'])
            is_intermediate = clase.get('is_intermediate', False)

            columns = []
            bool_cols = []

            if is_intermediate:
                columns.append("id INTEGER PRIMARY KEY")
                relationships = [r for r in self.parsed_relationships if r["from"] == clase['name']]

                for rel in relationships:
                    if rel["kind"] == "many_to_one":
                        rel_snake = self._to_snake_case(rel['to'])
                        fk_col = f"{rel_snake}id"
                        columns.append(f"{fk_col} INTEGER")
            else:
                relationships = [r for r in self.parsed_relationships if r["from"] == clase['name']]

                parent_class = None
                for rel in relationships:
                    if rel["kind"] == "inherits":
                        parent_class = rel["to"]
                        break

                def get_all_attributes(class_name):
                    attrs = []
                    current_class = next((c for c in self.classes if c['name'] == class_name), None)
                    if current_class:
                        parent_rels = [r for r in self.parsed_relationships if r["from"] == class_name and r["kind"] == "inherits"]
                        if parent_rels:
                            attrs.extend(get_all_attributes(parent_rels[0]["to"]))
                        existing_attr_names = {attr['name'].lower() for attr in attrs}
                        for attr in current_class.get('attributes', []):
                            if attr['name'].lower() not in existing_attr_names:
                                attrs.append(attr)
                    return attrs

                all_attrs = get_all_attributes(clase['name'])

                for i, attr in enumerate(all_attrs):
                    col_name = self._to_backend_json_key(attr['name'])
                    sql_type = self._map_sqlite_type(attr['type'])

                    if i == 0:
                        columns.append(f"{col_name} {sql_type} PRIMARY KEY")
                    else:
                        columns.append(f"{col_name} {sql_type}")

                    if sql_type == 'INTEGER' and attr['type'] in ['bool', 'Boolean']:
                        bool_cols.append(f"'{col_name}'")

                def get_all_relations(class_name):
                    rels = []
                    for r in self.parsed_relationships:
                        if r["from"] == class_name and r["kind"] == "inherits":
                            rels.extend(get_all_relations(r["to"]))
                            break
                    for r in self.parsed_relationships:
                        if r["from"] == class_name and r["kind"] in ["many_to_one", "one_to_one"]:
                            rels.append(r)
                    return rels

                all_rels = get_all_relations(clase['name'])
                added_rels = set()
                for rel in all_rels:
                    if rel['to'] not in added_rels:
                        fk_field = f"{self._to_snake_case(rel['to'])}Id"
                        fk_col = self._to_backend_json_key(fk_field)
                        columns.append(f"{fk_col} TEXT")
                        added_rels.add(rel['to'])

            cols_str = ",\n        ".join(columns)
            create_tables.append(f"    await db.execute('''\n      CREATE TABLE {table_name} (\n        {cols_str}\n      )\n    ''');")
            if bool_cols:
                bool_columns_map[table_name] = f"'{table_name}': [{', '.join(bool_cols)}]"

        bool_map_str = ",\n    ".join(bool_columns_map.values())
        tables_str = "\n".join(create_tables)

        content = f"""import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:flutter/foundation.dart';

class DatabaseHelper {{
  static final DatabaseHelper instance = DatabaseHelper._init();
  static Database? _database;
  DatabaseHelper._init();

  final Map<String, List<String>> _boolColumns = {{
    {bool_map_str}
  }};

  Future<Database> get database async {{
    if (_database != null) return _database!;
    _database = await _initDB('app_database.db');
    return _database!;
  }}

  Future<Database> _initDB(String filePath) async {{
    if (kIsWeb) throw Exception("SQLite is not supported on Web");
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);
    return await openDatabase(path, version: 1, onCreate: _createDB);
  }}

  Future _createDB(Database db, int version) async {{
{tables_str}
  }}

  Map<String, dynamic> _normalizeForDb(String table, Map<String, dynamic> map) {{
    final result = Map<String, dynamic>.from(map);
    if (_boolColumns.containsKey(table)) {{
      for (var col in _boolColumns[table]!) {{
        if (result.containsKey(col) && result[col] != null) {{
          result[col] = result[col] == true || result[col] == 1 || result[col] == 'true' ? 1 : 0;
        }}
      }}
    }}
    return result;
  }}

  Future<void> upsert(String table, Map<String, dynamic> map, String pkColumn) async {{
    if (kIsWeb) return;
    final db = await instance.database;
    final normalized = _normalizeForDb(table, map);
    await db.insert(table, normalized, conflictAlgorithm: ConflictAlgorithm.replace);
  }}

  Future<List<Map<String, dynamic>>> getAll(String table) async {{
    if (kIsWeb) return [];
    final db = await instance.database;
    return await db.query(table);
  }}

  Future<Map<String, dynamic>?> getById(String table, String pkColumn, String id) async {{
    if (kIsWeb) return null;
    final db = await instance.database;
    final res = await db.query(table, where: '$pkColumn = ?', whereArgs: [id]);
    if (res.isNotEmpty) return res.first;
    return null;
  }}

  Future<Map<String, dynamic>> insertLocal(String table, Map<String, dynamic> map, String pkColumn, bool isNumericPk) async {{
    if (kIsWeb) throw Exception("Offline persistence not supported on Web");
    final db = await instance.database;
    final normalized = _normalizeForDb(table, map);

    if (isNumericPk) {{
      final currentPk = normalized[pkColumn];
      if (currentPk == null || currentPk == 0 || currentPk == '0') {{
        final res = await db.rawQuery('SELECT MIN($pkColumn) as min_id FROM $table WHERE $pkColumn < 0');
        int nextId = -1;
        if (res.isNotEmpty && res.first['min_id'] != null) {{
          nextId = (res.first['min_id'] as int) - 1;
        }}
        normalized[pkColumn] = nextId;
      }}
    }}

    await db.insert(table, normalized, conflictAlgorithm: ConflictAlgorithm.replace);
    return normalized;
  }}

  Future<Map<String, dynamic>> updateLocal(String table, Map<String, dynamic> map, String pkColumn, String id) async {{
    if (kIsWeb) throw Exception("Offline persistence not supported on Web");
    final db = await instance.database;
    final normalized = _normalizeForDb(table, map);
    await db.update(table, normalized, where: '$pkColumn = ?', whereArgs: [id]);
    return normalized;
  }}

  Future<void> deleteLocal(String table, String pkColumn, String id) async {{
    if (kIsWeb) return;
    final db = await instance.database;
    await db.delete(table, where: '$pkColumn = ?', whereArgs: [id]);
  }}
}}
"""
        (base_path / 'lib' / 'database').mkdir(parents=True, exist_ok=True)
        (base_path / 'lib' / 'database' / 'database_helper.dart').write_text(self._sanitize(content), encoding="utf-8", newline="\n")

    def _generate_main(self, base_path, intermediate_entities=[]):
        """Genera el archivo main.dart"""
        entity_names = [
            c['name'] for c in self.classes
            if not c.get('is_intermediate', False)
        ]
        entity_names.extend(ie['name'] for ie in intermediate_entities)
        imports = [
            f"import 'views/{self._to_snake_case(name)}_list_view.dart';"
            for name in dict.fromkeys(entity_names)
        ]
        imports_str = '\n'.join(imports)
        
        content = f"""import 'package:flutter/material.dart';
import 'assistant/assistant_view.dart';
{imports_str}

void main() {{
  runApp(const MyApp());
}}

class MyApp extends StatelessWidget {{
  const MyApp({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: 'CRUD Generator',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }}
}}

class HomePage extends StatelessWidget {{
  const HomePage({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: const Text('Gestión de Clases'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
{self._generate_home_cards(intermediate_entities)}
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {{
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const AssistantView()),
          );
        }},
        icon: const Icon(Icons.mic),
        label: const Text('Asistente'),
      ),
    );
  }}
}}
"""
        (base_path / 'lib' / 'main.dart').write_text(self._sanitize(content), encoding="utf-8", newline="\n")

    def _generate_widget_test(self, base_path):
        """Genera una prueba mínima que no depende del backend."""
        content = """import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/main.dart';

void main() {
  testWidgets('shows the generated CRUD home page', (tester) async {
    await tester.pumpWidget(const MyApp());

    expect(find.text('Gestión de Clases'), findsOneWidget);
  });
}
"""
        (base_path / 'test' / 'widget_test.dart').write_text(
            self._sanitize(content),
            encoding="utf-8",
            newline="\n",
        )
    
    def _generate_home_cards(self, intermediate_entities=[]):
        """Genera las tarjetas de navegación en el home"""
        cards = []
        
        # Obtener nombres de entidades intermedias para excluirlas
        intermediate_names = {ie['name'] for ie in intermediate_entities}
        
        # Tarjetas para clases originales (excluyendo entidades intermedias)
        for clase in self.classes:
            # Saltar si es una entidad intermedia
            if clase.get('is_intermediate', False) or clase['name'] in intermediate_names:
                continue
            name = clase['name']
            snake_name = self._to_snake_case(name)
            cards.append(f"""          Card(
            margin: const EdgeInsets.only(bottom: 16),
            child: ListTile(
              leading: const Icon(Icons.table_chart, size: 40),
              title: Text('{name}'),
              subtitle: Text('Gestionar {name}'),
              trailing: const Icon(Icons.arrow_forward_ios),
              onTap: () {{
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => {name}ListView(),
                  ),
                );
              }},
            ),
          )""")
        
        # Tarjetas para entidades intermedias (relaciones)
        for ie in intermediate_entities:
            name = ie['name']
            snake_name = self._to_snake_case(name)
            cards.append(f"""          Card(
            margin: const EdgeInsets.only(bottom: 16),
            color: Colors.purple.shade50,
            child: ListTile(
              leading: const Icon(Icons.link, size: 40, color: Colors.purple),
              title: Text('{name}'),
              subtitle: Text('Gestionar relación {ie["first_entity"]} - {ie["second_entity"]}'),
              trailing: const Icon(Icons.arrow_forward_ios),
              onTap: () {{
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => {name}ListView(),
                  ),
                );
              }},
            ),
          )""")
        
        return ',\n'.join(cards)
    
    def _generate_config(self, base_path):
        """Genera el archivo de configuración para el API"""
        content = """class ApiConfig {
  // Cambia esta URL según tu backend
  static const String baseUrl = 'http://localhost:9000/api';
  
  // Para Android Emulator, usa: 'http://10.0.2.2:9000/api'
  // Para iOS Simulator, usa: 'http://localhost:9000/api'
  // Para dispositivo físico, usa la IP de tu computadora: 'http://192.168.x.x:9000/api'
}
"""
        (base_path / 'lib' / 'config.dart').write_text(content, encoding="utf-8", newline="\n")
    
    def _generate_model(self, base_path, clase):
      """Genera el modelo de datos, con imports y parsing de relaciones"""
      name = clase['name']
      relationships = self.parsed_relationships
      attributes = clase.get('attributes', [])

      # Detectar clase padre (herencia)
      parent_class = None
      for rel in relationships:
          if rel["from"] == name and rel["kind"] == "inherits":
              parent_class = rel["to"]
              break

      # IMPORTANTE: El primer atributo es la PK
      # Detectar tipo de PK (numérica o string)
      pk_attr = attributes[0] if attributes and not parent_class else None
      pk_type = None
      pk_name = None
      is_numeric_pk = False
      
      if pk_attr:
          pk_name = pk_attr['name']
          pk_type = self._convert_type(pk_attr['type'])
          is_numeric_pk = pk_type in ['int', 'double']

      # Detectar modelos relacionados para importar
      related_models = set()
      if parent_class:
          related_models.add(parent_class)
      
      # Importar modelos para todas las relaciones (necesarios para parsear objetos anidados)
      for rel in relationships:
          if rel["from"] == name and rel["kind"] in ["many_to_one", "one_to_one", "one_to_many"]:
              related_models.add(rel["to"])

      imports = "\n".join([
          f"import '{self._to_snake_case(model)}.dart';"
          for model in sorted(related_models)
      ])

      # Clase extends o normal
      class_declaration = f"class {name} extends {parent_class}" if parent_class else f"class {name}"

      # Propiedades (solo las propias, NO las heredadas)
      properties = []
      
      # Función recursiva para obtener TODOS los nombres de atributos del padre
      def get_all_parent_attribute_names(parent_class_name):
          parent_attr_names = set()
          parent = next((c for c in self.classes if c['name'] == parent_class_name), None)
          if parent:
              # Buscar si el padre también tiene padre
              for rel in relationships:
                  if rel["from"] == parent_class_name and rel["kind"] == "inherits":
                      # Recursivamente obtener atributos del abuelo
                      parent_attr_names.update(get_all_parent_attribute_names(rel["to"]))
              # Agregar atributos propios del padre
              for attr in parent.get('attributes', []):
                  parent_attr_names.add(attr['name'].lower())
          return parent_attr_names
      
      # Si NO tiene padre, agregar todos los atributos normalmente
      # Si SÍ tiene padre, NO agregar atributos que ya estén en el padre
      parent_attr_names = get_all_parent_attribute_names(parent_class) if parent_class else set()
      
      if not parent_class:
          # Sin herencia: agregar todos los atributos incluyendo PK
          for attr in attributes:
              dart_type = self._convert_type(attr['type'])
              properties.append(f"  final {dart_type} {attr['name']};")
      else:
          # Con herencia: NO agregar atributos que ya existen en el padre (recursivamente)
          for attr in attributes:
              # Comparar nombre del atributo con todos los atributos del padre
              if attr['name'].lower() not in parent_attr_names:
                  dart_type = self._convert_type(attr['type'])
                  properties.append(f"  final {dart_type} {attr['name']};")

      # Relaciones - ManyToOne/OneToOne: ID (required) + objeto completo (opcional para leer). OneToMany: lista completa
      # Normalizar nombres eliminando guiones bajos y convirtiendo a lowercase para comparación
      existing_attr_names = {attr['name'].lower().replace('_', '') for attr in attributes}
      rel_fields = []
      for rel in relationships:
          if rel["from"] == name:
              if rel["kind"] == "many_to_one":
                  # ManyToOne: ID (para enviar) + objeto completo opcional (para leer del GET)
                  field_name = f"{self._to_snake_case(rel['to'])}Id"
                  normalized_field = field_name.lower().replace('_', '')
                  if normalized_field not in existing_attr_names:
                      rel_fields.append(f"  final String {field_name};")
                  # Agregar también el objeto completo (nullable, solo para lectura)
                  obj_field_name = self._to_snake_case(rel['to'])
                  normalized_obj = obj_field_name.lower().replace('_', '')
                  if normalized_obj not in existing_attr_names:
                      rel_fields.append(f"  final {rel['to']}? {obj_field_name};")
              elif rel["kind"] == "one_to_one":
                  # OneToOne: ID (para enviar) + objeto completo opcional (para leer del GET)
                  field_name = f"{self._to_snake_case(rel['to'])}Id"
                  normalized_field = field_name.lower().replace('_', '')
                  if normalized_field not in existing_attr_names:
                      rel_fields.append(f"  final String {field_name};")
                  # Agregar también el objeto completo (nullable, solo para lectura)
                  obj_field_name = self._to_snake_case(rel['to'])
                  normalized_obj = obj_field_name.lower().replace('_', '')
                  if normalized_obj not in existing_attr_names:
                      rel_fields.append(f"  final {rel['to']}? {obj_field_name};")
              elif rel["kind"] == "one_to_many":
                  # OneToMany: Lista de objetos completos (solo para lectura desde GET)
                  # El backend devuelve la lista anidada en GET, pero NO se envía en POST/PUT
                  field_name = self._to_snake_case(rel['to'])
                  normalized_field = field_name.lower().replace('_', '')
                  if normalized_field not in existing_attr_names:
                      rel_fields.append(f"  final List<{rel['to']}> {field_name};")
      properties.extend(rel_fields)

      # Constructor con super() si hay herencia
      constructor_params_list = []
      super_params_list = []
      
      # Si tiene padre, necesitamos pasar sus parámetros al super()
      if parent_class:
          # Función recursiva para obtener TODOS los atributos del padre (incluyendo PK)
          def get_all_parent_attributes(class_name):
              attrs = []
              current_class = next((c for c in self.classes if c['name'] == class_name), None)
              if current_class:
                  # Buscar si esta clase también tiene padre
                  parent_rels = [r for r in relationships if r["from"] == class_name and r["kind"] == "inherits"]
                  if parent_rels:
                      parent_name = parent_rels[0]["to"]
                      attrs.extend(get_all_parent_attributes(parent_name))
                  # Agregar atributos propios del padre
                  attrs.extend(current_class.get('attributes', []))
              return attrs
          
          # Función para obtener relaciones del padre
          def get_all_parent_relationships(class_name):
              rels = []
              # Buscar si esta clase tiene padre primero
              parent_rels = [r for r in relationships if r["from"] == class_name and r["kind"] == "inherits"]
              if parent_rels:
                  # Recursivamente obtener relaciones del abuelo
                  rels.extend(get_all_parent_relationships(parent_rels[0]["to"]))
              
              # Agregar relaciones propias de esta clase (excepto herencia)
              for rel in relationships:
                  if rel["from"] == class_name and rel["kind"] != "inherits":
                      rels.append(rel)
              return rels
          
          # Obtener TODOS los atributos del padre (recursivamente)
          parent_attrs = get_all_parent_attributes(parent_class)
          parent_relationships = get_all_parent_relationships(parent_class)
          
          # Agregar parámetros del padre para el super()
          for attr in parent_attrs:
              attr_name = attr['name']
              attr_type = self._convert_type(attr['type'])
              super_params_list.append(f"{attr_name}: {attr_name}")
              constructor_params_list.append(f"required {attr_type} {attr_name}")
          
          # Agregar relaciones del padre al constructor (SOLO IDs)
          parent_existing_attrs = {attr['name'].lower().replace('_', '') for attr in parent_attrs}
          for rel in parent_relationships:
              if rel["kind"] == "many_to_one":
                  # ManyToOne: agregar el ID
                  field_name = f"{self._to_snake_case(rel['to'])}Id"
                  normalized = field_name.lower().replace('_', '')
                  if normalized not in parent_existing_attrs:
                      super_params_list.append(f"{field_name}: {field_name}")
                      constructor_params_list.append(f"required String {field_name}")
              elif rel["kind"] == "one_to_one":
                  # OneToOne: agregar el ID
                  field_name = f"{self._to_snake_case(rel['to'])}Id"
                  normalized = field_name.lower().replace('_', '')
                  if normalized not in parent_existing_attrs:
                      super_params_list.append(f"{field_name}: {field_name}")
                      constructor_params_list.append(f"required String {field_name}")
              # OneToMany: NO se agrega al constructor
      else:
          # Si no tiene padre, los atributos se agregan abajo con this.
          pass
      
      # Agregar parámetros propios (con this. si no hay padre, sin this. si hay padre)
      # Si hay herencia, NO agregar atributos que ya estén en el padre
      for attr in attributes:
          # Verificar si este atributo NO está en el padre
          if parent_class and attr['name'].lower() in parent_attr_names:
              continue  # Saltar atributos heredados
          constructor_params_list.append(f"required this.{attr['name']}")
      
      # Normalizar para comparación
      existing_attr_names_normalized = {attr['name'].lower().replace('_', '') for attr in attributes}
      
      for rel in relationships:
          if rel["from"] == name:
              if rel["kind"] == "many_to_one":
                  # Agregar FK (ID) para relaciones ManyToOne (required)
                  field_name = f"{self._to_snake_case(rel['to'])}Id"
                  normalized_field = field_name.lower().replace('_', '')
                  if normalized_field not in existing_attr_names_normalized:
                      constructor_params_list.append(f"required this.{field_name}")
                  # Agregar objeto completo (opcional, default null)
                  obj_field_name = self._to_snake_case(rel['to'])
                  normalized_obj = obj_field_name.lower().replace('_', '')
                  if normalized_obj not in existing_attr_names_normalized:
                      constructor_params_list.append(f"this.{obj_field_name}")
              elif rel["kind"] == "one_to_one":
                  # Agregar FK (ID) para relaciones OneToOne (required)
                  field_name = f"{self._to_snake_case(rel['to'])}Id"
                  normalized_field = field_name.lower().replace('_', '')
                  if normalized_field not in existing_attr_names_normalized:
                      constructor_params_list.append(f"required this.{field_name}")
                  # Agregar objeto completo (opcional, default null)
                  obj_field_name = self._to_snake_case(rel['to'])
                  normalized_obj = obj_field_name.lower().replace('_', '')
                  if normalized_obj not in existing_attr_names_normalized:
                      constructor_params_list.append(f"this.{obj_field_name}")
              elif rel["kind"] == "one_to_many":
                  # OneToMany: Lista opcional (vacía por defecto para POST/PUT, poblada en GET)
                  field_name = self._to_snake_case(rel['to'])
                  normalized_field = field_name.lower().replace('_', '')
                  if normalized_field not in existing_attr_names_normalized:
                      constructor_params_list.append(f"this.{field_name} = const []")
      constructor_params = ", ".join(constructor_params_list)
      
      # Generar llamada al super() si hay herencia
      super_call = ""
      if parent_class and super_params_list:
          super_call = f" : super({', '.join(super_params_list)})"

      # fromJson
      from_json_fields = []
      
      # Si tiene padre, incluir TODOS los atributos heredados (incluyendo PK)
      if parent_class:
          # Función recursiva para obtener todos los atributos del padre
          def get_all_parent_attributes_for_json(class_name):
              attrs = []
              current_class = next((c for c in self.classes if c['name'] == class_name), None)
              if current_class:
                  # Buscar si esta clase también tiene padre
                  parent_rels = [r for r in relationships if r["from"] == class_name and r["kind"] == "inherits"]
                  if parent_rels:
                      parent_name = parent_rels[0]["to"]
                      attrs.extend(get_all_parent_attributes_for_json(parent_name))
                  # Agregar atributos propios del padre
                  attrs.extend(current_class.get('attributes', []))
              return attrs
          
          # Función para obtener relaciones del padre (recursiva)
          def get_all_parent_relationships_for_json(class_name):
              rels = []
              parent_rels = [r for r in relationships if r["from"] == class_name and r["kind"] == "inherits"]
              if parent_rels:
                  rels.extend(get_all_parent_relationships_for_json(parent_rels[0]["to"]))
              for rel in relationships:
                  if rel["from"] == class_name and rel["kind"] != "inherits":
                      rels.append(rel)
              return rels
          
          parent_attrs = get_all_parent_attributes_for_json(parent_class)
          parent_rels = get_all_parent_relationships_for_json(parent_class)
          
          # Agregar todos los atributos heredados al fromJson
          for attr in parent_attrs:
              attr_type = self._convert_type(attr['type'])
              json_key = self._to_backend_json_key(attr['name'])
              if attr_type == 'int':
                  from_json_fields.append(f"{attr['name']}: json['{json_key}'] is int ? json['{json_key}'] : int.tryParse(json['{json_key}']?.toString() ?? '0') ?? 0")
              elif attr_type == 'double':
                  from_json_fields.append(f"{attr['name']}: json['{json_key}'] is double ? json['{json_key}'] : double.tryParse(json['{json_key}']?.toString() ?? '0.0') ?? 0.0")
              elif attr_type == 'String':
                  from_json_fields.append(f"{attr['name']}: json['{json_key}']?.toString() ?? ''")
              elif attr_type == 'bool':
                  from_json_fields.append(f"{attr['name']}: json['{json_key}'] == true || json['{json_key}'] == 1 || json['{json_key}'] == 'true'")
              else:
                  from_json_fields.append(f"{attr['name']}: json['{json_key}']")
          
          # Agregar relaciones heredadas del padre (SOLO IDs)
          parent_existing_attrs = {attr['name'].lower().replace('_', '') for attr in parent_attrs}
          for rel in parent_rels:
              rel_name = self._to_snake_case(rel['to'])
              normalized = rel_name.lower().replace('_', '')
              if normalized not in parent_existing_attrs:
                  if rel["kind"] == "many_to_one":
                      # Parsear solo el ID
                      field_name = f"{rel_name}Id"
                      fk_json_key = self._to_backend_json_key(field_name)
                      from_json_fields.append(f"{field_name}: json['{fk_json_key}']?.toString() ?? ''")
                  elif rel["kind"] == "one_to_one":
                      # Parsear solo el ID
                      field_name = f"{rel_name}Id"
                      fk_json_key = self._to_backend_json_key(field_name)
                      from_json_fields.append(f"{field_name}: json['{fk_json_key}']?.toString() ?? ''")
                  # OneToMany NO se parsea en fromJson
      
      # Agregar campos propios (evitando duplicar atributos heredados)
      for attr in attributes:
          # Si hay herencia, saltar atributos que ya estén en el padre
          if parent_class and attr['name'].lower() in parent_attr_names:
              continue  # Ya fue agregado por el padre
          
          attr_type = self._convert_type(attr['type'])
          json_key = self._to_backend_json_key(attr['name'])
          if attr_type == 'int':
              from_json_fields.append(f"{attr['name']}: json['{json_key}'] is int ? json['{json_key}'] : int.tryParse(json['{json_key}']?.toString() ?? '0') ?? 0")
          elif attr_type == 'double':
              from_json_fields.append(f"{attr['name']}: json['{json_key}'] is double ? json['{json_key}'] : double.tryParse(json['{json_key}']?.toString() ?? '0.0') ?? 0.0")
          elif attr_type == 'String':
              from_json_fields.append(f"{attr['name']}: json['{json_key}']?.toString() ?? ''")
          elif attr_type == 'bool':
              from_json_fields.append(f"{attr['name']}: json['{json_key}'] == true || json['{json_key}'] == 1 || json['{json_key}'] == 'true'")
          else:
              from_json_fields.append(f"{attr['name']}: json['{json_key}']")

      # Agregar relaciones - parsear IDs, objetos anidados y listas
      for rel in relationships:
          if rel["from"] == name:
              rel_name = self._to_snake_case(rel['to'])
              if rel["kind"] == "many_to_one":
                  # Parsear el ID de la relación ManyToOne
                  # Puede venir como campo separado 'personaid' o dentro del objeto 'persona.id'
                  field_name = f"{rel_name}Id"
                  fk_json_key = self._to_backend_json_key(field_name)
                  json_key = self._to_backend_json_key(rel_name)
                  
                  # Intentar obtener el ID de múltiples fuentes: campo directo, objeto.id, o conversión de int
                  id_parsing = f"{field_name}: json['{fk_json_key}'] != null ? json['{fk_json_key}'].toString() : (json['{json_key}'] is Map ? json['{json_key}']['id']?.toString() : json['{json_key}']?.toString()) ?? ''"
                  from_json_fields.append(id_parsing)
                  
                  # Parsear también el objeto completo si viene anidado en el JSON (validar que sea Map)
                  from_json_fields.append(f"{rel_name}: json['{json_key}'] is Map<String, dynamic> ? {rel['to']}.fromJson(json['{json_key}']) : null")
              elif rel["kind"] == "one_to_one":
                  # Parsear el ID de la relación OneToOne
                  # Puede venir como campo separado o dentro del objeto
                  field_name = f"{rel_name}Id"
                  fk_json_key = self._to_backend_json_key(field_name)
                  json_key = self._to_backend_json_key(rel_name)
                  
                  # Intentar obtener el ID de múltiples fuentes
                  id_parsing = f"{field_name}: json['{fk_json_key}'] != null ? json['{fk_json_key}'].toString() : (json['{json_key}'] is Map ? json['{json_key}']['id']?.toString() : json['{json_key}']?.toString()) ?? ''"
                  from_json_fields.append(id_parsing)
                  
                  # Parsear también el objeto completo si viene anidado en el JSON (validar que sea Map)
                  from_json_fields.append(f"{rel_name}: json['{json_key}'] is Map<String, dynamic> ? {rel['to']}.fromJson(json['{json_key}']) : null")
              elif rel["kind"] == "one_to_many":
                  # OneToMany: Parsear lista de objetos anidados que vienen en GET
                  # El backend puede devolver listas mixtas [objeto, id, objeto] debido a @JsonIdentityInfo
                  # Filtrar solo los objetos completos (Maps), omitir los IDs sueltos
                  json_key = self._to_backend_json_key(rel_name)
                  parse_logic = f"""json['{json_key}'] is List 
          ? (json['{json_key}'] as List)
              .whereType<Map<String, dynamic>>()
              .map((e) => {rel['to']}.fromJson(e))
              .toList()
          : []"""
                  from_json_fields.append(f"{rel_name}: {parse_logic}")

      # toJson - incluir campos heredados también
      to_json_fields = []
      
      # Si tiene padre, incluir todos los campos heredados (incluyendo PK)
      if parent_class:
          # Función recursiva para obtener todos los atributos del padre
          def get_all_parent_attributes_for_tojson(class_name):
              attrs = []
              current_class = next((c for c in self.classes if c['name'] == class_name), None)
              if current_class:
                  # Buscar si esta clase también tiene padre
                  parent_rels = [r for r in relationships if r["from"] == class_name and r["kind"] == "inherits"]
                  if parent_rels:
                      parent_name = parent_rels[0]["to"]
                      attrs.extend(get_all_parent_attributes_for_tojson(parent_name))
                  # Agregar atributos propios del padre
                  attrs.extend(current_class.get('attributes', []))
              return attrs
          
          # Función para obtener relaciones del padre (recursiva)
          def get_all_parent_relationships_for_tojson(class_name):
              rels = []
              parent_rels = [r for r in relationships if r["from"] == class_name and r["kind"] == "inherits"]
              if parent_rels:
                  rels.extend(get_all_parent_relationships_for_tojson(parent_rels[0]["to"]))
              for rel in relationships:
                  if rel["from"] == class_name and rel["kind"] != "inherits":
                      rels.append(rel)
              return rels
          
          parent_attrs = get_all_parent_attributes_for_tojson(parent_class)
          parent_rels = get_all_parent_relationships_for_tojson(parent_class)
          
          # Agregar todos los atributos heredados al toJson
          for attr in parent_attrs:
              json_key = self._to_backend_json_key(attr['name'])
              to_json_fields.append(f"'{json_key}': {attr['name']}")
          
          # Agregar relaciones heredadas del padre (SOLO IDs)
          parent_existing_attrs = {attr['name'].lower().replace('_', '') for attr in parent_attrs}
          for rel in parent_rels:
              rel_name = self._to_snake_case(rel['to'])
              normalized = rel_name.lower().replace('_', '')
              if normalized not in parent_existing_attrs:
                  if rel["kind"] == "many_to_one":
                      # Enviar solo el ID
                      field_name = f"{rel_name}Id"
                      fk_json_key = self._to_backend_json_key(field_name)
                      to_json_fields.append(f"'{fk_json_key}': {field_name}")
                  elif rel["kind"] == "one_to_one":
                      # Enviar solo el ID
                      field_name = f"{rel_name}Id"
                      fk_json_key = self._to_backend_json_key(field_name)
                      to_json_fields.append(f"'{fk_json_key}': {field_name}")
                  # OneToMany NO se envía en toJson
      
      # Agregar campos propios (evitando duplicar atributos heredados)
      for attr in attributes:
          # Si hay herencia, saltar atributos que ya estén en el padre
          if parent_class and attr['name'].lower() in parent_attr_names:
              continue  # Ya fue agregado por el padre
          
          json_key = self._to_backend_json_key(attr['name'])
          to_json_fields.append(f"'{json_key}': {attr['name']}")
      
      # Agregar relaciones - ENVIAR SOLO IDs, NO objetos completos
      for rel in relationships:
          if rel["from"] == name:
              rel_name = self._to_snake_case(rel['to'])
              if rel["kind"] == "many_to_one":
                  # Para ManyToOne: enviar solo el ID (formato: personaId)
                  field_name = f"{rel_name}Id"
                  fk_json_key = self._to_backend_json_key(field_name)
                  to_json_fields.append(f"'{fk_json_key}': {field_name}")
              elif rel["kind"] == "one_to_one":
                  # Para OneToOne: enviar solo el ID (formato: relacionId)
                  field_name = f"{rel_name}Id"
                  fk_json_key = self._to_backend_json_key(field_name)
                  to_json_fields.append(f"'{fk_json_key}': {field_name}")
              elif rel["kind"] == "one_to_many":
                  # OneToMany NO se envía en el formulario (se gestiona desde el lado "many")
                  pass

      # Generar el constructor - no se necesitan parámetros extra para PK
      # La PK se maneja como el primer atributo
      id_param = ""
      
      # fromJson - no se necesita manejo especial, la PK viene en los atributos
      id_from_json = ""

      # toJson - no se necesita manejo especial, la PK está en los atributos  
      id_to_json = ""

      # Generar método toString() con los 2 primeros atributos significativos (sin id)
      display_attrs = [attr for attr in attributes if attr['name'].lower() != 'id'][:2]
      if display_attrs:
          to_string_parts = [f"'{attr['name']}: ${{{attr['name']}}}'" for attr in display_attrs]
          to_string_body = ' + ", " + '.join(to_string_parts)
      else:
          # Si no hay atributos además del id, usar el id o pk_name
          if pk_name:
              to_string_body = f"'ID: ${{{pk_name}}}'"
          else:
              to_string_body = f"'ID: ${{id}}'"

      content = f"""{imports}

  {class_declaration} {{
  {chr(10).join(properties)}

    {name}({{
      {id_param}
      {constructor_params},
    }}){super_call};

    factory {name}.fromJson(Map<String, dynamic> json) {{
      return {name}(
        {id_from_json}
        {', '.join(from_json_fields)},
      );
    }}

    Map<String, dynamic> toJson() {{
      return {{
        {id_to_json}
        {', '.join(to_json_fields)},
      }};
    }}

    @override
    String toString() {{
      return {to_string_body};
    }}
  }}
  """
      file_path = base_path / 'lib' / 'models' / f'{self._to_snake_case(name)}.dart'
      file_path.write_text(self._sanitize(content), encoding="utf-8", newline="\n")


    
    def _generate_service(self, base_path, clase):
        name = clase['name']
        snake_name = self._to_snake_case(name)
        backend_url_name = self._to_backend_json_key(name)
        relationships = [r for r in self.parsed_relationships if r["from"] == name]
        
        def get_all_attributes(class_name):
            attrs = []
            current_class = next((c for c in self.classes if c['name'] == class_name), None)
            if current_class:
                parent_rels = [r for r in self.parsed_relationships if r["from"] == class_name and r["kind"] == "inherits"]
                if parent_rels:
                    attrs.extend(get_all_attributes(parent_rels[0]["to"]))
                existing_attr_names = {attr['name'].lower() for attr in attrs}
                for attr in current_class.get('attributes', []):
                    if attr['name'].lower() not in existing_attr_names:
                        attrs.append(attr)
            return attrs
        
        all_attributes = get_all_attributes(name)
        pk_attr = all_attributes[0] if all_attributes else None
        pk_type = self._convert_type(pk_attr['type']) if pk_attr else 'String'
        is_numeric_pk = pk_type in ['int', 'double'] if pk_attr else False
        pk_name = pk_attr['name'] if pk_attr else 'id'

        content = f"""import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import '../models/{snake_name}.dart';
import '../config.dart';
import '../database/database_helper.dart';

class {name}Service {{
  static const String baseUrl = ApiConfig.baseUrl;
  
  Future<List<{name}>> getAll() async {{
    List<{name}> remoteData = [];
    bool networkSuccess = false;
    try {{
      final response = await http.get(
        Uri.parse('$baseUrl/{backend_url_name}/'),
        headers: {{'Content-Type': 'application/json'}},
      );

      if (response.statusCode == 200 || response.statusCode == 201) {{
        final List<dynamic> jsonList = json.decode(utf8.decode(response.bodyBytes));
        remoteData = jsonList
            .whereType<Map<String, dynamic>>()
            .map((item) => {name}.fromJson(item))
            .toList();
        networkSuccess = true;
      }} else {{
        throw Exception('Error al cargar {name}s: ${{response.statusCode}}');
      }}
    }} catch (e) {{
      if (e.toString().contains('Error al cargar')) rethrow;
      if (kIsWeb) rethrow;
    }}

    if (kIsWeb) return remoteData;

    if (networkSuccess) {{
      for (var item in remoteData) {{
        await DatabaseHelper.instance.upsert('{snake_name}', item.toJson(), '{pk_name}');
      }}
    }}

    final localData = await DatabaseHelper.instance.getAll('{snake_name}');
    return localData.map((j) => {name}.fromJson(j)).toList();
  }}

  Future<{name}?> getById(String id) async {{
    try {{
      final response = await http.get(
        Uri.parse('$baseUrl/{backend_url_name}/$id/'),
        headers: {{'Content-Type': 'application/json'}},
      );

      if (response.statusCode == 200 || response.statusCode == 201) {{
        final data = json.decode(utf8.decode(response.bodyBytes));
        if (!kIsWeb) {{
          await DatabaseHelper.instance.upsert('{snake_name}', data, '{pk_name}');
        }}
        return {name}.fromJson(data);
      }} else {{
        if (!kIsWeb && response.statusCode == 404) {{
          final localData = await DatabaseHelper.instance.getById('{snake_name}', '{pk_name}', id);
          if (localData != null) return {name}.fromJson(localData);
        }}
        throw Exception('Error al obtener {name}: ${{response.statusCode}}');
      }}
    }} catch (e) {{
      if (e.toString().contains('Error al obtener')) rethrow;
      if (!kIsWeb) {{
        final localData = await DatabaseHelper.instance.getById('{snake_name}', '{pk_name}', id);
        if (localData != null) return {name}.fromJson(localData);
      }}
      throw Exception('Error de conexión: $e');
    }}
  }}

  Future<{name}> create({name} item) async {{
    try {{
      final response = await http.post(
        Uri.parse('$baseUrl/{backend_url_name}/'),
        headers: {{'Content-Type': 'application/json'}},
        body: json.encode(item.toJson()),
      );

      if (response.statusCode == 201 || response.statusCode == 200) {{
        final data = json.decode(utf8.decode(response.bodyBytes));
        if (!kIsWeb) {{
          await DatabaseHelper.instance.upsert('{snake_name}', data, '{pk_name}');
        }}
        return {name}.fromJson(data);
      }} else {{
        throw Exception('Error al crear {name}: ${{response.statusCode}} - ${{response.body}}');
      }}
    }} catch (e) {{
      if (e.toString().contains('Error al crear')) rethrow;
      if (kIsWeb) rethrow;

      final map = item.toJson();
      final insertedMap = await DatabaseHelper.instance.insertLocal('{snake_name}', map, '{pk_name}', {str(is_numeric_pk).lower()});
      return {name}.fromJson(insertedMap);
    }}
  }}

  Future<{name}> update(String id, {name} item) async {{
    try {{
      final response = await http.put(
        Uri.parse('$baseUrl/{backend_url_name}/$id/'),
        headers: {{'Content-Type': 'application/json'}},
        body: json.encode(item.toJson()),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {{
        final data = json.decode(utf8.decode(response.bodyBytes));
        if (!kIsWeb) {{
          await DatabaseHelper.instance.upsert('{snake_name}', data, '{pk_name}');
        }}
        return {name}.fromJson(data);
      }} else {{
        if (!kIsWeb && response.statusCode == 404) {{
          final updatedMap = await DatabaseHelper.instance.updateLocal('{snake_name}', item.toJson(), '{pk_name}', id);
          return {name}.fromJson(updatedMap);
        }}
        throw Exception('Error al actualizar {name}: ${{response.statusCode}} - ${{response.body}}');
      }}
    }} catch (e) {{
      if (e.toString().contains('Error al actualizar')) rethrow;
      if (kIsWeb) rethrow;

      final updatedMap = await DatabaseHelper.instance.updateLocal('{snake_name}', item.toJson(), '{pk_name}', id);
      return {name}.fromJson(updatedMap);
    }}
  }}

  Future<void> delete(String id) async {{
    try {{
      final response = await http.delete(Uri.parse('$baseUrl/{backend_url_name}/$id/'));

      if (response.statusCode == 204 || response.statusCode == 200) {{
        if (!kIsWeb) {{
          await DatabaseHelper.instance.deleteLocal('{snake_name}', '{pk_name}', id);
        }}
        return;
      }} else {{
        if (!kIsWeb && response.statusCode == 404) {{
          await DatabaseHelper.instance.deleteLocal('{snake_name}', '{pk_name}', id);
          return;
        }}
        throw Exception('Error al eliminar {name}: ${{response.statusCode}} - ${{response.body}}');
      }}
    }} catch (e) {{
      if (e.toString().contains('Error al eliminar')) rethrow;
      if (kIsWeb) rethrow;

      await DatabaseHelper.instance.deleteLocal('{snake_name}', '{pk_name}', id);
    }}
  }}
}}
"""
        (base_path / 'lib' / 'services' / f'{snake_name}_service.dart').write_text(self._sanitize(content), encoding="utf-8", newline="\n")

    def _generate_list_view(self, base_path, clase):
        """Genera la vista de listado"""
        name = clase['name']
        snake_name = self._to_snake_case(name)
        relationships = [r for r in self.parsed_relationships if r["from"] == name]
        attributes = clase.get('attributes', [])
        
        # Detectar herencia para obtener todos los atributos
        parent_class = None
        for rel in relationships:
            if rel["kind"] == "inherits":
                parent_class = rel["to"]
                break
        
        # Función recursiva para obtener todos los atributos heredados
        def get_all_attributes(class_name):
            attrs = []
            current_class = next((c for c in self.classes if c['name'] == class_name), None)
            if current_class:
                parent_rels = [r for r in self.parsed_relationships if r["from"] == class_name and r["kind"] == "inherits"]
                if parent_rels:
                    parent_name = parent_rels[0]["to"]
                    attrs.extend(get_all_attributes(parent_name))
                
                # Luego agregar atributos propios (solo si no existen ya en attrs)
                existing_attr_names = {attr['name'].lower() for attr in attrs}
                for attr in current_class.get('attributes', []):
                    if attr['name'].lower() not in existing_attr_names:
                        attrs.append(attr)
            return attrs
        
        all_attributes = get_all_attributes(name)
        
        # El primer atributo es la PK
        pk_attr = all_attributes[0] if all_attributes else None
        pk_name = pk_attr['name'] if pk_attr else 'id'
        
        # Segundo atributo para mostrar en la lista (o el primero si solo hay uno)
        display_attr = all_attributes[1]['name'] if len(all_attributes) > 1 else pk_name
        
        content = f"""import 'package:flutter/material.dart';
import '../models/{snake_name}.dart';
import '../services/{snake_name}_service.dart';
import '{snake_name}_form_view.dart';
import '{snake_name}_detail_view.dart';

class {name}ListView extends StatefulWidget {{
  const {name}ListView({{super.key}});

  @override
  State<{name}ListView> createState() => _{name}ListViewState();
}}

class _{name}ListViewState extends State<{name}ListView> {{
  final {name}Service _service = {name}Service();
  List<{name}> _items = [];
  bool _isLoading = true;

  @override
  void initState() {{
    super.initState();
    _loadItems();
  }}

  Future<void> _loadItems() async {{
    setState(() => _isLoading = true);
    try {{
      final items = await _service.getAll();
      setState(() {{
        _items = items;
        _isLoading = false;
      }});
    }} catch (e) {{
      setState(() => _isLoading = false);
      if (mounted) {{
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error al cargar: $e')),
        );
      }}
    }}
  }}

  Future<void> _deleteItem(String id) async {{
    try {{
      await _service.delete(id);
      _loadItems();
      if (mounted) {{
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Eliminado exitosamente')),
        );
      }}
    }} catch (e) {{
      if (mounted) {{
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error al eliminar: $e')),
        );
      }}
    }}
  }}

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: const Text('{name}'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? const Center(
                  child: Text('No hay registros. ¡Crea uno nuevo!'),
                )
              : ListView.builder(
                  itemCount: _items.length,
                  itemBuilder: (context, index) {{
                    final item = _items[index];
                    return Card(
                      margin: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      child: ListTile(
                        title: Text(item.{display_attr}.toString()),
                        subtitle: Text('{pk_name}: ${{item.{pk_name}}}'),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.edit),
                              onPressed: () async {{
                                await Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) => {name}FormView(
                                      item: item,
                                    ),
                                  ),
                                );
                                _loadItems();
                              }},
                            ),
                            IconButton(
                              icon: const Icon(Icons.delete),
                              color: Colors.red,
                              onPressed: () {{
                                showDialog(
                                  context: context,
                                  builder: (context) => AlertDialog(
                                    title: const Text('Confirmar'),
                                    content: const Text(
                                      '¿Deseas eliminar este registro?',
                                    ),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.pop(context),
                                        child: const Text('Cancelar'),
                                      ),
                                      TextButton(
                                        onPressed: () {{
                                          Navigator.pop(context);
                                          _deleteItem(item.{pk_name}.toString());
                                        }},
                                        child: const Text('Eliminar'),
                                      ),
                                    ],
                                  ),
                                );
                              }},
                            ),
                          ],
                        ),
                        onTap: () {{
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => {name}DetailView(item: item),
                            ),
                          );
                        }},
                      ),
                    );
                  }},
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {{
          await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const {name}FormView(),
            ),
          );
          _loadItems();
        }},
        child: const Icon(Icons.add),
      ),
    );
  }}
}}
"""
        file_path = base_path / 'lib' / 'views' / f'{snake_name}_list_view.dart'
        file_path.write_text(content, encoding="utf-8", newline="\n")
    
    def _generate_form_view(self, base_path, clase):
        """Genera la vista de formulario (crear/editar)"""
        name = clase['name']
        snake_name = self._to_snake_case(name)
        relationships = [r for r in self.parsed_relationships if r["from"] == name]
        attributes = clase.get('attributes', [])
        
        # Detectar herencia y obtener todos los atributos (propios + heredados)
        all_attributes = []
        parent_class = None
        for rel in relationships:
            if rel["kind"] == "inherits":
                parent_class = rel["to"]
                break
        
        # Función recursiva para obtener todos los atributos heredados
        def get_all_attributes(class_name):
            attrs = []
            current_class = next((c for c in self.classes if c['name'] == class_name), None)
            if current_class:
                # Primero obtener atributos del padre (si existe)
                parent_rels = [r for r in self.parsed_relationships if r["from"] == class_name and r["kind"] == "inherits"]
                if parent_rels:
                    parent_name = parent_rels[0]["to"]
                    attrs.extend(get_all_attributes(parent_name))
                
                # Luego agregar atributos propios (solo si no existen ya en attrs)
                existing_attr_names = {attr['name'].lower() for attr in attrs}
                for attr in current_class.get('attributes', []):
                    if attr['name'].lower() not in existing_attr_names:
                        attrs.append(attr)
            return attrs
        
        all_attributes = get_all_attributes(name)
        
        # Detectar tipo de PK (primer atributo si no hay herencia)
        pk_attr = all_attributes[0] if all_attributes else None
        pk_type = self._convert_type(pk_attr['type']) if pk_attr else 'String'
        is_numeric_pk = pk_type in ['int', 'double'] if pk_attr else False
        pk_name = pk_attr['name'] if pk_attr else 'id'
        
        # Verificar si la clase tiene un atributo 'id' definido
        has_id = any(attr['name'].lower() == 'id' for attr in all_attributes)
        
        # Normalizar para comparación (declarar temprano para uso posterior)
        existing_attr_names_normalized = {attr['name'].lower().replace('_', '') for attr in all_attributes}
        
        # Generar controladores
        # - Para PK numérica (autoincremental): NO generar controlador (solo en edición, readonly)
        # - Para PK string: SÍ generar controlador (se debe ingresar manualmente)
        # - Los atributos heredados SÍ necesitan controladores para poder editarlos
        controllers_list = []
        for i, attr in enumerate(all_attributes):
            # Si es la PK (primer atributo) y es numérica, no generar controlador para creación
            if i == 0 and is_numeric_pk:
                # Solo se mostrará readonly en edición
                continue
            # Para todos los demás atributos (propios y heredados), generar controlador
            controllers_list.append(f"final TextEditingController _{attr['name']}Controller = TextEditingController();")
        
        # Agregar variables para relaciones many_to_one y one_to_one (propias y heredadas)
        # Rastrear qué relaciones ya se agregaron para evitar duplicados
        added_relations = set()
        
        # Función para obtener todas las relaciones (propias y del padre)
        def get_all_relations_for_state(class_name):
            rels = []
            # Buscar padre
            for r in self.parsed_relationships:
                if r["from"] == class_name and r["kind"] == "inherits":
                    # Recursivamente obtener relaciones del padre
                    rels.extend(get_all_relations_for_state(r["to"]))
                    break
            # Agregar relaciones propias (ManyToOne y OneToOne)
            for r in self.parsed_relationships:
                if r["from"] == class_name and r["kind"] in ["many_to_one", "one_to_one"]:
                    rels.append(r)
            return rels
        
        all_relations = get_all_relations_for_state(name)
        for rel in all_relations:
            rel_key = f"{rel['to']}"
            if rel_key not in added_relations:
                controllers_list.append(f"String? _selected{rel['to']}Id;")
                added_relations.add(rel_key)
        
        # Relaciones one_to_many NO necesitan variables de estado en el formulario
        # porque NO se editan desde este lado (se gestionan desde el lado "many")
        
        controllers = '\n  '.join(controllers_list)
        
        # Inicializar controladores si es edición - incluir campos heredados
        init_controllers_list = []
        for i, attr in enumerate(all_attributes):
            # Si es PK numérica, no hay controlador para inicializar (solo lectura)
            if i == 0 and is_numeric_pk:
                continue
            # Inicializar todos los controladores (propios y heredados)
            init_controllers_list.append(f"_{attr['name']}Controller.text = widget.item!.{attr['name']}.toString();")
        
        # Inicializar relaciones many_to_one y one_to_one (propias y heredadas)
        # Usar las mismas relaciones que ya obtuvimos antes
        initialized_relations = set()
        for rel in all_relations:
            rel_key = f"{rel['to']}"
            if rel_key not in initialized_relations:
                field_name = f"{self._to_snake_case(rel['to'])}Id"
                # Convertir a String y manejar valores vacíos para evitar que sea ""
                # El dropdown espera null o un valor válido que exista en la lista
                init_controllers_list.append(f"if (widget.item!.{field_name}.isNotEmpty) {{ _selected{rel['to']}Id = widget.item!.{field_name}; }}")
                initialized_relations.add(rel_key)
        
        # Relaciones one_to_many NO se inicializan en el formulario
        # porque NO se editan desde este lado (solo lectura en vista de detalle)
        
        init_controllers = '\n      '.join(init_controllers_list)
        
        # Generar campos del formulario
        form_fields = []
        for i, attr in enumerate(all_attributes):
            dart_type = self._convert_type(attr['type'])
            keyboard_type = 'TextInputType.number' if dart_type in ['int', 'double'] else 'TextInputType.text'
            
            # Si es PK numérica y estamos EDITANDO, mostrar campo readonly
            if i == 0 and is_numeric_pk:
                form_fields.append(f"""            if (widget.item != null)
              TextFormField(
                initialValue: widget.item!.{attr['name']}.toString(),
                decoration: const InputDecoration(
                  labelText: '{attr['name']} (Auto)',
                  border: OutlineInputBorder(),
                ),
                enabled: false,
              )""")
                continue
            
            # Para todos los demás atributos (propios y heredados), crear campo editable
            form_fields.append(f"""            TextFormField(
              controller: _{attr['name']}Controller,
              decoration: const InputDecoration(
                labelText: '{attr['name']}',
                border: OutlineInputBorder(),
              ),
              keyboardType: {keyboard_type},
              validator: (value) {{
                if (value == null || value.isEmpty) {{
                  return 'Este campo es requerido';
                }}
                return null;
              }},
            )""")
        
        # Relaciones ManyToOne → Dropdown (sin coma al final)
        for rel in relationships:
            if rel["kind"] == "many_to_one":
                # Obtener la PK y display attr de la clase relacionada
                related_class = next((c for c in self.classes if c['name'] == rel['to']), None)
                
                # Función para obtener la PK de una clase (considerando herencia)
                def get_related_pk(class_name):
                    current = next((c for c in self.classes if c['name'] == class_name), None)
                    if current:
                        parent_rels = [r for r in self.parsed_relationships if r["from"] == class_name and r["kind"] == "inherits"]
                        if parent_rels:
                            return get_related_pk(parent_rels[0]["to"])
                        attrs = current.get('attributes', [])
                        if attrs:
                            return attrs[0]['name']
                    return 'id'
                
                related_pk = get_related_pk(rel['to'])
                display_attr = related_pk
                
                if related_class:
                    attrs = related_class.get('attributes', [])
                    # Buscar el primer atributo que no sea la PK para mostrar
                    for attr in attrs:
                        if attr['name'] != related_pk:
                            display_attr = attr['name']
                            break
                
                form_fields.append(f"""FutureBuilder<List<{rel['to']}>>(
              future: {rel['to']}Service().getAll(),
              builder: (context, snapshot) {{
                if (!snapshot.hasData) return const CircularProgressIndicator();
                final items = snapshot.data!;
                // Eliminar duplicados por ID si existen
                final uniqueItems = {{
                  for (var item in items) item.{related_pk}.toString(): item
                }}.values.toList();
                // Verificar que el valor seleccionado exista en la lista
                final validValue = _selected{rel['to']}Id != null && 
                    uniqueItems.any((e) => e.{related_pk}.toString() == _selected{rel['to']}Id)
                    ? _selected{rel['to']}Id
                    : null;
                return DropdownButtonFormField<String>(
                  decoration: const InputDecoration(labelText: '{rel['to']}'),
                  initialValue: validValue,
                  items: uniqueItems.map((e) => DropdownMenuItem(
                    value: e.{related_pk}.toString(),
                    child: Text(e.{display_attr}.toString()),
                  )).toList(),
                  onChanged: (v) {{
                    setState(() {{
                      _selected{rel['to']}Id = v;
                    }});
                  }},
                  validator: (value) {{
                    if (value == null || value.isEmpty) {{
                      return 'Este campo es requerido';
                    }}
                    return null;
                  }},
                );
              }},
            )""")
        
        # Relaciones OneToOne → Dropdown
        for rel in relationships:
            if rel["kind"] == "one_to_one":
                field_name = self._to_snake_case(rel['to'])
                normalized_field = field_name.lower().replace('_', '')
                if normalized_field not in existing_attr_names_normalized:
                    # Obtener la PK y display attr de la clase relacionada
                    related_class = next((c for c in self.classes if c['name'] == rel['to']), None)
                    
                    # Función para obtener la PK de una clase (considerando herencia)
                    def get_related_pk_one(class_name):
                        current = next((c for c in self.classes if c['name'] == class_name), None)
                        if current:
                            parent_rels = [r for r in self.parsed_relationships if r["from"] == class_name and r["kind"] == "inherits"]
                            if parent_rels:
                                return get_related_pk_one(parent_rels[0]["to"])
                            attrs = current.get('attributes', [])
                            if attrs:
                                return attrs[0]['name']
                        return 'id'
                    
                    related_pk = get_related_pk_one(rel['to'])
                    display_attr = related_pk
                    
                    if related_class:
                        attrs = related_class.get('attributes', [])
                        # Buscar el primer atributo que no sea la PK para mostrar
                        for attr in attrs:
                            if attr['name'] != related_pk:
                                display_attr = attr['name']
                                break
                    
                    form_fields.append(f"""FutureBuilder<List<{rel['to']}>>(
              future: {rel['to']}Service().getAll(),
              builder: (context, snapshot) {{
                if (!snapshot.hasData) return const CircularProgressIndicator();
                return DropdownButtonFormField<String>(
                  decoration: const InputDecoration(labelText: '{rel['to']}'),
                  initialValue: _selected{rel['to']}Id,
                  items: snapshot.data!.map((e) => DropdownMenuItem(
                    value: e.{related_pk}.toString(),
                    child: Text(e.{display_attr}.toString()),
                  )).toList(),
                  onChanged: (v) {{
                    setState(() {{
                      _selected{rel['to']}Id = v;
                    }});
                  }},
                  validator: (value) {{
                    if (value == null || value.isEmpty) {{
                      return 'Este campo es requerido';
                    }}
                    return null;
                  }},
                );
              }},
            )""")
        
        # Relaciones OneToMany → NO generar campos de formulario
        # En REST estándar, las relaciones one_to_many se gestionan desde el lado "many"
        # Solo se muestran en la vista de detalle (read-only), NO en el formulario
        # Por ejemplo: Persona tiene List<Perro>, pero NO se edita desde Persona
        # Se edita desde Perro seleccionando la Persona (many_to_one)

        # Generar creación del objeto
        # Para PKs numéricas: Si es creación, NO enviar (backend genera). Si es edición, enviar desde widget.item
        # Para PKs string: Siempre enviar desde el controlador
        create_object_fields_list = []
        for i, attr in enumerate(all_attributes):
            # Si es PK numérica (primer atributo y numérico)
            if i == 0 and is_numeric_pk:
                # En edición, usar el PK del item existente. En creación, el backend lo genera
                create_object_fields_list.append(f"{attr['name']}: widget.item?.{attr['name']} ?? 0")
            else:
                # Para todos los demás atributos (propios y heredados), usar el valor del controlador
                create_object_fields_list.append(f"{attr['name']}: {self._parse_field_value(attr)}")
        
        # Si hay herencia, agregar las relaciones del padre al objeto
        # Crear un set con los nombres ya usados para evitar duplicados
        used_field_names = {field.split(':')[0].strip() for field in create_object_fields_list}
        
        if parent_class:
            # Función recursiva para obtener relaciones del padre
            def get_all_parent_relationships_for_form(class_name):
                rels = []
                parent_rels = [r for r in self.parsed_relationships if r["from"] == class_name and r["kind"] == "inherits"]
                if parent_rels:
                    rels.extend(get_all_parent_relationships_for_form(parent_rels[0]["to"]))
                for rel in self.parsed_relationships:
                    if rel["from"] == class_name and rel["kind"] != "inherits":
                        rels.append(rel)
                return rels
            
            parent_rels = get_all_parent_relationships_for_form(parent_class)
            for rel in parent_rels:
                # Solo agregar relaciones ManyToOne y OneToOne (que son IDs)
                # OneToMany NO se pasa en el constructor (no existe en el modelo)
                if rel["kind"] == "many_to_one":
                    field_name = f"{self._to_snake_case(rel['to'])}Id"
                    if field_name not in used_field_names:
                        create_object_fields_list.append(f"{field_name}: _selected{rel['to']}Id ?? ''")
                        used_field_names.add(field_name)
                elif rel["kind"] == "one_to_one":
                    field_name = f"{self._to_snake_case(rel['to'])}Id"
                    if field_name not in used_field_names:
                        create_object_fields_list.append(f"{field_name}: _selected{rel['to']}Id ?? ''")
                        used_field_names.add(field_name)
                # OneToMany: NO se agrega (no existe en el modelo)
        
        create_object_fields = ',\n          '.join(create_object_fields_list)
        
        # Agregar relaciones many_to_one al objeto
        many_to_one_fields = []
        for rel in relationships:
            if rel["kind"] == "many_to_one":
                field_name = f"{self._to_snake_case(rel['to'])}Id"
                normalized_field = field_name.lower().replace('_', '')
                if normalized_field not in existing_attr_names_normalized:
                    many_to_one_fields.append(f"{field_name}: _selected{rel['to']}Id ?? ''")
        
        if many_to_one_fields:
            if create_object_fields:
                create_object_fields += ',\n          ' + ',\n          '.join(many_to_one_fields)
            else:
                create_object_fields = ',\n          '.join(many_to_one_fields)
        
        # Agregar relaciones OneToOne al objeto (solo IDs)
        one_to_one_fields = []
        for rel in relationships:
            if rel["kind"] == "one_to_one":
                field_name = f"{self._to_snake_case(rel['to'])}Id"
                normalized_field = field_name.lower().replace('_', '')
                if normalized_field not in existing_attr_names_normalized:
                    one_to_one_fields.append(f"{field_name}: _selected{rel['to']}Id ?? ''")
        
        if one_to_one_fields:
            if create_object_fields:
                create_object_fields += ',\n          ' + ',\n          '.join(one_to_one_fields)
            else:
                create_object_fields = ',\n          '.join(one_to_one_fields)
        
        # Generar imports para modelos y servicios relacionados
        related_imports = []
        
        for rel in relationships:
            # Importar servicios para cargar opciones de dropdown (ManyToOne y OneToOne)
            if rel["kind"] in ["one_to_one", "many_to_one"]:
                related_imports.append(f"import '../models/{self._to_snake_case(rel['to'])}.dart';")
                related_imports.append(f"import '../services/{self._to_snake_case(rel['to'])}_service.dart';")
            # one_to_many NO necesita imports en formulario (solo en vista de detalle)
        
        # Eliminar duplicados y ordenar
        related_imports = sorted(set(related_imports))
        related_imports_str = '\n'.join(related_imports) if related_imports else ''
        
        # No se necesitan métodos helper porque trabajamos solo con IDs
        helper_methods = []
        
        content = f"""import 'package:flutter/material.dart';
import '../models/{snake_name}.dart';
import '../services/{snake_name}_service.dart';
{related_imports_str}

class {name}FormView extends StatefulWidget {{
  final {name}? item;

  const {name}FormView({{super.key, this.item}});

  @override
  State<{name}FormView> createState() => _{name}FormViewState();
}}

class _{name}FormViewState extends State<{name}FormView> {{
  final _formKey = GlobalKey<FormState>();
  final {name}Service _service = {name}Service();
  {controllers}
  bool _isLoading = false;

  @override
  void initState() {{
    super.initState();
    if (widget.item != null) {{
      {init_controllers}
    }}
  }}

  @override
  void dispose() {{
{self._generate_dispose_controllers(all_attributes, is_numeric_pk, parent_class)}
    super.dispose();
  }}

  Future<void> _submit() async {{
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {{
      final item = {name}(
        {create_object_fields},
      );

      if (widget.item == null) {{
        await _service.create(item);
      }} else {{
        await _service.update(item.{pk_name}.toString(), item);
      }}

      if (mounted) {{
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.item == null
                ? 'Creado exitosamente'
                : 'Actualizado exitosamente'),
          ),
        );
      }}
    }} catch (e) {{
      setState(() => _isLoading = false);
      if (mounted) {{
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }}
    }}
  }}
{''.join(helper_methods)}

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.item == null ? 'Crear {name}' : 'Editar {name}'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  children: [
{','.join([chr(10) + '                    const SizedBox(height: 16),' + chr(10) + field for field in form_fields])},
                    const SizedBox(height: 24),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _submit,
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.all(16),
                        ),
                        child: Text(
                          widget.item == null ? 'Crear' : 'Actualizar',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
    );
  }}
}}
"""
        file_path = base_path / 'lib' / 'views' / f'{snake_name}_form_view.dart'
        file_path.write_text(content, encoding="utf-8", newline="\n")
    
    def _generate_detail_view(self, base_path, clase):
        """Genera la vista de detalle"""
        name = clase['name']
        snake_name = self._to_snake_case(name)
        relationships = [r for r in self.parsed_relationships if r["from"] == name]
        attributes = clase.get('attributes', [])
        
        # Detectar herencia y obtener todos los atributos
        parent_class = None
        for rel in relationships:
            if rel["kind"] == "inherits":
                parent_class = rel["to"]
                break
        
        # Función recursiva para obtener todos los atributos heredados
        def get_all_attributes(class_name):
            attrs = []
            current_class = next((c for c in self.classes if c['name'] == class_name), None)
            if current_class:
                # Primero obtener atributos del padre (si existe)
                parent_rels = [r for r in self.parsed_relationships if r["from"] == class_name and r["kind"] == "inherits"]
                if parent_rels:
                    parent_name = parent_rels[0]["to"]
                    attrs.extend(get_all_attributes(parent_name))
                
                # Luego agregar atributos propios (solo si no existen ya en attrs)
                existing_attr_names = {attr['name'].lower() for attr in attrs}
                for attr in current_class.get('attributes', []):
                    if attr['name'].lower() not in existing_attr_names:
                        attrs.append(attr)
            return attrs
        
        all_attributes = get_all_attributes(name)
        
        # El primer atributo es la PK
        pk_attr = all_attributes[0] if all_attributes else None
        pk_name = pk_attr['name'] if pk_attr else 'id'
        
        # Normalizar para evitar duplicados
        existing_attr_names_normalized = {attr['name'].lower().replace('_', '') for attr in all_attributes}
        
        # Generar filas de detalles - incluir todos los campos (incluyendo PK)
        detail_rows = []
        for attr in all_attributes:
            detail_rows.append(f"""              _buildDetailRow('{attr['name']}', item.{attr['name']}.toString()),""")
        
        # Agregar relaciones
        for rel in relationships:
            if rel["kind"] == "one_to_many":
                # OneToMany: Mostrar lista de objetos relacionados (viene del backend en GET)
                field_name = self._to_snake_case(rel['to'])
                normalized_field = field_name.lower().replace('_', '')
                if normalized_field not in existing_attr_names_normalized:
                    # Obtener información de la clase relacionada
                    related_class = next((c for c in self.classes if c['name'] == rel['to']), None)
                    
                    # Detectar si es una entidad intermedia (tiene exactamente 2 relaciones ManyToOne)
                    is_intermediate = False
                    intermediate_relations = []
                    if related_class:
                        related_relationships = [r for r in self.parsed_relationships if r["from"] == rel['to']]
                        many_to_one_rels = [r for r in related_relationships if r["kind"] == "many_to_one"]
                        if len(many_to_one_rels) == 2:
                            is_intermediate = True
                            intermediate_relations = many_to_one_rels
                    
                    # ALTERNATIVA: Detectar si el nombre de la clase relacionada contiene el nombre de la entidad actual
                    # Esto captura casos como "PerroPersona" cuando estamos en "Persona" o "Perro"
                    is_likely_intermediate = False
                    if not is_intermediate and related_class:
                        class_name_lower = rel['to'].lower()
                        current_name_lower = name.lower()
                        # Si el nombre de la clase contiene el nombre de la entidad actual, probablemente es intermedia
                        if current_name_lower in class_name_lower and len(rel['to']) > len(name):
                            is_likely_intermediate = True
                            # Forzar la detección de relaciones para esta entidad
                            related_relationships = [r for r in self.parsed_relationships if r["from"] == rel['to']]
                            many_to_one_rels = [r for r in related_relationships if r["kind"] == "many_to_one"]
                            if len(many_to_one_rels) >= 2:
                                is_intermediate = True
                                intermediate_relations = many_to_one_rels
                    
                    if is_intermediate and len(intermediate_relations) == 2:
                        # Es una entidad intermedia - mostrar solo la entidad relacionada (NO la actual)
                        first_rel = intermediate_relations[0]
                        second_rel = intermediate_relations[1]
                        
                        # Determinar cuál entidad es la "otra" (no la actual)
                        other_rel = None
                        other_field = None
                        other_entity_name = None
                        
                        if first_rel['to'] != name:
                            other_rel = first_rel
                            other_field = self._to_snake_case(first_rel['to'])
                            other_entity_name = first_rel['to']
                        elif second_rel['to'] != name:
                            other_rel = second_rel
                            other_field = self._to_snake_case(second_rel['to'])
                            other_entity_name = second_rel['to']
                        
                        if other_rel and other_field:
                            # Obtener los 2 primeros atributos significativos de la otra entidad (sin id)
                            other_entity_class = next((c for c in self.classes if c['name'] == other_entity_name), None)
                            other_attrs = []
                            
                            if other_entity_class:
                                other_attrs = [attr['name'] for attr in other_entity_class.get('attributes', []) if attr['name'].lower() != 'id'][:2]
                            
                            # Generar el código para mostrar solo la otra entidad con sus atributos
                            if other_attrs:
                                # Generar interpolaciones dentro de una sola cadena
                                attr_interpolations = ', '.join([f"${{e.{other_field}?.{attr}}}" for attr in other_attrs])
                                display_code = f"'• {attr_interpolations}'"
                            else:
                                display_code = f"'ID: ${{e.{other_field}id}}'"
                            
                            detail_rows.append(f"""              const SizedBox(height: 16),
              Text('{other_entity_name}s:', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              if (item.{field_name}.isEmpty)
                const Padding(
                  padding: EdgeInsets.only(left: 16, bottom: 4),
                  child: Text('No hay {other_entity_name.lower()}s relacionados', style: TextStyle(fontSize: 14, fontStyle: FontStyle.italic, color: Colors.grey)),
                )
              else
                ...item.{field_name}.map((e) => Padding(
                  padding: const EdgeInsets.only(left: 16, bottom: 4),
                  child: Text({display_code}, style: const TextStyle(fontSize: 14), overflow: TextOverflow.ellipsis, maxLines: 2),
                )),""")
                    
                    if not is_intermediate or len(intermediate_relations) != 2:
                        # Relación OneToMany normal: Mostrar el primer atributo descriptivo
                        display_attr = 'id'
                        if related_class:
                            attrs = related_class.get('attributes', [])
                            # Buscar un atributo descriptivo (no id)
                            for attr in attrs:
                                if attr['name'].lower() not in ['id']:
                                    display_attr = attr['name']
                                    break
                        
                        detail_rows.append(f"""              const SizedBox(height: 16),
              Text('{rel['to']}s:', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              if (item.{field_name}.isEmpty)
                const Padding(
                  padding: EdgeInsets.only(left: 16, bottom: 4),
                  child: Text('No hay {rel['to'].lower()}s registrados', style: TextStyle(fontSize: 14, fontStyle: FontStyle.italic, color: Colors.grey)),
                )
              else
                ...item.{field_name}.map((e) => Padding(
                  padding: const EdgeInsets.only(left: 16, bottom: 4),
                  child: Text('• ${{e.{display_attr}.toString()}}', style: const TextStyle(fontSize: 14)),
                )),""")
            elif rel["kind"] == "one_to_one" or rel["kind"] == "many_to_one":
                field_name = self._to_snake_case(rel['to'])
                normalized_field = field_name.lower().replace('_', '')
                if normalized_field not in existing_attr_names_normalized:
                    # Obtener atributos de la clase relacionada
                    related_class = next((c for c in self.classes if c['name'] == rel['to']), None)
                    if related_class:
                        attrs = related_class.get('attributes', [])
                        
                        # Si el objeto está disponible, mostrar los primeros 2 atributos (o 1 si solo tiene 1)
                        # Filtrar atributos que no sean 'id'
                        display_attrs = [attr for attr in attrs if attr['name'].lower() != 'id']
                        # Tomar los primeros 2 (o menos si no hay suficientes)
                        attrs_to_show = display_attrs[:2]
                        
                        for attr in attrs_to_show:
                            detail_rows.append(f"""              if (item.{field_name} != null) _buildDetailRow('{rel['to']}.{attr['name']}', item.{field_name}!.{attr['name']}.toString()),""")
        
        content = f"""import 'package:flutter/material.dart';
import '../models/{snake_name}.dart';

class {name}DetailView extends StatelessWidget {{
  final {name} item;

  const {name}DetailView({{super.key, required this.item}});

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: const Text('Detalle de {name}'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '{name}',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const Divider(height: 32),
{chr(10).join([row + chr(10) + '                const SizedBox(height: 12),' for row in detail_rows])}
              ],
            ),
          ),
        ),
      ),
    );
  }}

  Widget _buildDetailRow(String label, String value) {{
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 120,
          child: Text(
            '$label:',
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontSize: 16),
          ),
        ),
      ],
    );
  }}
}}
"""
        file_path = base_path / 'lib' / 'views' / f'{snake_name}_detail_view.dart'
        file_path.write_text(content, encoding="utf-8", newline="\n")
    
    def _generate_routes(self, base_path):
        """Genera el archivo de rutas (opcional)"""
        pass
    
    # ========================================
    # === ASISTENTE SCHEMA-AWARE (P0) ===
    # ========================================
    # Infraestructura generada de forma independiente a los generadores de
    # modelos/servicios/vistas ya existentes. Los métodos de esta sección NO
    # reutilizan ni refactorizan la lógica de herencia/relaciones de
    # _generate_model/_generate_service/_generate_database_helper: la
    # replican intencionalmente para no arriesgar una regresión en el CRUD
    # ya generado. Solo cubren las clases UML originales; las entidades
    # intermedias M:N quedan fuera del vocabulario del asistente en este P0.

    def _assistant_pick_name_field(self, fields):
        """Heurística de "campo legible" para el asistente.

        Prioridad: un campo String no-PK llamado name/nombre/title/titulo/
        label (comparación sin tildes). Si no hay, el primer campo String
        no-PK. Si no hay ninguno, None. No se inventan traducciones."""
        priority = {'name', 'nombre', 'title', 'titulo', 'label'}

        def fold(value):
            table = str.maketrans('áéíóúÁÉÍÓÚ', 'aeiouAEIOU')
            return value.translate(table).lower()

        for field in fields:
            if field['dart_type'] == 'String' and not field['is_primary_key'] and fold(field['name']) in priority:
                return field['name']
        for field in fields:
            if field['dart_type'] == 'String' and not field['is_primary_key']:
                return field['name']
        return None

    def _assistant_entity_metadata(self, clase):
        """Recolecta metadata del asistente para una clase UML original.

        Replica (sin reutilizar) el aplanamiento de atributos/relaciones que
        usan _generate_model/_generate_service, para no acoplar el asistente
        a esos métodos ni arriesgar tocarlos."""
        name = clase['name']
        relationships = self.parsed_relationships

        def collect_attrs(class_name):
            attrs = []
            current = next((c for c in self.classes if c['name'] == class_name), None)
            if current:
                parent_rels = [r for r in relationships if r["from"] == class_name and r["kind"] == "inherits"]
                if parent_rels:
                    attrs.extend(collect_attrs(parent_rels[0]["to"]))
                existing = {a['name'].lower() for a in attrs}
                for attr in current.get('attributes', []):
                    if attr['name'].lower() not in existing:
                        attrs.append(attr)
            return attrs

        all_attrs = collect_attrs(name)

        fields = []
        for i, attr in enumerate(all_attrs):
            dart_type = self._convert_type(attr['type'])
            is_pk = (i == 0)
            # Mirrors _generate_form_view's is_numeric_pk (int AND double are
            # both treated as generator-populated, non-user-entered PKs).
            # CommandValidator separately hard-blocks ALL mutations for a
            # double PK entity regardless of this flag; it is not reused to
            # decide that block.
            is_auto_increment = is_pk and dart_type in ('int', 'double')
            is_date = dart_type == 'DateTime'
            fields.append({
                'name': attr['name'],
                'dart_type': dart_type,
                'json_key': self._to_backend_json_key(attr['name']),
                'is_primary_key': is_pk,
                'is_auto_increment': is_auto_increment,
                'required_on_create': not is_auto_increment,
                'writable': not is_date,
            })

        def collect_rels(class_name):
            rels = []
            for r in relationships:
                if r["from"] == class_name and r["kind"] == "inherits":
                    rels.extend(collect_rels(r["to"]))
                    break
            for r in relationships:
                if r["from"] == class_name and r["kind"] in ("many_to_one", "one_to_one", "one_to_many"):
                    rels.append(r)
            return rels

        existing_attr_names = {a['name'].lower().replace('_', '') for a in all_attrs}
        relations = []
        for rel in collect_rels(name):
            target = rel['to']
            rel_snake = self._to_snake_case(target)
            if rel['kind'] in ('many_to_one', 'one_to_one'):
                field_name = f"{rel_snake}Id"
                normalized = field_name.lower().replace('_', '')
                if normalized in existing_attr_names:
                    continue
                relations.append({
                    'name': field_name,
                    'target_entity': target,
                    'kind': rel['kind'],
                    'json_key': self._to_backend_json_key(field_name),
                    'required_on_create': True,
                    'writable': True,
                })
            elif rel['kind'] == 'one_to_many':
                field_name = rel_snake
                normalized = field_name.lower().replace('_', '')
                if normalized in existing_attr_names:
                    continue
                relations.append({
                    'name': field_name,
                    'target_entity': target,
                    'kind': rel['kind'],
                    'json_key': self._to_backend_json_key(field_name),
                    'required_on_create': False,
                    'writable': False,
                })

        return {
            'name': name,
            'fields': fields,
            'relations': relations,
            'name_field': self._assistant_pick_name_field(fields),
        }

    def _assistant_dart_string_literal(self, value):
        escaped = value.replace('\\', '\\\\').replace("'", "\\'")
        return f"'{escaped}'"

    def _assistant_render_field(self, field):
        return (
            "AssistantFieldSchema(\n"
            f"          name: {self._assistant_dart_string_literal(field['name'])},\n"
            f"          dartType: {self._assistant_dart_string_literal(field['dart_type'])},\n"
            f"          jsonKey: {self._assistant_dart_string_literal(field['json_key'])},\n"
            f"          isPrimaryKey: {str(field['is_primary_key']).lower()},\n"
            f"          isAutoIncrement: {str(field['is_auto_increment']).lower()},\n"
            f"          requiredOnCreate: {str(field['required_on_create']).lower()},\n"
            f"          writable: {str(field['writable']).lower()},\n"
            "        )"
        )

    def _assistant_render_relation(self, rel):
        kind_map = {
            'many_to_one': 'AssistantRelationKind.manyToOne',
            'one_to_one': 'AssistantRelationKind.oneToOne',
            'one_to_many': 'AssistantRelationKind.oneToMany',
        }
        return (
            "AssistantRelationField(\n"
            f"          name: {self._assistant_dart_string_literal(rel['name'])},\n"
            f"          targetEntity: {self._assistant_dart_string_literal(rel['target_entity'])},\n"
            f"          kind: {kind_map[rel['kind']]},\n"
            f"          jsonKey: {self._assistant_dart_string_literal(rel['json_key'])},\n"
            f"          requiredOnCreate: {str(rel['required_on_create']).lower()},\n"
            f"          writable: {str(rel['writable']).lower()},\n"
            "        )"
        )

    def _generate_app_schema(self, base_path, original_classes):
        """Genera lib/assistant/app_schema.dart a partir de las clases UML
        originales (excluye entidades intermedias M:N)."""
        entity_literals = []
        for clase in original_classes:
            meta = self._assistant_entity_metadata(clase)
            fields_str = ',\n        '.join(self._assistant_render_field(f) for f in meta['fields'])
            relations_str = ',\n        '.join(self._assistant_render_relation(r) for r in meta['relations'])
            name_field_literal = (
                self._assistant_dart_string_literal(meta['name_field'])
                if meta['name_field'] else 'null'
            )
            entity_literals.append(
                "    AssistantEntitySchema(\n"
                f"      name: {self._assistant_dart_string_literal(meta['name'])},\n"
                f"      aliases: [{self._assistant_dart_string_literal(meta['name'].lower())}],\n"
                "      fields: [\n"
                f"        {fields_str}\n"
                "      ],\n"
                "      relations: [\n"
                f"        {relations_str}\n"
                "      ],\n"
                f"      nameField: {name_field_literal},\n"
                "    )"
            )
        entities_str = ',\n'.join(entity_literals)

        content = '''/// Esquema de entidades derivado del UML, usado por el asistente
/// (CommandParser, CommandValidator, CommandRouter). Generado
/// automáticamente: no editar a mano, regenerar el proyecto Flutter.
class AssistantFieldSchema {
  final String name;
  final String dartType;
  final String jsonKey;
  final bool isPrimaryKey;
  final bool isAutoIncrement;
  final bool requiredOnCreate;
  final bool writable;

  const AssistantFieldSchema({
    required this.name,
    required this.dartType,
    required this.jsonKey,
    required this.isPrimaryKey,
    required this.isAutoIncrement,
    required this.requiredOnCreate,
    required this.writable,
  });
}

enum AssistantRelationKind { manyToOne, oneToOne, oneToMany }

class AssistantRelationField {
  final String name;
  final String targetEntity;
  final AssistantRelationKind kind;
  final String jsonKey;
  final bool requiredOnCreate;
  final bool writable;

  const AssistantRelationField({
    required this.name,
    required this.targetEntity,
    required this.kind,
    required this.jsonKey,
    required this.requiredOnCreate,
    required this.writable,
  });
}

class AssistantEntitySchema {
  final String name;
  final List<String> aliases;
  final List<AssistantFieldSchema> fields;
  final List<AssistantRelationField> relations;
  final String? nameField;

  const AssistantEntitySchema({
    required this.name,
    required this.aliases,
    required this.fields,
    required this.relations,
    required this.nameField,
  });

  AssistantFieldSchema get pkField => fields.firstWhere((f) => f.isPrimaryKey);

  /// Campos escalares más los IDs de relación many-to-one/one-to-one,
  /// tratados de forma uniforme como campos String escribibles. Las
  /// relaciones one-to-many nunca se incluyen: son listas de solo lectura,
  /// el asistente nunca las escribe.
  List<AssistantFieldSchema> get allWritableFields => [
        ...fields,
        ...relations.where((r) => r.kind != AssistantRelationKind.oneToMany).map(
              (r) => AssistantFieldSchema(
                name: r.name,
                dartType: 'String',
                jsonKey: r.jsonKey,
                isPrimaryKey: false,
                isAutoIncrement: false,
                requiredOnCreate: r.requiredOnCreate,
                writable: r.writable,
              ),
            ),
      ];

  AssistantFieldSchema? fieldByName(String candidate) {
    final normalized = AppSchema.normalize(candidate);
    for (final field in allWritableFields) {
      if (AppSchema.normalize(field.name) == normalized) return field;
    }
    return null;
  }

  /// Convierte un mapa indexado por nombre de campo Dart (como el que
  /// produce CommandParser) en un mapa indexado por la clave JSON del
  /// backend (la que esperan los fromJson generados). Las claves
  /// desconocidas se descartan; CommandValidator ya debe haber rechazado
  /// campos desconocidos antes de llegar aquí.
  Map<String, dynamic> toJsonKeyed(Map<String, dynamic> fieldKeyedData) {
    final result = <String, dynamic>{};
    for (final entry in fieldKeyedData.entries) {
      final field = fieldByName(entry.key);
      if (field != null) {
        result[field.jsonKey] = entry.value;
      }
    }
    return result;
  }
}

class AppSchema {
  static const List<AssistantEntitySchema> entities = [
__ENTITIES__
  ];

  /// Resuelve un token en español (ya extraído por CommandParser) a una
  /// entidad conocida. Aplica una normalización singular/plural ingenua,
  /// pero nunca inventa traducciones ni sinónimos. Devuelve null tanto si
  /// no hay coincidencia como si es ambigua: en ambos casos el llamador
  /// debe tratarlo como "entidad desconocida" y no ejecutar nada.
  static AssistantEntitySchema? resolveEntity(String token) {
    final normalized = normalize(token);
    final singularized = normalize(_singularize(token));
    AssistantEntitySchema? match;
    for (final entity in entities) {
      final candidates = <String>{entity.name, ...entity.aliases};
      for (final candidate in candidates) {
        final normalizedCandidate = normalize(candidate);
        if (normalizedCandidate == normalized || normalizedCandidate == singularized) {
          if (match != null && match.name != entity.name) {
            return null;
          }
          match = entity;
        }
      }
    }
    return match;
  }

  /// Entidades que declaran un campo o relación escribible llamado
  /// [fieldToken] (comparación sin mayúsculas/tildes). Lo usa la gramática
  /// de UPDATE de CommandParser para inferir la entidad a partir del campo.
  static List<AssistantEntitySchema> entitiesWithField(String fieldToken) {
    final normalized = normalize(fieldToken);
    return entities
        .where((entity) => entity.allWritableFields.any((field) => normalize(field.name) == normalized))
        .toList();
  }

  static String _singularize(String word) {
    final lower = word.toLowerCase();
    if (lower.endsWith('es') && lower.length > 3) {
      return lower.substring(0, lower.length - 2);
    }
    if (lower.endsWith('s') && lower.length > 1) {
      return lower.substring(0, lower.length - 1);
    }
    return lower;
  }

  /// Minúsculas y sin tildes agudas, para comparaciones deterministas. A
  /// propósito NO toca 'ñ'/'ü': son letras propias del español, no vocales
  /// acentuadas.
  static String normalize(String value) {
    const from = 'áéíóúÁÉÍÓÚ';
    const to = 'aeiouAEIOU';
    var result = value.trim().toLowerCase();
    for (var i = 0; i < from.length; i++) {
      result = result.replaceAll(from[i], to[i].toLowerCase());
    }
    return result;
  }
}
'''
        content = content.replace('__ENTITIES__', entities_str)
        (base_path / 'lib' / 'assistant' / 'app_schema.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_business_command(self, base_path):
        """Genera lib/assistant/business_command.dart (genérico)."""
        content = '''/// Comando genérico producido por CommandParser tras interpretar una
/// instrucción escrita o hablada. Esta clase no contiene lógica: toda la
/// validación ocurre en CommandValidator y toda la ejecución ocurre en
/// CommandRouter. Un futuro intérprete de lenguaje natural podría
/// reemplazar CommandParser sin tocar CommandValidator, CommandRouter ni
/// este archivo, siempre que siga produciendo BusinessCommand.
enum CommandAction { create, read, update, delete, unknown }

class BusinessCommand {
  /// Qué quiere hacer el usuario.
  final CommandAction action;

  /// Nombre canónico de la entidad, tal como aparece en AppSchema
  /// (por ejemplo, 'Producto').
  final String entity;

  /// Valores a escribir (CREATE) o a aplicar (UPDATE), indexados por
  /// nombre de campo Dart (no por clave JSON del backend).
  final Map<String, dynamic> data;

  /// Valores usados para ubicar el/los registro(s) objetivo
  /// (READ de uno solo/UPDATE/DELETE). Vacío en CREATE y en READ/LIST de
  /// todos los registros.
  final Map<String, dynamic> filters;

  /// Texto original a partir del cual se interpretó el comando. Se
  /// conserva para mensajes de error y para mostrarle al usuario qué se
  /// entendió.
  final String rawText;

  const BusinessCommand({
    required this.action,
    required this.entity,
    required this.data,
    required this.filters,
    required this.rawText,
  });

  @override
  String toString() =>
      'BusinessCommand(action: $action, entity: $entity, data: $data, filters: $filters)';
}
'''
        (base_path / 'lib' / 'assistant' / 'business_command.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_entity_service_adapter(self, base_path):
        """Genera lib/assistant/entity_service_adapter.dart (genérico)."""
        content = '''import 'app_schema.dart';

/// Interfaz uniforme que usa CommandRouter para llegar al {Entity}Service
/// generado concreto sin conocer su tipo. Se genera una implementación por
/// cada entidad UML original en entity_service_registry.dart, y cada
/// implementación solo llama a los métodos del Service ya generado (getAll,
/// create, update, delete) — nunca a DatabaseHelper ni a dart:http
/// directamente — de modo que el asistente hereda automáticamente el
/// comportamiento de red-primero/respaldo-SQLite que esos servicios ya
/// tienen.
abstract class EntityServiceAdapter {
  final AssistantEntitySchema schema;
  const EntityServiceAdapter(this.schema);

  Future<List<Map<String, dynamic>>> list();
  Future<Map<String, dynamic>> create(Map<String, dynamic> jsonData);
  Future<Map<String, dynamic>> updateFromMap(String id, Map<String, dynamic> mergedJsonData);
  Future<void> deleteById(String id);
}
'''
        (base_path / 'lib' / 'assistant' / 'entity_service_adapter.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_command_parser(self, base_path):
        """Genera lib/assistant/command_parser.dart (genérico: consulta
        AppSchema en tiempo de ejecución, no depende del esquema UML en
        tiempo de generación)."""
        content = r'''import 'app_schema.dart';
import 'business_command.dart';

/// Resultado de intentar interpretar un texto como comando. [error] viene
/// acompañado de un mensaje pensado para mostrarse tal cual al usuario.
class ParsedCommandResult {
  final BusinessCommand? command;
  final String? error;

  const ParsedCommandResult.success(BusinessCommand command)
      : command = command,
        error = null;

  const ParsedCommandResult.failure(String error)
      : command = null,
        error = error;

  bool get isSuccess => command != null;
}

/// Parser determinista y consciente del esquema para un conjunto acotado de
/// comandos CRUD en español. Esto es reconocimiento de patrones de gramática
/// fija — NO es un modelo de lenguaje ni IA. Cualquier entrada que no
/// encaje en las formas soportadas falla de forma cerrada: se devuelve un
/// [ParsedCommandResult.failure] y nunca se produce un BusinessCommand
/// parcial ni una ejecución "mejor esfuerzo".
class CommandParser {
  static const Map<String, CommandAction> _actionVerbs = {
    'registra': CommandAction.create,
    'registrar': CommandAction.create,
    'crea': CommandAction.create,
    'crear': CommandAction.create,
    'agrega': CommandAction.create,
    'agregar': CommandAction.create,
    'añade': CommandAction.create,
    'añadir': CommandAction.create,
    'muestra': CommandAction.read,
    'muestrame': CommandAction.read,
    'listar': CommandAction.read,
    'lista': CommandAction.read,
    'ver': CommandAction.read,
    'busca': CommandAction.read,
    'buscar': CommandAction.read,
    'encuentra': CommandAction.read,
    'actualiza': CommandAction.update,
    'actualizar': CommandAction.update,
    'modifica': CommandAction.update,
    'modificar': CommandAction.update,
    'cambia': CommandAction.update,
    'cambiar': CommandAction.update,
    'edita': CommandAction.update,
    'editar': CommandAction.update,
    'elimina': CommandAction.delete,
    'eliminar': CommandAction.delete,
    'borra': CommandAction.delete,
    'borrar': CommandAction.delete,
    'quita': CommandAction.delete,
    'quitar': CommandAction.delete,
  };

  static const Set<String> _leadingArticles = {
    'un', 'una', 'unos', 'unas', 'el', 'la', 'los', 'las',
  };

  ParsedCommandResult parse(String rawText) {
    final trimmed = rawText.trim();
    if (trimmed.isEmpty) {
      return const ParsedCommandResult.failure('Escribe o di un comando.');
    }

    final tokens = _splitWords(trimmed);
    final verbToken = tokens.first;
    final rest = tokens.length > 1 ? tokens.sublist(1).join(' ') : '';

    final action = _actionVerbs[AppSchema.normalize(verbToken)];
    if (action == null) {
      return ParsedCommandResult.failure('No reconozco la acción "$verbToken".');
    }

    switch (action) {
      case CommandAction.create:
        return _parseCreate(rest, trimmed);
      case CommandAction.read:
        return _parseReadOrDelete(rest, trimmed, CommandAction.read);
      case CommandAction.delete:
        return _parseReadOrDelete(rest, trimmed, CommandAction.delete);
      case CommandAction.update:
        return _parseUpdate(rest, trimmed);
      case CommandAction.unknown:
        return const ParsedCommandResult.failure('No reconozco esa acción.');
    }
  }

  ParsedCommandResult _parseCreate(String rest, String rawText) {
    if (rest.isEmpty) {
      return const ParsedCommandResult.failure('Falta indicar qué crear.');
    }

    final conMatch = RegExp(r'\s+con\s+', caseSensitive: false).firstMatch(rest);
    final beforeCon = conMatch == null ? rest : rest.substring(0, conMatch.start);
    final afterCon = conMatch == null ? '' : rest.substring(conMatch.end);

    final beforeTokens = _splitWords(beforeCon);
    if (beforeTokens.isEmpty) {
      return const ParsedCommandResult.failure('Falta indicar qué crear.');
    }
    var cursor = 0;
    if (_leadingArticles.contains(AppSchema.normalize(beforeTokens[cursor]))) {
      cursor++;
    }
    if (cursor >= beforeTokens.length) {
      return const ParsedCommandResult.failure('Falta indicar la entidad a crear.');
    }
    final entityToken = beforeTokens[cursor];
    final entity = AppSchema.resolveEntity(entityToken);
    if (entity == null) {
      return ParsedCommandResult.failure('No conozco la entidad "$entityToken".');
    }
    final nameValueRaw = beforeTokens.sublist(cursor + 1).join(' ').trim();

    final data = <String, dynamic>{};
    if (nameValueRaw.isNotEmpty) {
      if (entity.nameField == null) {
        return ParsedCommandResult.failure(
            'No sé qué hacer con "$nameValueRaw" para ${entity.name}.');
      }
      data[entity.nameField!] = nameValueRaw;
    }

    if (afterCon.trim().isNotEmpty) {
      final clauses = afterCon.split(RegExp(r'\s+y\s+', caseSensitive: false));
      for (final rawClause in clauses) {
        final clause = rawClause.trim();
        if (clause.isEmpty) continue;
        final clauseTokens = _splitWords(clause);
        if (clauseTokens.length < 2) {
          return ParsedCommandResult.failure('No entendí "$clause".');
        }
        final fieldToken = clauseTokens.first;
        final valueRaw = clauseTokens.sublist(1).join(' ').trim();
        final field = entity.fieldByName(fieldToken);
        if (field == null) {
          return ParsedCommandResult.failure(
              'No reconozco el campo "$fieldToken" en ${entity.name}.');
        }
        if (data.containsKey(field.name)) {
          return ParsedCommandResult.failure('El campo "$fieldToken" está repetido.');
        }
        data[field.name] = valueRaw;
      }
    }

    return ParsedCommandResult.success(BusinessCommand(
      action: CommandAction.create,
      entity: entity.name,
      data: data,
      filters: const {},
      rawText: rawText,
    ));
  }

  ParsedCommandResult _parseReadOrDelete(String rest, String rawText, CommandAction action) {
    if (rest.isEmpty) {
      return const ParsedCommandResult.failure('Falta indicar sobre qué entidad.');
    }
    final tokens = _splitWords(rest);
    var cursor = 0;
    if (_leadingArticles.contains(AppSchema.normalize(tokens[cursor]))) {
      cursor++;
    }
    if (cursor >= tokens.length) {
      return const ParsedCommandResult.failure('Falta indicar la entidad.');
    }
    final entityToken = tokens[cursor];
    final entity = AppSchema.resolveEntity(entityToken);
    if (entity == null) {
      return ParsedCommandResult.failure('No conozco la entidad "$entityToken".');
    }
    final leftover = tokens.sublist(cursor + 1).join(' ').trim();

    final filters = <String, dynamic>{};
    if (leftover.isNotEmpty) {
      if (entity.nameField == null) {
        return ParsedCommandResult.failure('No sé cómo buscar "$leftover" en ${entity.name}.');
      }
      filters[entity.nameField!] = leftover;
    } else if (action == CommandAction.delete) {
      return ParsedCommandResult.failure(
          'Indica cuál ${entity.name} eliminar (por ejemplo, su nombre).');
    }

    return ParsedCommandResult.success(BusinessCommand(
      action: action,
      entity: entity.name,
      data: const {},
      filters: filters,
      rawText: rawText,
    ));
  }

  ParsedCommandResult _parseUpdate(String rest, String rawText) {
    if (rest.isEmpty) {
      return const ParsedCommandResult.failure('Falta indicar qué actualizar.');
    }

    final aMatches = RegExp(r'\s+a\s+', caseSensitive: false).allMatches(rest).toList();
    if (aMatches.isEmpty) {
      return const ParsedCommandResult.failure('Indica el nuevo valor con "... a <valor>".');
    }
    final lastA = aMatches.last;
    final left = rest.substring(0, lastA.start).trim();
    final right = rest.substring(lastA.end).trim();
    if (left.isEmpty || right.isEmpty) {
      return const ParsedCommandResult.failure('Indica el nuevo valor con "... a <valor>".');
    }

    final leftTokens = _splitWords(left);
    var cursor = 0;
    if (_leadingArticles.contains(AppSchema.normalize(leftTokens[cursor]))) {
      cursor++;
    }
    if (cursor >= leftTokens.length) {
      return const ParsedCommandResult.failure('No entendí qué actualizar.');
    }
    final firstToken = leftTokens[cursor];

    final candidatesByField = AppSchema.entitiesWithField(firstToken);
    if (candidatesByField.length > 1) {
      return ParsedCommandResult.failure(
          'El campo "$firstToken" existe en varias entidades; sé más específico.');
    }
    if (candidatesByField.length == 1) {
      // Modo B: el campo va primero y la entidad se infiere a partir de él.
      final entity = candidatesByField.first;
      final field = entity.fieldByName(firstToken)!;
      var targetRaw = leftTokens.sublist(cursor + 1).join(' ').trim();
      targetRaw = _stripLeadingWord(targetRaw, 'de');
      if (targetRaw.isEmpty) {
        return ParsedCommandResult.failure('Indica cuál ${entity.name} actualizar.');
      }
      if (entity.nameField == null) {
        return ParsedCommandResult.failure('No sé cómo identificar ${entity.name} por nombre.');
      }
      return ParsedCommandResult.success(BusinessCommand(
        action: CommandAction.update,
        entity: entity.name,
        data: {field.name: right},
        filters: {entity.nameField!: targetRaw},
        rawText: rawText,
      ));
    }

    // Modo A: la entidad va primero y el campo se toma de la cláusula
    // posterior al último "a".
    final entity = AppSchema.resolveEntity(firstToken);
    if (entity == null) {
      return ParsedCommandResult.failure('No reconozco "$firstToken".');
    }
    final targetRaw = leftTokens.sublist(cursor + 1).join(' ').trim();
    if (targetRaw.isEmpty) {
      return ParsedCommandResult.failure('Indica cuál ${entity.name} actualizar.');
    }
    if (entity.nameField == null) {
      return ParsedCommandResult.failure('No sé cómo identificar ${entity.name} por nombre.');
    }
    final rightTokens = _splitWords(right);
    if (rightTokens.length < 2) {
      return ParsedCommandResult.failure('Indica qué campo actualizar y su valor.');
    }
    final fieldToken = rightTokens.first;
    final newValueRaw = rightTokens.sublist(1).join(' ').trim();
    final field = entity.fieldByName(fieldToken);
    if (field == null) {
      return ParsedCommandResult.failure('No reconozco el campo "$fieldToken" en ${entity.name}.');
    }

    return ParsedCommandResult.success(BusinessCommand(
      action: CommandAction.update,
      entity: entity.name,
      data: {field.name: newValueRaw},
      filters: {entity.nameField!: targetRaw},
      rawText: rawText,
    ));
  }

  List<String> _splitWords(String value) =>
      value.trim().split(RegExp(r'\s+')).where((t) => t.isNotEmpty).toList();

  String _stripLeadingWord(String value, String word) {
    final tokens = _splitWords(value);
    if (tokens.isNotEmpty && AppSchema.normalize(tokens.first) == word) {
      return tokens.sublist(1).join(' ').trim();
    }
    return value;
  }
}
'''
        (base_path / 'lib' / 'assistant' / 'command_parser.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_command_validator(self, base_path):
        """Genera lib/assistant/command_validator.dart (genérico: valida
        contra AppSchema en tiempo de ejecución)."""
        content = '''import 'app_schema.dart';
import 'business_command.dart';

/// Resultado de validar un BusinessCommand ya interpretado.
class ValidationResult {
  final bool isValid;
  final BusinessCommand? command;
  final String? error;

  const ValidationResult.valid(BusinessCommand command)
      : isValid = true,
        command = command,
        error = null;

  const ValidationResult.invalid(String error)
      : isValid = false,
        command = null,
        error = error;
}

/// Valida un BusinessCommand ya interpretado contra AppSchema antes de
/// llamar a cualquier servicio. No realiza E/S ni efectos secundarios: solo
/// clasifica si el comando es seguro de ejecutar.
///
/// IMPORTANTE: el BusinessCommand devuelto en un ValidationResult.valid
/// NO es el mismo que se recibió. Su `data` se reemplaza por los valores ya
/// coercionados a su tipo Dart real (String recortado, int, double con coma
/// normalizada a punto, o bool) — CommandRouter y los adaptadores deben usar
/// SIEMPRE ese `data` coercionado, nunca los strings crudos originales.
///
/// Los requisitos replican exactamente el comportamiento actual de los
/// formularios generados: la PK numérica autoincremental (int o double) se
/// omite en CREATE y se rechaza si se indica explícitamente, la PK String es
/// obligatoria, los atributos escalares y heredados son obligatorios, y los
/// IDs de relación many-to-one/one-to-one son obligatorios. Una entidad con
/// PK double queda inhabilitada para CREATE, UPDATE y DELETE en este P0
/// (READ sigue disponible); los campos de fecha (Date/DateTime) se marcan no
/// escribibles por las inconsistencias conocidas en su generación actual —
/// ninguna de las dos cosas se corrige aquí.
class CommandValidator {
  ValidationResult validate(BusinessCommand command) {
    if (command.action == CommandAction.unknown) {
      return const ValidationResult.invalid('Comando no reconocido.');
    }

    final matches = AppSchema.entities.where((e) => e.name == command.entity).toList();
    if (matches.isEmpty) {
      return ValidationResult.invalid('No conozco la entidad "${command.entity}".');
    }
    final entity = matches.first;

    for (final key in command.data.keys) {
      if (entity.fieldByName(key) == null) {
        return ValidationResult.invalid('No reconozco el campo "$key" en ${entity.name}.');
      }
    }
    for (final key in command.filters.keys) {
      if (entity.fieldByName(key) == null) {
        return ValidationResult.invalid('No reconozco el campo "$key" en ${entity.name}.');
      }
    }

    switch (command.action) {
      case CommandAction.create:
        return _validateCreate(entity, command);
      case CommandAction.read:
        return ValidationResult.valid(command);
      case CommandAction.update:
        return _validateMutation(entity, command, requireData: true);
      case CommandAction.delete:
        return _validateMutation(entity, command, requireData: false);
      case CommandAction.unknown:
        return const ValidationResult.invalid('Comando no reconocido.');
    }
  }

  ValidationResult _validateCreate(AssistantEntitySchema entity, BusinessCommand command) {
    if (entity.pkField.dartType == 'double') {
      return ValidationResult.invalid(
          '${entity.name} usa una clave primaria double; el asistente no soporta crear, '
          'actualizar ni eliminar registros de esa entidad en este P0.');
    }

    if (entity.pkField.isAutoIncrement && command.data.containsKey(entity.pkField.name)) {
      return ValidationResult.invalid(
          '"${entity.pkField.name}" se genera automáticamente; no lo indiques al crear un ${entity.name}.');
    }

    for (final field in entity.allWritableFields) {
      if (field.isPrimaryKey && field.isAutoIncrement) continue;
      final provided = command.data.containsKey(field.name);
      if (!field.writable) {
        if (provided) {
          return ValidationResult.invalid(
              'El campo "${field.name}" no es compatible con el asistente todavía.');
        }
        if (field.requiredOnCreate) {
          return ValidationResult.invalid(
              '${entity.name} requiere "${field.name}", que aún no es compatible con el asistente.');
        }
        continue;
      }
      if (field.requiredOnCreate && !provided) {
        return ValidationResult.invalid('Falta el campo "${field.name}".');
      }
    }

    final coercedData = <String, dynamic>{};
    for (final entry in command.data.entries) {
      final field = entity.fieldByName(entry.key)!;
      final coerced = _coerce(field, entry.value.toString());
      if (coerced == null) {
        return ValidationResult.invalid('El valor de "${field.name}" no es válido para su tipo.');
      }
      coercedData[entry.key] = coerced;
    }

    return ValidationResult.valid(BusinessCommand(
      action: command.action,
      entity: command.entity,
      data: coercedData,
      filters: command.filters,
      rawText: command.rawText,
    ));
  }

  ValidationResult _validateMutation(
    AssistantEntitySchema entity,
    BusinessCommand command, {
    required bool requireData,
  }) {
    if (entity.pkField.dartType == 'double') {
      return ValidationResult.invalid(
          '${entity.name} usa una clave primaria double; el asistente no soporta crear, '
          'actualizar ni eliminar registros de esa entidad en este P0.');
    }
    if (command.filters.isEmpty) {
      return ValidationResult.invalid('Indica cuál ${entity.name} quieres afectar.');
    }
    if (requireData && command.data.isEmpty) {
      return ValidationResult.invalid('Indica qué campo actualizar.');
    }
    final coercedData = <String, dynamic>{};
    for (final entry in command.data.entries) {
      final field = entity.fieldByName(entry.key)!;
      if (!field.writable) {
        return ValidationResult.invalid(
            'El campo "${field.name}" no es compatible con el asistente todavía.');
      }
      final coerced = _coerce(field, entry.value.toString());
      if (coerced == null) {
        return ValidationResult.invalid('El valor de "${field.name}" no es válido para su tipo.');
      }
      coercedData[entry.key] = coerced;
    }
    return ValidationResult.valid(BusinessCommand(
      action: command.action,
      entity: command.entity,
      data: coercedData,
      filters: command.filters,
      rawText: command.rawText,
    ));
  }

  /// La coerción refleja las mismas restricciones que los formularios
  /// CREATE generados: los valores int/double/bool deben parsear
  /// limpiamente o se rechazan por completo.
  static dynamic coerce(AssistantFieldSchema field, String raw) => _coerce(field, raw);

  static dynamic _coerce(AssistantFieldSchema field, String raw) {
    final value = raw.trim();
    switch (field.dartType) {
      case 'String':
        return value;
      case 'int':
        return int.tryParse(value);
      case 'double':
        return double.tryParse(value.replaceAll(',', '.'));
      case 'bool':
        final normalized = AppSchema.normalize(value);
        if (normalized == 'true' || normalized == 'si' || normalized == 'activo' || normalized == 'verdadero') {
          return true;
        }
        if (normalized == 'false' || normalized == 'no' || normalized == 'inactivo' || normalized == 'falso') {
          return false;
        }
        return null;
      case 'DateTime':
        return null;
      default:
        return null;
    }
  }
}
'''
        (base_path / 'lib' / 'assistant' / 'command_validator.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_entity_service_registry(self, base_path, original_classes):
        """Genera lib/assistant/entity_service_registry.dart: una clase
        adaptadora mínima por cada entidad UML original que SOLO llama a los
        {Name}Service ya generados (nunca a DatabaseHelper ni a dart:http
        directamente), reutilizando fromJson/toJson tal como están."""
        adapter_template = (
            "class _{name}Adapter extends EntityServiceAdapter {{\n"
            "  _{name}Adapter(AssistantEntitySchema schema) : super(schema);\n"
            "  final {name}Service _service = {name}Service();\n"
            "\n"
            "  @override\n"
            "  Future<List<Map<String, dynamic>>> list() async =>\n"
            "      (await _service.getAll()).map((item) => item.toJson()).toList();\n"
            "\n"
            "  @override\n"
            "  Future<Map<String, dynamic>> create(Map<String, dynamic> jsonData) async {{\n"
            "    final created = await _service.create({name}.fromJson(jsonData));\n"
            "    return created.toJson();\n"
            "  }}\n"
            "\n"
            "  @override\n"
            "  Future<Map<String, dynamic>> updateFromMap(String id, Map<String, dynamic> mergedJsonData) async {{\n"
            "    final updated = await _service.update(id, {name}.fromJson(mergedJsonData));\n"
            "    return updated.toJson();\n"
            "  }}\n"
            "\n"
            "  @override\n"
            "  Future<void> deleteById(String id) => _service.delete(id);\n"
            "}}"
        )

        imports = []
        adapters = []
        map_entries = []
        for clase in original_classes:
            name = clase['name']
            snake = self._to_snake_case(name)
            imports.append(f"import '../models/{snake}.dart';")
            imports.append(f"import '../services/{snake}_service.dart';")
            adapters.append(adapter_template.format(name=name))
            name_literal = self._assistant_dart_string_literal(name)
            map_entries.append(
                f"  {name_literal}: _{name}Adapter(\n"
                f"    AppSchema.entities.firstWhere((e) => e.name == {name_literal}),\n"
                "  ),"
            )

        imports_str = "\n".join(dict.fromkeys(imports))
        adapters_str = "\n\n".join(adapters)
        map_entries_str = "\n".join(map_entries)

        content = (
            "import 'app_schema.dart';\n"
            "import 'entity_service_adapter.dart';\n"
            f"{imports_str}\n"
            "\n"
            f"{adapters_str}\n"
            "\n"
            "final Map<String, EntityServiceAdapter> entityServiceRegistry = {\n"
            f"{map_entries_str}\n"
            "};\n"
        )
        (base_path / 'lib' / 'assistant' / 'entity_service_registry.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_command_router(self, base_path):
        """Genera lib/assistant/command_router.dart (genérico)."""
        content = '''import 'app_schema.dart';
import 'business_command.dart';
import 'entity_service_adapter.dart';
import 'entity_service_registry.dart';

/// Resultado de ejecutar (o intentar ejecutar) un BusinessCommand.
/// [pendingDelete] solo se establece cuando un objetivo de DELETE fue
/// resuelto con éxito y todavía necesita confirmación explícita del
/// usuario — ver [CommandRouter.confirmDelete].
class RouterOutcome {
  final bool success;
  final String message;
  final List<Map<String, dynamic>> rows;
  final PendingDelete? pendingDelete;

  const RouterOutcome({
    required this.success,
    required this.message,
    this.rows = const [],
    this.pendingDelete,
  });
}

class PendingDelete {
  final String entity;
  final String pk;
  final Map<String, dynamic> preview;
  const PendingDelete({required this.entity, required this.pk, required this.preview});
}

/// Ejecuta BusinessCommand ya validados contra la capa {Entity}Service
/// generada, a través de un registro de adaptadores (por defecto,
/// entityServiceRegistry). Nunca importa DatabaseHelper ni dart:http
/// directamente, y nunca confía en ninguna bandera de confirmación provista
/// por el llamador: la seguridad de DELETE se deriva únicamente de
/// `command.action == CommandAction.delete`, que dispara un flujo de dos
/// fases: resolver aquí (execute) y luego confirmar explícitamente
/// (confirmDelete). El registro es inyectable solo para permitir pruebas
/// unitarias con adaptadores falsos; en la app real siempre se usa el
/// registro generado.
class CommandRouter {
  final Map<String, EntityServiceAdapter> _registry;

  CommandRouter({Map<String, EntityServiceAdapter>? registry})
      : _registry = registry ?? entityServiceRegistry;

  Future<RouterOutcome> execute(BusinessCommand command) async {
    final adapter = _registry[command.entity];
    if (adapter == null) {
      return RouterOutcome(success: false, message: 'Entidad no soportada: ${command.entity}.');
    }
    final schema = adapter.schema;

    switch (command.action) {
      case CommandAction.create:
        return _executeCreate(adapter, schema, command);
      case CommandAction.read:
        return _executeRead(adapter, schema, command);
      case CommandAction.update:
        return _executeUpdate(adapter, schema, command);
      case CommandAction.delete:
        return _resolveDelete(adapter, schema, command);
      case CommandAction.unknown:
        return const RouterOutcome(success: false, message: 'Comando no reconocido.');
    }
  }

  /// Fase 2 de DELETE. [pending] DEBE provenir de un PendingDelete devuelto
  /// previamente por [execute] — nunca se vuelve a derivar a partir de
  /// filtros, de modo que confirmar nunca puede volver a ejecutar el
  /// emparejamiento difuso contra datos que pudieron haber cambiado.
  Future<RouterOutcome> confirmDelete(PendingDelete pending) async {
    final adapter = _registry[pending.entity];
    if (adapter == null) {
      return RouterOutcome(success: false, message: 'Entidad no soportada: ${pending.entity}.');
    }
    await adapter.deleteById(pending.pk);
    return const RouterOutcome(success: true, message: 'Eliminado correctamente.');
  }

  Future<RouterOutcome> _executeCreate(
    EntityServiceAdapter adapter,
    AssistantEntitySchema schema,
    BusinessCommand command,
  ) async {
    final jsonData = schema.toJsonKeyed(command.data);
    final created = await adapter.create(jsonData);
    return RouterOutcome(success: true, message: '${schema.name} creado correctamente.', rows: [created]);
  }

  Future<RouterOutcome> _executeRead(
    EntityServiceAdapter adapter,
    AssistantEntitySchema schema,
    BusinessCommand command,
  ) async {
    final all = await adapter.list();
    if (command.filters.isEmpty) {
      return RouterOutcome(success: true, message: '${all.length} resultado(s).', rows: all);
    }
    final matches = _matchRows(all, schema, command.filters, exact: false);
    return RouterOutcome(
      success: true,
      message: matches.isEmpty ? 'Sin resultados.' : '${matches.length} resultado(s).',
      rows: matches,
    );
  }

  Future<RouterOutcome> _executeUpdate(
    EntityServiceAdapter adapter,
    AssistantEntitySchema schema,
    BusinessCommand command,
  ) async {
    final all = await adapter.list();
    final matches = _matchRows(all, schema, command.filters, exact: true);
    if (matches.isEmpty) {
      return const RouterOutcome(success: false, message: 'No encontré ningún registro que coincida.');
    }
    if (matches.length > 1) {
      return RouterOutcome(
        success: false,
        message: 'La búsqueda es ambigua: coinciden ${matches.length} registros.',
        rows: matches,
      );
    }
    final target = matches.first;
    final pk = target[schema.pkField.jsonKey];
    final merged = Map<String, dynamic>.from(target)..addAll(schema.toJsonKeyed(command.data));
    final updated = await adapter.updateFromMap(pk.toString(), merged);
    return RouterOutcome(success: true, message: '${schema.name} actualizado correctamente.', rows: [updated]);
  }

  Future<RouterOutcome> _resolveDelete(
    EntityServiceAdapter adapter,
    AssistantEntitySchema schema,
    BusinessCommand command,
  ) async {
    final all = await adapter.list();
    final matches = _matchRows(all, schema, command.filters, exact: true);
    if (matches.isEmpty) {
      return const RouterOutcome(success: false, message: 'No encontré ningún registro que coincida.');
    }
    if (matches.length > 1) {
      return RouterOutcome(
        success: false,
        message: 'La búsqueda es ambigua: coinciden ${matches.length} registros.',
        rows: matches,
      );
    }
    final target = matches.first;
    final pk = target[schema.pkField.jsonKey].toString();
    return RouterOutcome(
      success: true,
      message: 'Confirma la eliminación de este registro.',
      pendingDelete: PendingDelete(entity: schema.name, pk: pk, preview: target),
    );
  }

  List<Map<String, dynamic>> _matchRows(
    List<Map<String, dynamic>> rows,
    AssistantEntitySchema schema,
    Map<String, dynamic> filters, {
    required bool exact,
  }) {
    return rows.where((row) {
      for (final entry in filters.entries) {
        final field = schema.fieldByName(entry.key);
        if (field == null) return false;
        final rowValue = row[field.jsonKey];
        if (!_valuesMatch(rowValue, entry.value, exact: exact)) return false;
      }
      return true;
    }).toList();
  }

  bool _valuesMatch(dynamic rowValue, dynamic filterValue, {required bool exact}) {
    final rowText = AppSchema.normalize(rowValue?.toString() ?? '');
    final filterText = AppSchema.normalize(filterValue?.toString() ?? '');
    if (exact) return rowText == filterText;
    return rowText.contains(filterText);
  }
}
'''
        (base_path / 'lib' / 'assistant' / 'command_router.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_voice_input_controller(self, base_path):
        """Genera lib/assistant/voice_input_controller.dart (genérico)."""
        content = '''import 'package:flutter/foundation.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

/// Envoltorio delgado sobre package:speech_to_text. La voz es solo un
/// mecanismo de entrada: lo que se reconoce se entrega al mismo pipeline de
/// CommandParser que usa el texto escrito — nunca se salta la validación.
/// Este controlador NO afirma reconocimiento offline/en el dispositivo: la
/// disponibilidad, el idioma soportado y la dependencia de red varían según
/// la plataforma, el sistema operativo y el servicio de reconocimiento de
/// voz instalado, y no se han verificado aquí. Requiere los permisos de
/// micrófono/reconocimiento de voz nativos correspondientes (ver la
/// documentación del generador CASE para los pasos exactos).
///
/// Deliberadamente no se inicializa en Web.
class VoiceInputController {
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _available = false;
  bool _initialized = false;

  bool get isAvailable => _available;
  bool get isListening => _speech.isListening;

  Future<bool> initialize() async {
    if (kIsWeb) {
      _initialized = true;
      _available = false;
      return false;
    }
    if (_initialized) return _available;
    try {
      _available = await _speech.initialize(
        onStatus: (status) => debugPrint('VoiceInputController status: $status'),
        onError: (error) => debugPrint('VoiceInputController error: $error'),
      );
    } catch (error) {
      debugPrint('VoiceInputController initialize failed: $error');
      _available = false;
    }
    _initialized = true;
    return _available;
  }

  Future<void> startListening({required void Function(String recognizedText) onResult}) async {
    if (kIsWeb || !_available) return;
    try {
      await _speech.listen(
        onResult: (result) {
          if (result.finalResult && result.recognizedWords.isNotEmpty) {
            onResult(result.recognizedWords);
          }
        },
        listenOptions: stt.SpeechListenOptions(localeId: 'es_ES'),
      );
    } catch (error) {
      debugPrint('VoiceInputController listen failed: $error');
    }
  }

  Future<void> stopListening() async {
    if (_speech.isListening) {
      await _speech.stop();
    }
  }

  void dispose() {
    if (_speech.isListening) {
      _speech.stop();
    }
  }
}
'''
        (base_path / 'lib' / 'assistant' / 'voice_input_controller.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_assistant_view(self, base_path):
        """Genera lib/assistant/assistant_view.dart (genérico)."""
        content = '''import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'business_command.dart';
import 'command_parser.dart';
import 'command_router.dart';
import 'command_validator.dart';
import 'voice_input_controller.dart';

class AssistantHistoryEntry {
  final String text;
  final bool isError;
  const AssistantHistoryEntry(this.text, {this.isError = false});
}

/// Punto de entrada global del asistente consciente del esquema. Acepta
/// texto escrito (siempre disponible) y, en plataformas nativas
/// compatibles, entrada hablada que se transcribe a texto y se procesa por
/// exactamente el mismo pipeline de interpretación — la voz nunca se salta
/// la validación.
class AssistantView extends StatefulWidget {
  /// Only meant for tests: injects a CommandRouter (e.g. backed by fake
  /// adapters) instead of the real one, so failure paths can be exercised
  /// without a live service/database. Production code should never pass
  /// this.
  final CommandRouter? router;

  const AssistantView({super.key, this.router});

  @override
  State<AssistantView> createState() => _AssistantViewState();
}

class _AssistantViewState extends State<AssistantView> {
  final _controller = TextEditingController();
  final _parser = CommandParser();
  final _validator = CommandValidator();
  late final CommandRouter _router = widget.router ?? CommandRouter();
  final _voice = VoiceInputController();
  final List<AssistantHistoryEntry> _history = [];
  bool _voiceAvailable = false;
  bool _isListening = false;
  bool _isBusy = false;

  @override
  void initState() {
    super.initState();
    _initVoice();
  }

  Future<void> _initVoice() async {
    if (kIsWeb) return;
    final available = await _voice.initialize();
    if (mounted) setState(() => _voiceAvailable = available);
  }

  @override
  void dispose() {
    _voice.dispose();
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isBusy) return;
    setState(() {
      _isBusy = true;
      _history.add(AssistantHistoryEntry(text));
    });
    _controller.clear();

    try {
      final parsed = _parser.parse(text);
      if (!parsed.isSuccess) {
        _appendResult(parsed.error!, isError: true);
        return;
      }

      final validated = _validator.validate(parsed.command!);
      if (!validated.isValid) {
        _appendResult(validated.error!, isError: true);
        return;
      }

      final command = validated.command!;
      if (command.action == CommandAction.delete) {
        final outcome = await _router.execute(command);
        if (!outcome.success || outcome.pendingDelete == null) {
          _appendResult(outcome.message, isError: !outcome.success);
          return;
        }
        if (!mounted) return;
        final confirmed = await _confirmDelete(outcome.pendingDelete!);
        if (confirmed != true) {
          _appendResult('Eliminación cancelada.');
          return;
        }
        final result = await _router.confirmDelete(outcome.pendingDelete!);
        _appendResult(result.message, isError: !result.success);
        return;
      }

      final outcome = await _router.execute(command);
      _appendResult(outcome.message, isError: !outcome.success);
    } catch (_) {
      // Nunca se muestra el detalle/stack trace real: solo un mensaje
      // genérico. El comando pudo fallar por cualquier excepción no
      // anticipada del adaptador/servicio (red, parsing, etc.).
      _appendResult('Ocurrió un error al ejecutar el comando.', isError: true);
    } finally {
      // Red de seguridad: _appendResult ya limpia _isBusy en cada camino de
      // retorno normal, pero esto garantiza que nunca quede atascado en
      // busy si una excepción escapó antes de llegar a _appendResult.
      if (mounted && _isBusy) {
        setState(() => _isBusy = false);
      }
    }
  }

  void _appendResult(String message, {bool isError = false}) {
    if (!mounted) return;
    setState(() {
      _history.add(AssistantHistoryEntry(message, isError: isError));
      _isBusy = false;
    });
  }

  Future<bool?> _confirmDelete(PendingDelete pending) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirmar eliminación'),
        content: Text('Se eliminará ${pending.entity} (id: ${pending.pk}):\\n${pending.preview}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
  }

  Future<void> _toggleListening() async {
    if (!_voiceAvailable) return;
    if (_isListening) {
      await _voice.stopListening();
      if (mounted) setState(() => _isListening = false);
      return;
    }
    setState(() => _isListening = true);
    await _voice.startListening(
      onResult: (text) {
        if (!mounted) return;
        setState(() {
          _controller.text = text;
          _isListening = false;
        });
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Asistente')),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _history.length,
              itemBuilder: (context, index) {
                final entry = _history[index];
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Text(
                    entry.text,
                    style: TextStyle(color: entry.isError ? Colors.red : null),
                  ),
                );
              },
            ),
          ),
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: const InputDecoration(
                      hintText: 'Escribe un comando, por ejemplo: Muéstrame los productos',
                    ),
                    onSubmitted: (_) => _submit(),
                  ),
                ),
                if (_voiceAvailable)
                  IconButton(
                    icon: Icon(_isListening ? Icons.mic : Icons.mic_none),
                    onPressed: _toggleListening,
                  ),
                IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: _isBusy ? null : _submit,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
'''
        (base_path / 'lib' / 'assistant' / 'assistant_view.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _assistant_sample_value(self, dart_type, seed):
        if dart_type == 'int':
            return str(10 + seed)
        if dart_type == 'double':
            return f"{5 + seed},5"
        if dart_type == 'bool':
            return 'true'
        return f"Valor{seed}"

    def _assistant_dart_typed_literal(self, dart_type, raw_value):
        """Mirrors CommandValidator._coerce() to build the DART LITERAL a
        generated test should expect once a raw value is coerced. Used only
        to build test assertions, never emitted as runtime generator output."""
        value = raw_value.strip()
        if dart_type == 'int':
            return str(int(value))
        if dart_type == 'double':
            return repr(float(value.replace(',', '.')))
        if dart_type == 'bool':
            truthy = {'true', 'si', 'sí', 'activo', 'verdadero'}
            return 'true' if value.lower() in truthy else 'false'
        return self._assistant_dart_string_literal(value)

    def _assistant_render_dart_map(self, entries):
        parts = [
            f"{self._assistant_dart_string_literal(k)}: {self._assistant_dart_string_literal(v)}"
            for k, v in entries
        ]
        return "{" + ", ".join(parts) + "}"

    def _assistant_required_create_data(self, meta, name_value='Ejemplo Uno'):
        entries = []
        seed = 1
        for field in meta['fields']:
            if field['is_primary_key'] and field['is_auto_increment']:
                continue
            if not field['writable'] or not field['required_on_create']:
                continue
            if field['name'] == meta['name_field']:
                entries.append((field['name'], name_value))
            else:
                entries.append((field['name'], self._assistant_sample_value(field['dart_type'], seed)))
            seed += 1
        for rel in meta['relations']:
            if rel['kind'] in ('many_to_one', 'one_to_one') and rel['required_on_create'] and rel['writable']:
                entries.append((rel['name'], str(seed)))
                seed += 1
        return entries

    def _assistant_render_parser_case(self, test_name, input_text, action, entity, data, filters):
        lines = [f"  test({self._assistant_dart_string_literal(test_name)}, () {{"]
        lines.append(
            f"    final result = CommandParser().parse({self._assistant_dart_string_literal(input_text)});"
        )
        lines.append("    expect(result.isSuccess, isTrue, reason: result.error);")
        lines.append(f"    expect(result.command!.action, {action});")
        lines.append(f"    expect(result.command!.entity, {self._assistant_dart_string_literal(entity)});")
        for key, value in data:
            lines.append(
                f"    expect(result.command!.data[{self._assistant_dart_string_literal(key)}], "
                f"{self._assistant_dart_string_literal(value)});"
            )
        for key, value in filters:
            lines.append(
                f"    expect(result.command!.filters[{self._assistant_dart_string_literal(key)}], "
                f"{self._assistant_dart_string_literal(value)});"
            )
        lines.append("  });")
        return "\n".join(lines)

    def _assistant_render_failure_case(self, test_name, input_text):
        return (
            f"  test({self._assistant_dart_string_literal(test_name)}, () {{\n"
            f"    final result = CommandParser().parse({self._assistant_dart_string_literal(input_text)});\n"
            "    expect(result.isSuccess, isFalse);\n"
            "    expect(result.error, isNotNull);\n"
            "  });"
        )

    def _assistant_find_writable_field(self, metas, dart_type):
        """First (entity, field) pair, across ALL entities, with a writable
        non-PK field of the given Dart type on a non-double-PK entity. Only
        used for standalone CREATE-only coercion tests, so a nameField is
        not required (CREATE never needs to filter/identify a row)."""
        for meta in metas:
            if meta['fields'] and meta['fields'][0]['dart_type'] == 'double':
                continue
            for field in meta['fields']:
                if field['dart_type'] == dart_type and field['writable'] and not field['is_primary_key']:
                    return meta, field
        return None, None

    def _assistant_find_required_relation(self, metas):
        """First (entity, relation) pair with a required many-to-one/
        one-to-one relation, across ALL entities. Only used for a
        standalone CREATE-only test, so a nameField is not required."""
        for meta in metas:
            if meta['fields'] and meta['fields'][0]['dart_type'] == 'double':
                continue
            for rel in meta['relations']:
                if rel['kind'] in ('many_to_one', 'one_to_one') and rel['required_on_create'] and rel['writable']:
                    return meta, rel
        return None, None

    def _assistant_find_string_pk_entity(self, metas):
        for meta in metas:
            if meta['fields'] and meta['fields'][0]['dart_type'] == 'String':
                return meta
        return None

    def _assistant_render_type_coercion_create_test(self, meta, field, raw_value, test_name):
        entries = self._assistant_required_create_data(meta)
        entries = [(k, raw_value) if k == field['name'] else (k, v) for k, v in entries]
        template = '''  test('__TEST_NAME__', () async {
    final targetSchema = AppSchema.entities.firstWhere((e) => e.name == __ENTITY__);
    final adapter = _FakeAdapter(targetSchema, []);
    final router = CommandRouter(registry: {__ENTITY__: adapter});
    final validated = CommandValidator().validate(BusinessCommand(
      action: CommandAction.create,
      entity: __ENTITY__,
      data: __DATA__,
      filters: const {},
      rawText: 'test',
    ));
    expect(validated.isValid, isTrue, reason: validated.error);
    expect(validated.command!.data[__FIELD__], __EXPECTED__);
    final outcome = await router.execute(validated.command!);
    expect(outcome.success, isTrue);
    expect(adapter.lastCreatedMap![__JSON_KEY__], __EXPECTED__);
  });'''
        return (
            template
            .replace('__TEST_NAME__', test_name)
            .replace('__ENTITY__', self._assistant_dart_string_literal(meta['name']))
            .replace('__DATA__', self._assistant_render_dart_map(entries))
            .replace('__FIELD__', self._assistant_dart_string_literal(field['name']))
            .replace('__JSON_KEY__', self._assistant_dart_string_literal(field['json_key']))
            .replace('__EXPECTED__', self._assistant_dart_typed_literal(field['dart_type'], raw_value))
        )

    def _assistant_render_relation_create_test(self, meta, rel):
        entries = self._assistant_required_create_data(meta)
        rel_value = next(v for k, v in entries if k == rel['name'])
        template = '''  test('CREATE sends a required relationship id under its normalized JSON key', () async {
    final targetSchema = AppSchema.entities.firstWhere((e) => e.name == __ENTITY__);
    final adapter = _FakeAdapter(targetSchema, []);
    final router = CommandRouter(registry: {__ENTITY__: adapter});
    final validated = CommandValidator().validate(BusinessCommand(
      action: CommandAction.create,
      entity: __ENTITY__,
      data: __DATA__,
      filters: const {},
      rawText: 'test',
    ));
    expect(validated.isValid, isTrue, reason: validated.error);
    final outcome = await router.execute(validated.command!);
    expect(outcome.success, isTrue);
    expect(adapter.lastCreatedMap![__JSON_KEY__], __EXPECTED__);
  });'''
        return (
            template
            .replace('__ENTITY__', self._assistant_dart_string_literal(meta['name']))
            .replace('__DATA__', self._assistant_render_dart_map(entries))
            .replace('__JSON_KEY__', self._assistant_dart_string_literal(rel['json_key']))
            .replace('__EXPECTED__', self._assistant_dart_string_literal(rel_value))
        )

    def _generate_assistant_tests(self, base_path, original_classes):
        """Genera test/assistant/command_parser_test.dart,
        test/assistant/command_validator_test.dart y
        test/assistant/command_router_test.dart, adaptados al esquema UML
        real. Los casos que dependen de una forma que el esquema actual no
        tiene (PK String, relación obligatoria, campo de fecha, campo bool o
        double) solo se incluyen cuando el esquema efectivamente la tiene."""
        metas = [self._assistant_entity_metadata(c) for c in original_classes]
        # El "subject" de las pruebas CRUD principales nunca es una entidad
        # con PK double: TODAS las mutaciones fallan cerrado para esa PK, lo
        # que volvería vacías las pruebas de create/update/delete.
        subject = next(
            (m for m in metas if m['name_field'] and not (m['fields'] and m['fields'][0]['dart_type'] == 'double')),
            None,
        )

        parser_cases = [
            self._assistant_render_failure_case(
                'fails closed on an unrecognized action verb',
                'Teletransporta un widget',
            ),
            self._assistant_render_failure_case(
                'fails closed on an unrecognized entity',
                'Registra un marciano Bob',
            ),
        ]
        validator_cases = []
        router_test_blocks = []
        assistant_view_test_content = None

        if subject is not None:
            entity_name = subject['name']
            entity_lower = entity_name.lower()
            name_field = subject['name_field']
            entity_literal = self._assistant_dart_string_literal(entity_name)
            writable_extra = [
                f for f in subject['fields']
                if f['writable'] and not f['is_primary_key'] and f['name'] != name_field
            ]
            extra_fields = writable_extra[:3]

            # ---------------------------------------------------------
            # command_parser_test.dart
            # ---------------------------------------------------------
            clause_parts = []
            create_data = [(name_field, 'Ejemplo Uno')]
            for i, f in enumerate(extra_fields):
                value = self._assistant_sample_value(f['dart_type'], i + 1)
                clause_parts.append(f"{f['name']} {value}")
                create_data.append((f['name'], value))
            create_text = f"Registra un {entity_lower} Ejemplo Uno"
            if clause_parts:
                create_text += " con " + " y ".join(clause_parts)

            parser_cases.append(self._assistant_render_parser_case(
                'parses the flagship CREATE shape with a multiword name and extra fields',
                create_text, 'CommandAction.create', entity_name, create_data, [],
            ))
            parser_cases.append(self._assistant_render_parser_case(
                'parses a LIST-all READ with no filters, ignoring case/accents/extra whitespace',
                f"  MUÉSTRAME   los {entity_lower}s  ", 'CommandAction.read', entity_name, [], [],
            ))
            parser_cases.append(self._assistant_render_parser_case(
                'parses a single-target READ using the name field',
                f"Busca el {entity_lower} Ejemplo Uno", 'CommandAction.read', entity_name,
                [], [(name_field, 'Ejemplo Uno')],
            ))
            parser_cases.append(self._assistant_render_parser_case(
                'parses DELETE with a target filter (never deletes by itself)',
                f"Elimina el {entity_lower} Ejemplo Uno", 'CommandAction.delete', entity_name,
                [], [(name_field, 'Ejemplo Uno')],
            ))

            if extra_fields:
                update_field = extra_fields[0]
                update_value = self._assistant_sample_value(update_field['dart_type'], 9)
                parser_cases.append(self._assistant_render_parser_case(
                    'parses UPDATE using the entity-first grammar',
                    f"Actualiza el {entity_lower} Ejemplo Uno a {update_field['name']} {update_value}",
                    'CommandAction.update', entity_name,
                    [(update_field['name'], update_value)], [(name_field, 'Ejemplo Uno')],
                ))
                parser_cases.append(self._assistant_render_failure_case(
                    'fails closed when the UPDATE value clause is missing a field name',
                    f"Actualiza el {entity_lower} Ejemplo Uno a {update_value}",
                ))

            parser_cases.append(self._assistant_render_failure_case(
                'fails closed on an unrecognized field inside a CREATE clause',
                f"Registra un {entity_lower} Ejemplo Uno con campoInventado 1",
            ))
            parser_cases.append(self._assistant_render_failure_case(
                'fails closed on ambiguous/incomplete CREATE field clauses',
                f"Registra un {entity_lower} Ejemplo Uno con campoInventado",
            ))

            # ---------------------------------------------------------
            # command_validator_test.dart
            # ---------------------------------------------------------
            full_data_entries = self._assistant_required_create_data(subject)

            validator_cases.append(f"""  test('allows CREATE when every required field is present, auto PK omitted', () {{
    final command = BusinessCommand(
      action: CommandAction.create,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map(full_data_entries)},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isTrue, reason: result.error);
  }});""")

            if full_data_entries:
                missing_map = self._assistant_render_dart_map(full_data_entries[1:])
                validator_cases.append(f"""  test('rejects CREATE missing a required field', () {{
    final command = BusinessCommand(
      action: CommandAction.create,
      entity: {entity_literal},
      data: {missing_map},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isFalse);
  }});""")

            if subject['fields'][0]['is_auto_increment']:
                pk_field_name = subject['fields'][0]['name']
                explicit_pk_entries = full_data_entries + [(pk_field_name, '999')]
                validator_cases.append(f"""  test('rejects an explicit value for the auto-increment primary key on CREATE', () {{
    final command = BusinessCommand(
      action: CommandAction.create,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map(explicit_pk_entries)},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isFalse);
  }});""")

            validator_cases.append(f"""  test('rejects UPDATE with no target filter', () {{
    final command = BusinessCommand(
      action: CommandAction.update,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map([(name_field, 'x')])},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isFalse);
  }});""")

            validator_cases.append(f"""  test('rejects DELETE with no target filter', () {{
    final command = BusinessCommand(
      action: CommandAction.delete,
      entity: {entity_literal},
      data: const {{}},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isFalse);
  }});""")

            relation_required = next(
                (r for r in subject['relations']
                 if r['kind'] in ('many_to_one', 'one_to_one') and r['required_on_create']),
                None,
            )
            if relation_required is not None:
                without_relation = [e for e in full_data_entries if e[0] != relation_required['name']]
                validator_cases.append(f"""  test('rejects CREATE missing a required relationship id', () {{
    final command = BusinessCommand(
      action: CommandAction.create,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map(without_relation)},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isFalse);
  }});""")

            date_field = next((f for f in subject['fields'] if f['dart_type'] == 'DateTime'), None)
            if date_field is not None:
                with_date = full_data_entries + [(date_field['name'], '01/01/2026')]
                validator_cases.append(f"""  test('rejects a Date field write as unsupported in this P0', () {{
    final command = BusinessCommand(
      action: CommandAction.create,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map(with_date)},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isFalse);
  }});""")

            # Regression coverage for the "validate but discard" bug: the
            # coerced, typed value must be what ends up in result.command!.data.
            bool_meta, bool_field = self._assistant_find_writable_field(metas, 'bool')
            if bool_meta is not None:
                bool_entries_base = self._assistant_required_create_data(bool_meta)
                for word, expected in [
                    ('sí', 'true'), ('si', 'true'), ('activo', 'true'), ('verdadero', 'true'),
                    ('no', 'false'), ('inactivo', 'false'), ('falso', 'false'),
                ]:
                    entries = [(k, word) if k == bool_field['name'] else (k, v) for k, v in bool_entries_base]
                    validator_cases.append(f"""  test('coerces bool word \"{word}\" to {expected}', () {{
    final command = BusinessCommand(
      action: CommandAction.create,
      entity: {self._assistant_dart_string_literal(bool_meta['name'])},
      data: {self._assistant_render_dart_map(entries)},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isTrue, reason: result.error);
    expect(result.command!.data[{self._assistant_dart_string_literal(bool_field['name'])}], {expected});
  }});""")

            double_meta, double_field = self._assistant_find_writable_field(metas, 'double')
            if double_meta is not None:
                double_entries_base = self._assistant_required_create_data(double_meta)
                for raw, expected in [('10,5', '10.5'), ('10.5', '10.5')]:
                    entries = [(k, raw) if k == double_field['name'] else (k, v) for k, v in double_entries_base]
                    validator_cases.append(f"""  test('coerces double \"{raw}\" to {expected}', () {{
    final command = BusinessCommand(
      action: CommandAction.create,
      entity: {self._assistant_dart_string_literal(double_meta['name'])},
      data: {self._assistant_render_dart_map(entries)},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isTrue, reason: result.error);
    expect(result.command!.data[{self._assistant_dart_string_literal(double_field['name'])}], {expected});
  }});""")

            double_pk_entity = next((m for m in metas if m['fields'] and m['fields'][0]['dart_type'] == 'double'), None)
            if double_pk_entity is not None:
                dpk_entity_literal = self._assistant_dart_string_literal(double_pk_entity['name'])
                dpk_data = self._assistant_required_create_data(double_pk_entity) if double_pk_entity['name_field'] else []
                dpk_name_field = double_pk_entity['name_field']
                dpk_filters = (
                    self._assistant_render_dart_map([(dpk_name_field, 'Ejemplo Uno')])
                    if dpk_name_field else '{}'
                )
                validator_cases.append(f"""  test('double PK: CREATE is rejected', () {{
    final command = BusinessCommand(
      action: CommandAction.create,
      entity: {dpk_entity_literal},
      data: {self._assistant_render_dart_map(dpk_data)},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isFalse);
  }});""")
                validator_cases.append(f"""  test('double PK: UPDATE is rejected', () {{
    final command = BusinessCommand(
      action: CommandAction.update,
      entity: {dpk_entity_literal},
      data: {self._assistant_render_dart_map([(dpk_name_field, 'x')]) if dpk_name_field else 'const {}'},
      filters: {dpk_filters},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isFalse);
  }});""")
                validator_cases.append(f"""  test('double PK: DELETE is rejected', () {{
    final command = BusinessCommand(
      action: CommandAction.delete,
      entity: {dpk_entity_literal},
      data: const {{}},
      filters: {dpk_filters},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isFalse);
  }});""")

            string_pk_entity = self._assistant_find_string_pk_entity(metas)
            if string_pk_entity is not None:
                sp_entries = self._assistant_required_create_data(string_pk_entity)
                pk_field = string_pk_entity['fields'][0]
                sp_without_pk = [e for e in sp_entries if e[0] != pk_field['name']]
                sp_entity_literal = self._assistant_dart_string_literal(string_pk_entity['name'])
                validator_cases.append(f"""  test('requires a String primary key on CREATE', () {{
    final command = BusinessCommand(
      action: CommandAction.create,
      entity: {sp_entity_literal},
      data: {self._assistant_render_dart_map(sp_without_pk)},
      filters: const {{}},
      rawText: 'test',
    );
    final result = CommandValidator().validate(command);
    expect(result.isValid, isFalse);
  }});""")

            # ---------------------------------------------------------
            # command_router_test.dart
            # ---------------------------------------------------------
            pk_dart_type = subject['fields'][0]['dart_type']
            if pk_dart_type == 'int':
                pk_seed_1, pk_seed_2, pk_string_1 = '1', '2', "'1'"
            else:
                pk_seed_1, pk_seed_2, pk_string_1 = "'seed-1'", "'seed-2'", "'seed-1'"

            router_preamble = f"""  final schema = AppSchema.entities.firstWhere((e) => e.name == {entity_literal});
  final pkJsonKey = schema.pkField.jsonKey;
  final nameJsonKey = schema.fieldByName({self._assistant_dart_string_literal(name_field)})!.jsonKey;
"""

            router_test_blocks.append(f"""  test('CREATE validates and sends values under normalized backend JSON keys, PK omitted', () async {{
    final adapter = _FakeAdapter(schema, []);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final validated = CommandValidator().validate(BusinessCommand(
      action: CommandAction.create,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map(create_data)},
      filters: const {{}},
      rawText: 'test',
    ));
    expect(validated.isValid, isTrue, reason: validated.error);
    final outcome = await router.execute(validated.command!);
    expect(outcome.success, isTrue);
    expect(adapter.lastCreatedMap, isNotNull);
    expect(adapter.lastCreatedMap![nameJsonKey], 'Ejemplo Uno');
    expect(adapter.lastCreatedMap!.containsKey(pkJsonKey), isFalse);
  }});""")

            if extra_fields:
                update_field = extra_fields[0]
                update_raw = self._assistant_sample_value(update_field['dart_type'], 50)
                update_expected = self._assistant_dart_typed_literal(update_field['dart_type'], update_raw)
                unchanged_field = extra_fields[1] if len(extra_fields) > 1 else None
                seed_literal_by_type = {'int': '42', 'double': '3.5', 'bool': 'false'}
                unchanged_seed_entry = ''
                unchanged_assertion = ''
                if unchanged_field is not None:
                    unchanged_seed_literal = seed_literal_by_type.get(unchanged_field['dart_type'], "'Sin cambios'")
                    unchanged_seed_entry = (
                        f", {self._assistant_dart_string_literal(unchanged_field['json_key'])}: {unchanged_seed_literal}"
                    )
                    unchanged_assertion = (
                        f"    expect(adapter.lastUpdatedMap![{self._assistant_dart_string_literal(unchanged_field['json_key'])}], "
                        f"{unchanged_seed_literal});"
                    )

                router_test_blocks.append(f"""  test('UPDATE overlays only the changed field, preserves other fields, and targets the stable PK under the normalized key', () async {{
    final adapter = _FakeAdapter(schema, [
      {{pkJsonKey: {pk_seed_1}, nameJsonKey: 'Ejemplo Uno'{unchanged_seed_entry}}},
    ]);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final validated = CommandValidator().validate(BusinessCommand(
      action: CommandAction.update,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map([(update_field['name'], update_raw)])},
      filters: {self._assistant_render_dart_map([(name_field, 'Ejemplo Uno')])},
      rawText: 'test',
    ));
    expect(validated.isValid, isTrue, reason: validated.error);
    final outcome = await router.execute(validated.command!);
    expect(outcome.success, isTrue);
    expect(adapter.updateCalls, 1);
    expect(adapter.lastUpdatedId, {pk_string_1});
    expect(adapter.lastUpdatedMap![{self._assistant_dart_string_literal(update_field['json_key'])}], {update_expected});
    expect(adapter.lastUpdatedMap![nameJsonKey], 'Ejemplo Uno');
{unchanged_assertion}
  }});""")

                router_test_blocks.append(f"""  test('UPDATE with zero matches does not call update', () async {{
    final adapter = _FakeAdapter(schema, []);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final outcome = await router.execute(BusinessCommand(
      action: CommandAction.update,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map([(update_field['name'], update_raw)])},
      filters: {self._assistant_render_dart_map([(name_field, 'Nadie')])},
      rawText: 'test',
    ));
    expect(outcome.success, isFalse);
    expect(adapter.updateCalls, 0);
  }});""")

                router_test_blocks.append(f"""  test('UPDATE with more than one match is ambiguous and never calls update', () async {{
    final adapter = _FakeAdapter(schema, [
      {{pkJsonKey: {pk_seed_1}, nameJsonKey: 'Ejemplo Uno'}},
      {{pkJsonKey: {pk_seed_2}, nameJsonKey: 'Ejemplo Uno'}},
    ]);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final outcome = await router.execute(BusinessCommand(
      action: CommandAction.update,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map([(update_field['name'], update_raw)])},
      filters: {self._assistant_render_dart_map([(name_field, 'Ejemplo Uno')])},
      rawText: 'test',
    ));
    expect(outcome.success, isFalse);
    expect(adapter.updateCalls, 0);
  }});""")

            router_test_blocks.append(f"""  test('DELETE with zero matches does not delete', () async {{
    final adapter = _FakeAdapter(schema, []);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final outcome = await router.execute(BusinessCommand(
      action: CommandAction.delete,
      entity: {entity_literal},
      data: const {{}},
      filters: {self._assistant_render_dart_map([(name_field, 'Nadie')])},
      rawText: 'test',
    ));
    expect(outcome.success, isFalse);
    expect(outcome.pendingDelete, isNull);
    expect(adapter.deleteCalls, 0);
  }});""")

            router_test_blocks.append(f"""  test('DELETE with more than one match is ambiguous and never deletes', () async {{
    final adapter = _FakeAdapter(schema, [
      {{pkJsonKey: {pk_seed_1}, nameJsonKey: 'Ejemplo Uno'}},
      {{pkJsonKey: {pk_seed_2}, nameJsonKey: 'Ejemplo Uno'}},
    ]);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final outcome = await router.execute(BusinessCommand(
      action: CommandAction.delete,
      entity: {entity_literal},
      data: const {{}},
      filters: {self._assistant_render_dart_map([(name_field, 'Ejemplo Uno')])},
      rawText: 'test',
    ));
    expect(outcome.success, isFalse);
    expect(outcome.pendingDelete, isNull);
    expect(adapter.deleteCalls, 0);
  }});""")

            router_test_blocks.append(f"""  test('DELETE resolves exactly one match to a PendingDelete with the stable PK; confirmDelete deletes that exact PK without re-matching', () async {{
    final adapter = _FakeAdapter(schema, [
      {{pkJsonKey: {pk_seed_1}, nameJsonKey: 'Ejemplo Uno'}},
    ]);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final outcome = await router.execute(BusinessCommand(
      action: CommandAction.delete,
      entity: {entity_literal},
      data: const {{}},
      filters: {self._assistant_render_dart_map([(name_field, 'Ejemplo Uno')])},
      rawText: 'test',
    ));
    expect(outcome.success, isTrue);
    expect(outcome.pendingDelete, isNotNull);
    expect(outcome.pendingDelete!.pk, {pk_string_1});
    expect(adapter.deleteCalls, 0);

    // Mutar los datos subyacentes DESPUÉS de resolver: confirmDelete debe
    // borrar el PK ya resuelto, sin volver a ejecutar el emparejamiento.
    adapter.rows.clear();
    final confirmOutcome = await router.confirmDelete(outcome.pendingDelete!);
    expect(confirmOutcome.success, isTrue);
    expect(adapter.deleteCalls, 1);
    expect(adapter.lastDeletedId, {pk_string_1});
  }});""")

            bool_router_meta, bool_router_field = self._assistant_find_writable_field(metas, 'bool')
            if bool_router_meta is not None:
                router_test_blocks.append(self._assistant_render_type_coercion_create_test(
                    bool_router_meta, bool_router_field, 'sí',
                    'CREATE sends a coerced bool value (from the word "sí") to the adapter as an actual bool',
                ))

            double_router_meta, double_router_field = self._assistant_find_writable_field(metas, 'double')
            if double_router_meta is not None:
                router_test_blocks.append(self._assistant_render_type_coercion_create_test(
                    double_router_meta, double_router_field, '10,5',
                    'CREATE sends a comma-decimal value ("10,5") to the adapter as an actual double',
                ))

            relation_meta, relation_rel = self._assistant_find_required_relation(metas)
            if relation_meta is not None:
                router_test_blocks.append(self._assistant_render_relation_create_test(relation_meta, relation_rel))

            string_pk_router_entity = self._assistant_find_string_pk_entity(metas)
            if string_pk_router_entity is not None:
                sp_entries = self._assistant_required_create_data(string_pk_router_entity)
                sp_pk_field = string_pk_router_entity['fields'][0]
                sp_pk_value = next(v for k, v in sp_entries if k == sp_pk_field['name'])
                sp_entity_literal = self._assistant_dart_string_literal(string_pk_router_entity['name'])
                router_test_blocks.append(f"""  test('String primary key: CREATE requires the explicit PK value and sends it under its JSON key', () async {{
    final spSchema = AppSchema.entities.firstWhere((e) => e.name == {sp_entity_literal});
    final adapter = _FakeAdapter(spSchema, []);
    final router = CommandRouter(registry: {{{sp_entity_literal}: adapter}});
    final validated = CommandValidator().validate(BusinessCommand(
      action: CommandAction.create,
      entity: {sp_entity_literal},
      data: {self._assistant_render_dart_map(sp_entries)},
      filters: const {{}},
      rawText: 'test',
    ));
    expect(validated.isValid, isTrue, reason: validated.error);
    final outcome = await router.execute(validated.command!);
    expect(outcome.success, isTrue);
    expect(adapter.lastCreatedMap![{self._assistant_dart_string_literal(sp_pk_field['json_key'])}], {self._assistant_dart_string_literal(sp_pk_value)});
  }});""")

                if string_pk_router_entity['name_field']:
                    sp_name_field = string_pk_router_entity['name_field']
                    sp_name_json_key = self._to_backend_json_key(sp_name_field)
                    router_test_blocks.append(f"""  test('String primary key: UPDATE targets the exact String PK', () async {{
    final spSchema = AppSchema.entities.firstWhere((e) => e.name == {sp_entity_literal});
    final adapter = _FakeAdapter(spSchema, [
      {{{self._assistant_dart_string_literal(sp_pk_field['json_key'])}: {self._assistant_dart_string_literal(sp_pk_value)}, {self._assistant_dart_string_literal(sp_name_json_key)}: 'Etiqueta Uno'}},
    ]);
    final router = CommandRouter(registry: {{{sp_entity_literal}: adapter}});
    final outcome = await router.execute(BusinessCommand(
      action: CommandAction.update,
      entity: {sp_entity_literal},
      data: {self._assistant_render_dart_map([(sp_name_field, 'Etiqueta Dos')])},
      filters: {self._assistant_render_dart_map([(sp_name_field, 'Etiqueta Uno')])},
      rawText: 'test',
    ));
    expect(outcome.success, isTrue);
    expect(adapter.lastUpdatedId, {self._assistant_dart_string_literal(sp_pk_value)});
  }});""")

            # ---------------------------------------------------------
            # assistant_view_test.dart — proves an adapter/service
            # exception during _submit() never leaves the assistant
            # permanently busy, and that typed input keeps working when
            # voice never becomes available (no plugin registered in the
            # widget-test sandbox).
            # ---------------------------------------------------------
            widget_template = '''import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/assistant/app_schema.dart';
import 'package:generated_crud_app/assistant/assistant_view.dart';
import 'package:generated_crud_app/assistant/command_router.dart';
import 'package:generated_crud_app/assistant/entity_service_adapter.dart';

class _ThrowingAdapter extends EntityServiceAdapter {
  _ThrowingAdapter(super.schema);

  @override
  Future<List<Map<String, dynamic>>> list() async {
    throw Exception('simulated adapter failure');
  }

  @override
  Future<Map<String, dynamic>> create(Map<String, dynamic> jsonData) async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> updateFromMap(String id, Map<String, dynamic> mergedJsonData) async =>
      throw UnimplementedError();

  @override
  Future<void> deleteById(String id) async => throw UnimplementedError();
}

void main() {
  testWidgets(
    'an adapter exception during a command does not leave the assistant permanently busy',
    (tester) async {
      final schema = AppSchema.entities.firstWhere((e) => e.name == __ENTITY__);
      final router = CommandRouter(registry: {__ENTITY__: _ThrowingAdapter(schema)});

      await tester.pumpWidget(MaterialApp(home: AssistantView(router: router)));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), __LIST_COMMAND__);
      await tester.tap(find.byIcon(Icons.send));
      await tester.pumpAndSettle();

      // A concise, generic error reached the UI — never a raw exception.
      expect(find.textContaining('error'), findsWidgets);

      // The send control is usable again: a second submission must still
      // run (and fail the same way) instead of being silently ignored
      // because _isBusy stayed stuck true.
      await tester.enterText(find.byType(TextField), __LIST_COMMAND__);
      await tester.tap(find.byIcon(Icons.send));
      await tester.pumpAndSettle();
      expect(find.textContaining('error'), findsNWidgets(2));
    },
  );

  testWidgets('typed input keeps working when voice never becomes available', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: AssistantView()));
    await tester.pumpAndSettle();

    expect(find.byType(TextField), findsOneWidget);
    expect(find.byIcon(Icons.mic), findsNothing);
    expect(find.byIcon(Icons.mic_none), findsNothing);
    expect(find.byIcon(Icons.send), findsOneWidget);
  });
}
'''
            assistant_view_test_content = (
                widget_template
                .replace('__ENTITY__', entity_literal)
                .replace('__LIST_COMMAND__', self._assistant_dart_string_literal(f"Muestra los {entity_lower}s"))
            )

        parser_test_content = (
            "import 'package:flutter_test/flutter_test.dart';\n"
            "import 'package:generated_crud_app/assistant/business_command.dart';\n"
            "import 'package:generated_crud_app/assistant/command_parser.dart';\n"
            "\n"
            "void main() {\n"
            + "\n\n".join(parser_cases) +
            "\n}\n"
        )
        (base_path / 'test' / 'assistant' / 'command_parser_test.dart').write_text(
            self._sanitize(parser_test_content), encoding="utf-8", newline="\n"
        )

        validator_test_content = (
            "import 'package:flutter_test/flutter_test.dart';\n"
            "import 'package:generated_crud_app/assistant/business_command.dart';\n"
            "import 'package:generated_crud_app/assistant/command_validator.dart';\n"
            "\n"
            "void main() {\n"
            + ("\n\n".join(validator_cases) if validator_cases else "  test('no assistant-writable entity in this schema', () {\n    expect(true, isTrue);\n  });")
            + "\n}\n"
        )
        (base_path / 'test' / 'assistant' / 'command_validator_test.dart').write_text(
            self._sanitize(validator_test_content), encoding="utf-8", newline="\n"
        )

        if router_test_blocks:
            router_boilerplate = '''import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/assistant/app_schema.dart';
import 'package:generated_crud_app/assistant/business_command.dart';
import 'package:generated_crud_app/assistant/command_router.dart';
import 'package:generated_crud_app/assistant/command_validator.dart';
import 'package:generated_crud_app/assistant/entity_service_adapter.dart';

class _FakeAdapter extends EntityServiceAdapter {
  _FakeAdapter(super.schema, this.rows);
  final List<Map<String, dynamic>> rows;
  int deleteCalls = 0;
  int updateCalls = 0;
  String? lastDeletedId;
  String? lastUpdatedId;
  Map<String, dynamic>? lastUpdatedMap;
  Map<String, dynamic>? lastCreatedMap;

  @override
  Future<List<Map<String, dynamic>>> list() async => rows;

  @override
  Future<Map<String, dynamic>> create(Map<String, dynamic> jsonData) async {
    lastCreatedMap = jsonData;
    rows.add(jsonData);
    return jsonData;
  }

  @override
  Future<Map<String, dynamic>> updateFromMap(String id, Map<String, dynamic> mergedJsonData) async {
    updateCalls++;
    lastUpdatedId = id;
    lastUpdatedMap = mergedJsonData;
    return mergedJsonData;
  }

  @override
  Future<void> deleteById(String id) async {
    deleteCalls++;
    lastDeletedId = id;
  }
}

void main() {
__PREAMBLE__
__TESTS__
}
'''
            router_test_content = (
                router_boilerplate
                .replace('__PREAMBLE__', router_preamble)
                .replace('__TESTS__', "\n\n".join(router_test_blocks))
            )
            (base_path / 'test' / 'assistant' / 'command_router_test.dart').write_text(
                self._sanitize(router_test_content), encoding="utf-8", newline="\n"
            )

        if assistant_view_test_content is not None:
            (base_path / 'test' / 'assistant' / 'assistant_view_test.dart').write_text(
                self._sanitize(assistant_view_test_content), encoding="utf-8", newline="\n"
            )

    # ========================================
    # === GENERADORES PARA ENTIDADES INTERMEDIAS ===
    # ========================================
    
    def _generate_intermediate_model(self, base_path, intermediate):
        """Genera el modelo para una entidad intermedia (relación ManyToMany)"""
        name = intermediate['name']
        first_entity = intermediate['first_entity']
        second_entity = intermediate['second_entity']
        snake_name = self._to_snake_case(name)
        first_snake = self._to_snake_case(first_entity)
        second_snake = self._to_snake_case(second_entity)
        
        # El backend devuelve los campos con el nombre de la entidad en minúsculas
        # Por ejemplo: "perro" y "persona", no "perroid" y "personaid"
        first_json_key = first_snake  # ya está en snake_case/lowercase
        second_json_key = second_snake
        
        content = f"""import '{first_snake}.dart';
import '{second_snake}.dart';

class {name} {{
  final int id;
  final int {first_snake}id;
  final {first_entity}? {first_snake};
  final int {second_snake}id;
  final {second_entity}? {second_snake};

  {name}({{
    required this.id,
    required this.{first_snake}id,
    this.{first_snake},
    required this.{second_snake}id,
    this.{second_snake},
  }});

  factory {name}.fromJson(Map<String, dynamic> json) {{
    return {name}(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id']?.toString() ?? '0') ?? 0,
      {first_snake}id: json['{first_json_key}'] != null && json['{first_json_key}'] is Map
          ? (json['{first_json_key}']['id'] is int ? json['{first_json_key}']['id'] : int.tryParse(json['{first_json_key}']['id']?.toString() ?? '0') ?? 0)
          : 0,
      {first_snake}: json['{first_json_key}'] != null && json['{first_json_key}'] is Map 
          ? {first_entity}.fromJson(json['{first_json_key}']) 
          : null,
      {second_snake}id: json['{second_json_key}'] != null && json['{second_json_key}'] is Map
          ? (json['{second_json_key}']['id'] is int ? json['{second_json_key}']['id'] : int.tryParse(json['{second_json_key}']['id']?.toString() ?? '0') ?? 0)
          : 0,
      {second_snake}: json['{second_json_key}'] != null && json['{second_json_key}'] is Map
          ? {second_entity}.fromJson(json['{second_json_key}']) 
          : null,
    );
  }}

  Map<String, dynamic> toJson() {{
    return {{
      '{first_snake}id': {first_snake}id,
      '{second_snake}id': {second_snake}id,
    }};
  }}

  @override
  String toString() {{
    final firstStr = {first_snake}?.toString() ?? 'ID: ${{{first_snake}id}}';
    final secondStr = {second_snake}?.toString() ?? 'ID: ${{{second_snake}id}}';
    return '({first_entity}: $firstStr) ↔ ({second_entity}: $secondStr)';
  }}
}}
"""
        file_path = base_path / 'lib' / 'models' / f'{snake_name}.dart'
        file_path.write_text(self._sanitize(content), encoding="utf-8", newline="\n")
    
    def _generate_intermediate_service(self, base_path, intermediate):
        name = intermediate['name']
        snake_name = self._to_snake_case(name)
        backend_url_name = self._to_backend_json_key(name)
        
        content = f"""import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import '../models/{snake_name}.dart';
import '../config.dart';
import '../database/database_helper.dart';

class {name}Service {{
  static const String baseUrl = ApiConfig.baseUrl;
  
  Future<List<{name}>> getAll() async {{
    List<{name}> remoteData = [];
    bool networkSuccess = false;
    try {{
      final response = await http.get(
        Uri.parse('$baseUrl/{backend_url_name}/'),
        headers: {{'Content-Type': 'application/json'}},
      );

      if (response.statusCode == 200 || response.statusCode == 201) {{
        final List<dynamic> jsonList = json.decode(utf8.decode(response.bodyBytes));
        remoteData = jsonList
            .whereType<Map<String, dynamic>>()
            .map((item) => {name}.fromJson(item))
            .toList();
        networkSuccess = true;
      }} else {{
        throw Exception('Error al cargar {name}s: ${{response.statusCode}}');
      }}
    }} catch (e) {{
      if (e.toString().contains('Error al cargar')) rethrow;
      if (kIsWeb) rethrow;
    }}

    if (kIsWeb) return remoteData;

    if (networkSuccess) {{
      for (var item in remoteData) {{
        await DatabaseHelper.instance.upsert('{snake_name}', item.toJson(), 'id');
      }}
    }}

    final localData = await DatabaseHelper.instance.getAll('{snake_name}');
    return localData.map((j) => {name}.fromJson(j)).toList();
  }}

  Future<{name}?> getById(String id) async {{
    try {{
      final response = await http.get(
        Uri.parse('$baseUrl/{backend_url_name}/$id/'),
        headers: {{'Content-Type': 'application/json'}},
      );

      if (response.statusCode == 200 || response.statusCode == 201) {{
        final data = json.decode(utf8.decode(response.bodyBytes));
        if (!kIsWeb) {{
          await DatabaseHelper.instance.upsert('{snake_name}', data, 'id');
        }}
        return {name}.fromJson(data);
      }} else {{
        if (!kIsWeb && response.statusCode == 404) {{
          final localData = await DatabaseHelper.instance.getById('{snake_name}', 'id', id);
          if (localData != null) return {name}.fromJson(localData);
        }}
        throw Exception('Error al obtener {name}: ${{response.statusCode}}');
      }}
    }} catch (e) {{
      if (e.toString().contains('Error al obtener')) rethrow;
      if (!kIsWeb) {{
        final localData = await DatabaseHelper.instance.getById('{snake_name}', 'id', id);
        if (localData != null) return {name}.fromJson(localData);
      }}
      throw Exception('Error de conexión: $e');
    }}
  }}

  Future<{name}> create({name} item) async {{
    try {{
      final response = await http.post(
        Uri.parse('$baseUrl/{backend_url_name}/'),
        headers: {{'Content-Type': 'application/json'}},
        body: json.encode(item.toJson()),
      );

      if (response.statusCode == 201 || response.statusCode == 200) {{
        final data = json.decode(utf8.decode(response.bodyBytes));
        if (!kIsWeb) {{
          await DatabaseHelper.instance.upsert('{snake_name}', data, 'id');
        }}
        return {name}.fromJson(data);
      }} else {{
        throw Exception('Error al crear {name}: ${{response.statusCode}} - ${{response.body}}');
      }}
    }} catch (e) {{
      if (e.toString().contains('Error al crear')) rethrow;
      if (kIsWeb) rethrow;

      final map = item.toJson();
      final insertedMap = await DatabaseHelper.instance.insertLocal('{snake_name}', map, 'id', true);
      return {name}.fromJson(insertedMap);
    }}
  }}

  Future<{name}> update(String id, {name} item) async {{
    try {{
      final response = await http.put(
        Uri.parse('$baseUrl/{backend_url_name}/$id/'),
        headers: {{'Content-Type': 'application/json'}},
        body: json.encode(item.toJson()),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {{
        final data = json.decode(utf8.decode(response.bodyBytes));
        if (!kIsWeb) {{
          await DatabaseHelper.instance.upsert('{snake_name}', data, 'id');
        }}
        return {name}.fromJson(data);
      }} else {{
        if (!kIsWeb && response.statusCode == 404) {{
          final updatedMap = await DatabaseHelper.instance.updateLocal('{snake_name}', item.toJson(), 'id', id);
          return {name}.fromJson(updatedMap);
        }}
        throw Exception('Error al actualizar {name}: ${{response.statusCode}} - ${{response.body}}');
      }}
    }} catch (e) {{
      if (e.toString().contains('Error al actualizar')) rethrow;
      if (kIsWeb) rethrow;

      final updatedMap = await DatabaseHelper.instance.updateLocal('{snake_name}', item.toJson(), 'id', id);
      return {name}.fromJson(updatedMap);
    }}
  }}

  Future<void> delete(String id) async {{
    try {{
      final response = await http.delete(Uri.parse('$baseUrl/{backend_url_name}/$id/'));

      if (response.statusCode == 204 || response.statusCode == 200) {{
        if (!kIsWeb) {{
          await DatabaseHelper.instance.deleteLocal('{snake_name}', 'id', id);
        }}
        return;
      }} else {{
        if (!kIsWeb && response.statusCode == 404) {{
          await DatabaseHelper.instance.deleteLocal('{snake_name}', 'id', id);
          return;
        }}
        throw Exception('Error al eliminar {name}: ${{response.statusCode}} - ${{response.body}}');
      }}
    }} catch (e) {{
      if (e.toString().contains('Error al eliminar')) rethrow;
      if (kIsWeb) rethrow;

      await DatabaseHelper.instance.deleteLocal('{snake_name}', 'id', id);
    }}
  }}
}}
"""
        (base_path / 'lib' / 'services' / f'{snake_name}_service.dart').write_text(self._sanitize(content), encoding="utf-8", newline="\n")

    def _generate_intermediate_list_view(self, base_path, intermediate):
        """Genera la vista de listado para una entidad intermedia"""
        name = intermediate['name']
        first_entity = intermediate['first_entity']
        second_entity = intermediate['second_entity']
        snake_name = self._to_snake_case(name)
        first_snake = self._to_snake_case(first_entity)
        second_snake = self._to_snake_case(second_entity)
        
        content = f"""import 'package:flutter/material.dart';
import '../models/{snake_name}.dart';
import '../services/{snake_name}_service.dart';
import '{snake_name}_form_view.dart';
import '{snake_name}_detail_view.dart';

class {name}ListView extends StatefulWidget {{
  const {name}ListView({{super.key}});

  @override
  State<{name}ListView> createState() => _{name}ListViewState();
}}

class _{name}ListViewState extends State<{name}ListView> {{
  final {name}Service _service = {name}Service();
  List<{name}> _items = [];
  bool _isLoading = true;

  @override
  void initState() {{
    super.initState();
    _loadItems();
  }}

  Future<void> _loadItems() async {{
    setState(() => _isLoading = true);
    try {{
      final items = await _service.getAll();
      setState(() {{
        _items = items;
        _isLoading = false;
      }});
    }} catch (e) {{
      setState(() => _isLoading = false);
      if (mounted) {{
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error al cargar: $e')),
        );
      }}
    }}
  }}

  Future<void> _deleteItem(String id) async {{
    try {{
      await _service.delete(id);
      _loadItems();
      if (mounted) {{
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Eliminado exitosamente')),
        );
      }}
    }} catch (e) {{
      if (mounted) {{
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error al eliminar: $e')),
        );
      }}
    }}
  }}

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: const Text('{name} (Relación)'),
        backgroundColor: Colors.purple,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? const Center(
                  child: Text('No hay relaciones. ¡Crea una nueva!'),
                )
              : ListView.builder(
                  itemCount: _items.length,
                  itemBuilder: (context, index) {{
                    final item = _items[index];
                    final firstDisplay = item.{first_snake}?.toString() ?? 'ID: ${{item.{first_snake}id}}';
                    final secondDisplay = item.{second_snake}?.toString() ?? 'ID: ${{item.{second_snake}id}}';
                    
                    return Card(
                      margin: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      child: ListTile(
                        leading: const Icon(Icons.link, color: Colors.purple),
                        title: Text('{first_entity} ↔ {second_entity}'),
                        subtitle: Text('$firstDisplay → $secondDisplay'),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.edit),
                              onPressed: () async {{
                                await Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) => {name}FormView(
                                      item: item,
                                    ),
                                  ),
                                );
                                _loadItems();
                              }},
                            ),
                            IconButton(
                              icon: const Icon(Icons.delete),
                              color: Colors.red,
                              onPressed: () {{
                                showDialog(
                                  context: context,
                                  builder: (context) => AlertDialog(
                                    title: const Text('Confirmar'),
                                    content: const Text(
                                      '¿Deseas eliminar esta relación?',
                                    ),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.pop(context),
                                        child: const Text('Cancelar'),
                                      ),
                                      TextButton(
                                        onPressed: () {{
                                          Navigator.pop(context);
                                          _deleteItem(item.id.toString());
                                        }},
                                        child: const Text('Eliminar'),
                                      ),
                                    ],
                                  ),
                                );
                              }},
                            ),
                          ],
                        ),
                        onTap: () {{
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => {name}DetailView(item: item),
                            ),
                          );
                        }},
                      ),
                    );
                  }},
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {{
          await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const {name}FormView(),
            ),
          );
          _loadItems();
        }},
        child: const Icon(Icons.add),
      ),
    );
  }}
}}
"""
        file_path = base_path / 'lib' / 'views' / f'{snake_name}_list_view.dart'
        file_path.write_text(content, encoding="utf-8", newline="\n")
    
    def _generate_intermediate_form_view(self, base_path, intermediate):
        """Genera el formulario para crear/editar una entidad intermedia"""
        name = intermediate['name']
        first_entity = intermediate['first_entity']
        second_entity = intermediate['second_entity']
        snake_name = self._to_snake_case(name)
        first_snake = self._to_snake_case(first_entity)
        second_snake = self._to_snake_case(second_entity)
        
        content = f"""import 'package:flutter/material.dart';
import '../models/{snake_name}.dart';
import '../models/{first_snake}.dart';
import '../models/{second_snake}.dart';
import '../services/{snake_name}_service.dart';
import '../services/{first_snake}_service.dart';
import '../services/{second_snake}_service.dart';

class {name}FormView extends StatefulWidget {{
  final {name}? item;

  const {name}FormView({{super.key, this.item}});

  @override
  State<{name}FormView> createState() => _{name}FormViewState();
}}

class _{name}FormViewState extends State<{name}FormView> {{
  final _formKey = GlobalKey<FormState>();
  final {name}Service _service = {name}Service();
  final {first_entity}Service _{first_snake}Service = {first_entity}Service();
  final {second_entity}Service _{second_snake}Service = {second_entity}Service();
  
  bool _isLoading = false;
  List<{first_entity}> _{first_snake}Options = [];
  List<{second_entity}> _{second_snake}Options = [];
  int? _selected{first_entity}Id;
  int? _selected{second_entity}Id;

  @override
  void initState() {{
    super.initState();
    _loadOptions();
    if (widget.item != null) {{
      _selected{first_entity}Id = widget.item!.{first_snake}id;
      _selected{second_entity}Id = widget.item!.{second_snake}id;
    }}
  }}

  Future<void> _loadOptions() async {{
    try {{
      final {first_snake}List = await _{first_snake}Service.getAll();
      final {second_snake}List = await _{second_snake}Service.getAll();
      setState(() {{
        _{first_snake}Options = {first_snake}List;
        _{second_snake}Options = {second_snake}List;
      }});
    }} catch (e) {{
      if (mounted) {{
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error al cargar opciones: $e')),
        );
      }}
    }}
  }}

  Future<void> _submit() async {{
    if (!_formKey.currentState!.validate()) return;
    if (_selected{first_entity}Id == null || _selected{second_entity}Id == null) {{
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Debes seleccionar ambas entidades')),
      );
      return;
    }}

    setState(() => _isLoading = true);

    try {{
      final item = {name}(
        id: widget.item?.id ?? 0,
        {first_snake}id: _selected{first_entity}Id!,
        {second_snake}id: _selected{second_entity}Id!,
      );

      if (widget.item == null) {{
        await _service.create(item);
      }} else {{
        await _service.update(item.id.toString(), item);
      }}

      if (mounted) {{
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.item == null
                ? 'Relación creada exitosamente'
                : 'Relación actualizada exitosamente'),
          ),
        );
      }}
    }} catch (e) {{
      setState(() => _isLoading = false);
      if (mounted) {{
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }}
    }}
  }}

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.item == null ? 'Crear Relación {name}' : 'Editar Relación {name}'),
        backgroundColor: Colors.purple,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  children: [
                    DropdownButtonFormField<int>(
                      initialValue: _selected{first_entity}Id,
                      decoration: const InputDecoration(
                        labelText: 'Seleccionar {first_entity}',
                        border: OutlineInputBorder(),
                      ),
                      items: _{first_snake}Options.map((item) {{
                        return DropdownMenuItem<int>(
                          value: item.id,
                          child: Text(item.toString()),
                        );
                      }}).toList(),
                      onChanged: (value) {{
                        setState(() => _selected{first_entity}Id = value);
                      }},
                      validator: (value) {{
                        if (value == null) return 'Debes seleccionar una opción';
                        return null;
                      }},
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<int>(
                      initialValue: _selected{second_entity}Id,
                      decoration: const InputDecoration(
                        labelText: 'Seleccionar {second_entity}',
                        border: OutlineInputBorder(),
                      ),
                      items: _{second_snake}Options.map((item) {{
                        return DropdownMenuItem<int>(
                          value: item.id,
                          child: Text(item.toString()),
                        );
                      }}).toList(),
                      onChanged: (value) {{
                        setState(() => _selected{second_entity}Id = value);
                      }},
                      validator: (value) {{
                        if (value == null) return 'Debes seleccionar una opción';
                        return null;
                      }},
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _submit,
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.all(16),
                        ),
                        child: Text(
                          widget.item == null ? 'Crear Relación' : 'Actualizar Relación',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
    );
  }}
}}
"""
        file_path = base_path / 'lib' / 'views' / f'{snake_name}_form_view.dart'
        file_path.write_text(content, encoding="utf-8", newline="\n")
    
    def _generate_intermediate_detail_view(self, base_path, intermediate):
        """Genera la vista de detalle para una entidad intermedia"""
        name = intermediate['name']
        first_entity = intermediate['first_entity']
        second_entity = intermediate['second_entity']
        snake_name = self._to_snake_case(name)
        first_snake = self._to_snake_case(first_entity)
        second_snake = self._to_snake_case(second_entity)
        
        # Obtener los 2 primeros atributos significativos de cada entidad relacionada (sin id)
        first_entity_class = next((c for c in self.classes if c['name'] == first_entity), None)
        second_entity_class = next((c for c in self.classes if c['name'] == second_entity), None)
        
        first_attrs = []
        second_attrs = []
        
        if first_entity_class:
            first_attrs = [attr for attr in first_entity_class.get('attributes', []) if attr['name'].lower() != 'id'][:2]
        if second_entity_class:
            second_attrs = [attr for attr in second_entity_class.get('attributes', []) if attr['name'].lower() != 'id'][:2]
        
        # Generar filas para mostrar los atributos de cada entidad
        first_entity_rows = []
        if first_attrs:
            for attr in first_attrs:
                first_entity_rows.append(f"""                if (item.{first_snake} != null) _buildDetailRow('{first_entity}.{attr['name']}', item.{first_snake}!.{attr['name']}.toString()),
                if (item.{first_snake} != null) const SizedBox(height: 12),""")
        
        second_entity_rows = []
        if second_attrs:
            for attr in second_attrs:
                second_entity_rows.append(f"""                if (item.{second_snake} != null) _buildDetailRow('{second_entity}.{attr['name']}', item.{second_snake}!.{attr['name']}.toString()),
                if (item.{second_snake} != null) const SizedBox(height: 12),""")
        
        content = f"""import 'package:flutter/material.dart';
import '../models/{snake_name}.dart';

class {name}DetailView extends StatelessWidget {{
  final {name} item;

  const {name}DetailView({{super.key, required this.item}});

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: const Text('Detalle de Relación {name}'),
        backgroundColor: Colors.purple,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Relación {first_entity} - {second_entity}',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const Divider(height: 32),
                _buildDetailRow('ID de Relación', item.id.toString()),
                const SizedBox(height: 12),
                _buildDetailRow('ID de {first_entity}', item.{first_snake}id.toString()),
                const SizedBox(height: 12),
{chr(10).join(first_entity_rows) if first_entity_rows else f"                _buildDetailRow('{first_entity}', item.{first_snake}?.toString() ?? 'No disponible'),{chr(10)}                const SizedBox(height: 12),"}
                _buildDetailRow('ID de {second_entity}', item.{second_snake}id.toString()),
                const SizedBox(height: 12),
{chr(10).join(second_entity_rows) if second_entity_rows else f"                _buildDetailRow('{second_entity}', item.{second_snake}?.toString() ?? 'No disponible'),"}
              ],
            ),
          ),
        ),
      ),
    );
  }}

  Widget _buildDetailRow(String label, String value) {{
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 150,
          child: Text(
            '$label:',
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontSize: 16),
          ),
        ),
      ],
    );
  }}
}}
"""
        file_path = base_path / 'lib' / 'views' / f'{snake_name}_detail_view.dart'
        file_path.write_text(content, encoding="utf-8", newline="\n")
    
    # Utilidades
    def _to_snake_case(self, name):
        """Convierte PascalCase a snake_case"""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    
    def _to_backend_json_key(self, name):
        """Convierte nombre de atributo al formato del backend: minúsculas sin separadores"""
        # Eliminar guiones bajos y convertir a minúsculas
        return name.replace('_', '').lower()
    
    def _convert_type(self, uml_type):
        """Convierte tipos UML a tipos Dart"""
        type_map = {
            'string': 'String',
            'String': 'String',
            'int': 'int',
            'Int': 'int',
            'double': 'double',
            'Double': 'double',
            'bool': 'bool',
            'Boolean': 'bool',
            'Date': 'DateTime',
        }
        return type_map.get(uml_type, 'String')
    
    def _generate_copy_with_params(self, attributes):
        """Genera parámetros para copyWith"""
        params = []
        for attr in attributes:
            dart_type = self._convert_type(attr['type'])
            params.append(f"    {dart_type}? {attr['name']}")
        return ',\n'.join(params) + ',' if params else ''
    
    def _generate_copy_with_assignments(self, attributes):
        """Genera asignaciones para copyWith"""
        assignments = []
        for attr in attributes:
            assignments.append(f"      {attr['name']}: {attr['name']} ?? this.{attr['name']}")
        return ',\n'.join(assignments) + ',' if assignments else ''
    
    def _parse_field_value(self, attr):
        """Genera el código para parsear el valor del campo"""
        dart_type = self._convert_type(attr['type'])
        field_name = attr['name']
        
        if dart_type == 'int':
            return f"int.tryParse(_{field_name}Controller.text) ?? 0"
        elif dart_type == 'double':
            return f"double.tryParse(_{field_name}Controller.text) ?? 0.0"
        elif dart_type == 'bool':
            return f"_{field_name}Controller.text.toLowerCase() == 'true'"
        else:
            return f"_{field_name}Controller.text"


    def _sanitize(self, text: str) -> str:
        """Normaliza texto y elimina caracteres problemáticos."""
        text = unicodedata.normalize("NFC", text)
        # Reemplazar signos que a veces fallan en YAML
        text = (
            text.replace("¿", "?")
                .replace("¡", "!")
                .replace("“", '"')
                .replace("”", '"')
                .replace("‘", "'")
                .replace("’", "'")
        )
        return text

    def _generate_dispose_controllers(self, attributes, is_numeric_pk=False, parent_class=None):
        """Genera dispose para los controladores que realmente existen"""
        disposes = []
        for i, attr in enumerate(attributes):
            # Si es la PK (primer atributo) y es numérica, NO hay controlador
            if i == 0 and is_numeric_pk:
                continue
            disposes.append(f"    _{attr['name']}Controller.dispose();")
        return '\n'.join(disposes)
