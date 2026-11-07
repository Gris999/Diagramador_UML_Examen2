import json
import os
from pathlib import Path
import unicodedata

from . import app_icon


class FlutterCRUDGenerator:
    def __init__(self, uml_json):
        self.uml_json = uml_json
        self.classes, self.relationships = self._expand_recursive_many_to_many(
            uml_json.get('classes', []), uml_json.get('relationships', [])
        )
        self.parsed_relationships = self._parse_relationships()

    def _expand_recursive_many_to_many(self, classes, relationships):
        """Una N:M de una clase con ella misma (amistades entre personas) se expande como la manda el editor: una clase
        asociativa (Persona_Persona) con dos relaciones 1:N. La entidad intermedia automática de este generador une dos
        clases distintas y con la misma clase en los dos extremos repetiría sus campos."""
        by_id = {c['id']: c for c in classes}
        taken_names = {c['name'] for c in classes}
        expanded_classes = list(classes)
        expanded = []
        for rel in relationships:
            labels = rel.get('labels') or []
            raw_source = labels[0].strip() if len(labels) > 0 and labels[0] else ''
            raw_target = labels[1].strip() if len(labels) > 1 and labels[1] else ''
            class_id = rel.get('sourceId')
            if (rel.get('type', '').lower() == 'association' and class_id == rel.get('targetId') and class_id in by_id
                    and '*' in raw_source and '*' in raw_target):
                name = by_id[class_id]['name']
                junction_name = f"{name}_{name}"
                n = 2
                while junction_name in taken_names:
                    junction_name = f"{name}_{name}_{n}"
                    n += 1
                taken_names.add(junction_name)
                junction_id = f"junction:{class_id}:{class_id}:{rel.get('id')}"
                expanded_classes.append({'id': junction_id, 'name': junction_name,
                                         'attributes': [{'name': 'id', 'type': 'int'}], 'methods': []})
                for role in ('source', 'target'):
                    expanded.append({'id': f"junction-link:{junction_id}:{role}", 'type': 'association',
                                     'sourceId': class_id, 'targetId': junction_id, 'labels': ['1', '0..*']})
                continue
            expanded.append(rel)
        return expanded_classes, expanded

    def _parse_relationships(self):
      """Convierte relaciones UML en vínculos lógicos entre clases - MISMA LÓGICA QUE ProjectGenerator.java"""
      relations_map = {cls['id']: cls['name'] for cls in self.classes}
      parsed = []
      
      # Detectar relaciones ManyToMany para crear entidades intermedias
      many_to_many_relations = []

      # Nombre de cada campo de relación, con las mismas reglas que RelationNaming.java: el de la clase del otro extremo, salvo
      # que ya lo use otro campo de esa clase (una recursiva usa padre/hijos; una repetida, un número: aeropuerto2).
      used_fields = {}

      def unique_field(class_name, base):
          taken = used_fields.setdefault(class_name, set())
          field = base
          n = 2
          while field in taken:
              field = f"{base}{n}"
              n += 1
          taken.add(field)
          return field

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
              
              recursive = src == tgt
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
                  base = self._to_snake_case(intermediate_name)
                  parsed.append({"from": src, "to": intermediate_name, "kind": "one_to_many",
                                 "field": unique_field(src, f"{base}_origen" if recursive else base)})
                  parsed.append({"from": tgt, "to": intermediate_name, "kind": "one_to_many",
                                 "field": unique_field(tgt, f"{base}_destino" if recursive else base)})
              elif source_is_many and not target_is_many:
                  # source *..1 target => Source tiene ManyToOne hacia Target
                  parsed.append({"from": src, "to": tgt, "kind": "many_to_one",
                                 "optional": target_card.startswith("0"),
                                 "field": unique_field(src, "padre" if recursive else self._to_snake_case(tgt))})
              elif not source_is_many and not target_is_many:
                  # 1..1 => OneToOne
                  is_composition = rtype == "composition"
                  parsed.append({"from": src, "to": tgt, "kind": "one_to_one", "composition": is_composition,
                                 "field": unique_field(src, self._to_snake_case(tgt))})
              elif not source_is_many and target_is_many:
                  # source 1..* target => Source tiene OneToMany hacia Target
                  parsed.append({"from": src, "to": tgt, "kind": "one_to_many",
                                 "field": unique_field(src, "hijos" if recursive else self._to_snake_case(tgt))})
              
              # === Lado INVERSO (Target) ===
              if not target_is_many and source_is_many:
                  # source *..1 target => Target tiene OneToMany hacia Source (relación inversa)
                  parsed.append({"from": tgt, "to": src, "kind": "one_to_many",
                                 "field": unique_field(tgt, "hijos" if recursive else self._to_snake_case(src))})
              elif target_is_many and not source_is_many:
                  # source 1..* target => Target tiene ManyToOne hacia Source (relación inversa)
                  parsed.append({"from": tgt, "to": src, "kind": "many_to_one",
                                 "optional": source_card.startswith("0"),
                                 "field": unique_field(tgt, "padre" if recursive else self._to_snake_case(src))})

      return parsed
        
    def generate_project(self, output_dir="generated_flutter_app"):
        """Genera el proyecto Flutter completo"""
        base_path = Path(output_dir)
        
        # Crear estructura de carpetas
        self._create_folder_structure(base_path)
        
        # Generar archivos base
        self._generate_pubspec(base_path)
        self._generate_app_icon(base_path)
        self._generate_config(base_path)
        self._generate_ios_local_ai_setup_script(base_path)
        
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
                    "field": self._to_snake_case(entity_name),
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
            self._generate_assistant_texts(base_path)
            self._generate_entity_service_registry(base_path, original_classes)
            self._generate_command_router(base_path)
            self._generate_voice_input_controller(base_path)
            self._generate_model_downloader(base_path)
            self._generate_local_model_manager(base_path)
            self._generate_local_llm_command_extractor(base_path)
            self._generate_local_llm_chat(base_path)
            self._generate_assistant_view(base_path)
            self._generate_assistant_tests(base_path, original_classes)
            self._generate_assistant_texts_tests(base_path)
            self._generate_voice_tests(base_path)
            self._generate_model_download_tests(base_path)
            self._generate_local_llm_tests(base_path, original_classes)
            self._generate_local_llm_chat_tests(base_path)

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
  flutter: '>=3.38.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.2
  http: ^1.1.0
  provider: ^6.0.5
  sqflite: ^2.4.4
  path: ^1.9.1
  speech_to_text: ^7.5.0
  file_selector: ^1.1.0
  path_provider: ^2.1.6
  # Versiones EXACTAS y juntas (ambas usan el runtime nativo v0.4.1). Con ^, pub resolvia llamadart 0.8.24 +
  # companion 0.0.23, un par que llamadart rechaza en Apple y el proyecto dejaba de compilar. El par
  # 0.8.23 + 0.0.18 tampoco sirve: su hook falla con el Flutter actual (carpeta Artifacts/). Subirlas siempre como par.
  llamadart: 0.8.24
  llamadart_llama_cpp_flutter: 0.0.19

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^2.0.0
  flutter_launcher_icons: ^0.14.0

# Icono propio de la app (en vez del logo de Flutter). `tool/configure_ios_local_ai.sh` ejecuta
# `dart run flutter_launcher_icons` despues de `flutter create`.
flutter_launcher_icons:
  android: true
  ios: true
  image_path: "assets/icon/app_icon.png"
  adaptive_icon_background: "#__ICON_BACKGROUND__"
  adaptive_icon_foreground: "assets/icon/app_icon_foreground.png"
  remove_alpha_ios: true

flutter:
  uses-material-design: true
"""
        content = content.replace('__ICON_BACKGROUND__', self._seed_color_hex(self._app_name()))
        with open(base_path / 'pubspec.yaml', "w", encoding="utf-8") as f:
          f.write(self._sanitize(content))

    def _generate_ios_local_ai_setup_script(self, base_path):
        """Genera tool/configure_ios_local_ai.sh: un script POSIX (sed/grep
        solamente, sin Ruby/plutil) que el desarrollador ejecuta DESPUES de
        `flutter create . --platforms=ios,android,web`, para fijar el
        deployment target de iOS en 16.4 (requerido por el motor de
        inferencia local). No modifica archivos del SDK de Flutter: solo
        ios/Runner.xcodeproj/project.pbxproj (siempre) e ios/Podfile (solo si
        existe), ambos dentro del propio proyecto generado.
        Nota verificada empiricamente (Flutter 3.47.x): `flutter create` con
        integracion via Swift Package Manager (el default actual) NO genera
        ios/Podfile en absoluto; solo aparece si/cuando el proyecto adopta
        CocoaPods. El script debe funcionar en ambos casos: el
        IPHONEOS_DEPLOYMENT_TARGET del .pbxproj es el requisito real que
        Xcode exige para resolver el paquete SPM
        llamadart_llama_cpp_flutter; el Podfile es opcional/best-effort."""
        content = '''#!/bin/sh
# Configura el proyecto iOS generado para requerir 16.4+, necesario para la
# inferencia local (llamadart + llamadart_llama_cpp_flutter). Ejecutar UNA
# vez despues de `flutter create . --platforms=ios,android,web`.
#
# Uso:
#   tool/configure_ios_local_ai.sh            # aplica el deployment target
#   tool/configure_ios_local_ai.sh --verify   # solo verifica, no modifica
#
# No modifica nada fuera de ios/Runner.xcodeproj/project.pbxproj (siempre),
# ios/Podfile (solo si existe) e ios/Runner/Info.plist (solo agrega los dos
# textos de permiso de voz, una sola vez) de este proyecto. No requiere Ruby,
# CocoaPods ni plutil: solo sed/grep/awk.
#
# Los textos de permiso son obligatorios: sin NSMicrophoneUsageDescription y
# NSSpeechRecognitionUsageDescription, iOS CIERRA la app (privacy violation)
# en cuanto el asistente pide el microfono o el reconocimiento de voz.
#
# Nota: con integracion via Swift Package Manager (el flujo por defecto en
# Flutter 3.38+), `flutter create` NO genera ios/Podfile; en ese caso este
# script solo toca project.pbxproj, que es lo que Xcode realmente exige para
# resolver el paquete llamadart_llama_cpp_flutter. Si tu proyecto SI usa
# CocoaPods, tambien fija `platform :ios, 'X.Y'` en el Podfile.

set -eu

TARGET="16.4"
PODFILE="ios/Podfile"
PBXPROJ="ios/Runner.xcodeproj/project.pbxproj"
INFO_PLIST="ios/Runner/Info.plist"
ANDROID_MANIFEST="android/app/src/main/AndroidManifest.xml"
MIC_KEY="NSMicrophoneUsageDescription"
SPEECH_KEY="NSSpeechRecognitionUsageDescription"
# Nombre que se ve bajo el icono (solo letras, numeros, espacios, punto y guion: seguro en plist, XML y shell).
APP_DISPLAY_NAME='__APP_DISPLAY_NAME__'
VERIFY_ONLY=0

if [ "${1:-}" = "--verify" ]; then
  VERIFY_ONLY=1
fi

if [ ! -f "$PBXPROJ" ]; then
  echo "error: $PBXPROJ no existe. Ejecuta primero:" >&2
  echo "  flutter create . --platforms=ios,android,web" >&2
  exit 1
fi

check_podfile() {
  [ -f "$PODFILE" ] || return 0
  grep -Eq "^[[:space:]]*platform[[:space:]]*:ios,[[:space:]]*['\\"]${TARGET}['\\"]" "$PODFILE"
}

check_pbxproj() {
  ! grep -E "IPHONEOS_DEPLOYMENT_TARGET[[:space:]]*=" "$PBXPROJ" \\
    | grep -vq "IPHONEOS_DEPLOYMENT_TARGET = ${TARGET};"
}

has_plist_key() {
  grep -q "<key>$1</key>" "$INFO_PLIST"
}

check_plist() {
  [ -f "$INFO_PLIST" ] || return 0
  has_plist_key "$MIC_KEY" && has_plist_key "$SPEECH_KEY"
}

# Cambia el <string> que sigue a <key>CLAVE</key>; si la clave no existe, la agrega.
set_plist_string() {
  if grep -q "<key>$1</key>" "$INFO_PLIST"; then
    awk -v k="$1" -v v="$2" '
      prev ~ ("<key>" k "</key>") { sub(/<string>[^<]*<\\/string>/, "<string>" v "</string>") }
      { print; prev = $0 }
    ' "$INFO_PLIST" > "$INFO_PLIST.new" && mv "$INFO_PLIST.new" "$INFO_PLIST"
  else
    add_plist_key "$1" "$2"
  fi
}

# Agrega <key>/<string> justo despues del primer <dict> (el de nivel superior).
add_plist_key() {
  has_plist_key "$1" && return 0
  awk -v k="$1" -v t="$2" '
    !done && /<dict>/ { print; print "    <key>" k "</key>"; print "    <string>" t "</string>"; done = 1; next }
    { print }
  ' "$INFO_PLIST" > "$INFO_PLIST.new" && mv "$INFO_PLIST.new" "$INFO_PLIST"
}

if [ "$VERIFY_ONLY" -eq 1 ]; then
  ok=1
  if ! check_podfile; then
    echo "FAIL: $PODFILE no fija platform :ios, '${TARGET}'" >&2
    ok=0
  fi
  if ! check_pbxproj; then
    echo "FAIL: $PBXPROJ tiene un IPHONEOS_DEPLOYMENT_TARGET distinto de ${TARGET}" >&2
    ok=0
  fi
  if ! check_plist; then
    echo "FAIL: $INFO_PLIST no tiene $MIC_KEY y $SPEECH_KEY (sin ellos iOS cierra la app al abrir el asistente)" >&2
    ok=0
  fi
  if [ "$ok" -eq 1 ]; then
    echo "OK: iOS deployment target en ${TARGET} y permisos de voz presentes"
    exit 0
  fi
  exit 1
fi

# --- Podfile (si existe): fijar/crear la linea `platform :ios, 'X.Y'` ---
if [ -f "$PODFILE" ]; then
  if grep -Eq "^[[:space:]]*#?[[:space:]]*platform[[:space:]]*:ios," "$PODFILE"; then
    sed -i.bak -E "s/^[[:space:]]*#?[[:space:]]*platform[[:space:]]*:ios,.*/platform :ios, '${TARGET}'/" "$PODFILE"
  else
    { echo "platform :ios, '${TARGET}'"; cat "$PODFILE"; } > "$PODFILE.new" && mv "$PODFILE.new" "$PODFILE"
  fi
  rm -f "$PODFILE.bak"
else
  echo "info: $PODFILE no existe (proyecto integrado via Swift Package Manager); se omite."
fi

# --- project.pbxproj: reemplazar todas las ocurrencias de
# IPHONEOS_DEPLOYMENT_TARGET (Debug/Release/Profile suelen repetirla) ---
sed -i.bak -E "s/IPHONEOS_DEPLOYMENT_TARGET = [^;]*;/IPHONEOS_DEPLOYMENT_TARGET = ${TARGET};/g" "$PBXPROJ"
rm -f "$PBXPROJ.bak"

# --- Info.plist: textos de permiso de voz (iOS cierra la app si faltan) ---
if [ -f "$INFO_PLIST" ]; then
  add_plist_key "$MIC_KEY" "Esta app usa el microfono para el asistente por voz."
  add_plist_key "$SPEECH_KEY" "Esta app usa reconocimiento de voz para interpretar comandos del asistente."
  set_plist_string CFBundleDisplayName "$APP_DISPLAY_NAME"
else
  echo "info: $INFO_PLIST no existe; se omiten los textos de permiso de voz."
fi

# --- Android: nombre bajo el icono ---
if [ -f "$ANDROID_MANIFEST" ]; then
  sed -i.bak -E "s/android:label=\\"[^\\"]*\\"/android:label=\\"${APP_DISPLAY_NAME}\\"/" "$ANDROID_MANIFEST"
  rm -f "$ANDROID_MANIFEST.bak"
fi

# --- Android: permisos de internet (descargar la IA local) y microfono (voz), una sola vez ---
if [ -f "$ANDROID_MANIFEST" ]; then
  for PERMISSION in INTERNET RECORD_AUDIO; do
    if ! grep -q "android.permission.$PERMISSION" "$ANDROID_MANIFEST"; then
      awk -v p="$PERMISSION" '
        { print }
        !done && /<manifest/ { print "    <uses-permission android:name=\\"android.permission." p "\\"/>"; done = 1 }
      ' "$ANDROID_MANIFEST" > "$ANDROID_MANIFEST.new" && mv "$ANDROID_MANIFEST.new" "$ANDROID_MANIFEST"
    fi
  done
fi

# --- Icono propio de la app (en vez del logo de Flutter) ---
if [ -f assets/icon/app_icon.png ] && command -v dart >/dev/null 2>&1; then
  if dart run flutter_launcher_icons >/dev/null 2>&1; then
    echo "OK: icono de la app generado"
  else
    echo "aviso: no se pudo generar el icono; ejecuta 'flutter pub get' y luego 'dart run flutter_launcher_icons'" >&2
  fi
fi

if check_podfile && check_pbxproj && check_plist; then
  echo "OK: iOS deployment target configurado en ${TARGET} y permisos de voz presentes"
else
  echo "error: la configuracion no se aplico correctamente; revisa $PBXPROJ, $INFO_PLIST (y $PODFILE si existe)" >&2
  exit 1
fi
'''
        content = content.replace('__APP_DISPLAY_NAME__', self._platform_app_name())
        script_path = base_path / 'tool' / 'configure_ios_local_ai.sh'
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(self._sanitize(content), encoding="utf-8", newline="\n")
        try:
            script_path.chmod(0o755)
        except OSError:
            pass

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
                        rel_snake = self._rel_field(rel)
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
                    if self._rel_field(rel) not in added_rels:
                        fk_field = f"{self._rel_field(rel)}Id"
                        fk_col = self._to_backend_json_key(fk_field)
                        columns.append(f"{fk_col} TEXT")
                        added_rels.add(self._rel_field(rel))

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

    DEFAULT_APP_NAME = 'Mi aplicación'

    def _platform_app_name(self):
        """Nombre que ve la persona bajo el icono (iOS CFBundleDisplayName / Android label): solo letras, numeros,
        espacios, punto y guion, para que sea seguro dentro de un plist, un XML y un script de shell."""
        import re
        cleaned = re.sub(r'[^\w .\-]', ' ', self._app_name())
        return ' '.join(cleaned.split())[:30] or self.DEFAULT_APP_NAME

    def _generate_app_icon(self, base_path):
        """Escribe assets/icon/app_icon.png (iOS) y app_icon_foreground.png (Android adaptable), con el color de la app."""
        seed = self._seed_color_hex(self._app_name())
        icon_dir = base_path / 'assets' / 'icon'
        icon_dir.mkdir(parents=True, exist_ok=True)
        (icon_dir / 'app_icon.png').write_bytes(app_icon.render_png(seed))
        (icon_dir / 'app_icon_foreground.png').write_bytes(app_icon.render_png(seed, foreground=True))

    def _app_name(self):
        """Nombre de la aplicacion: lo que el usuario escribio al exportar (`appName`, o `projectName`), o un nombre neutro."""
        raw = self.uml_json.get('appName') or self.uml_json.get('projectName') or ''
        name = ' '.join(str(raw).split())[:40].strip()
        return name or self.DEFAULT_APP_NAME

    @staticmethod
    def _dart_string_literal(value):
        """Literal de cadena Dart entre comillas simples (escapa barra, comilla, $ y saltos de linea)."""
        escaped = (
            value.replace('\\', '\\\\').replace("'", "\\'").replace('$', '\\$').replace('\n', ' ').replace('\r', ' ')
        )
        return f"'{escaped}'"

    def _seed_color_hex(self, app_name):
        """Color base de la app (6 hex): el tono sale del nombre, asi cada sistema tiene su propia identidad."""
        import colorsys
        import hashlib
        hue = int(hashlib.sha256(app_name.encode('utf-8')).hexdigest()[:8], 16) % 360 / 360.0
        red, green, blue = colorsys.hls_to_rgb(hue, 0.42, 0.62)
        return '%02X%02X%02X' % (round(red * 255), round(green * 255), round(blue * 255))

    @staticmethod
    def _plural_label(name):
        """"DetalleVenta" -> "Detalle ventas": plural en espanol, mismas reglas que AssistantTexts.plural."""
        import re
        words = re.sub(r'([a-záéíóúñ0-9])([A-ZÁÉÍÓÚÑ])', r'\1 \2', name).replace('_', ' ').lower()
        if words.endswith('z'):
            words = words[:-1] + 'ces'
        elif re.search(r'[aeiouáéíóú]$', words):
            words += 's'
        else:
            words += 'es'
        return words[:1].upper() + words[1:]

    def _generate_main(self, base_path, intermediate_entities=[]):
        """Genera el archivo main.dart: inicio generico (sirve para cualquier diagrama)."""
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
        app_name = self._app_name()
        app_name_literal = self._dart_string_literal(app_name)
        seed = self._seed_color_hex(app_name)

        content = f"""import 'package:flutter/material.dart';
import 'assistant/assistant_view.dart';
{imports_str}

/// Nombre de la aplicacion (lo elige la persona al exportar desde el diagramador).
const String _appName = {app_name_literal};

/// Color base: sale del nombre, asi cada sistema tiene su propia identidad.
const Color _seed = Color(0xFF{seed});

void main() {{
  runApp(const MyApp());
}}

class MyApp extends StatelessWidget {{
  const MyApp({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: _appName,
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: _seed),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: _seed, brightness: Brightness.dark),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }}
}}

class _Section {{
  final String title;
  final String subtitle;
  final WidgetBuilder builder;
  final bool isRelation;
  const _Section(this.title, this.subtitle, this.builder, {{this.isRelation = false}});
}}

final List<_Section> _sections = [
{self._generate_home_cards(intermediate_entities)}
];

class HomePage extends StatelessWidget {{
  const HomePage({{super.key}});

  @override
  Widget build(BuildContext context) {{
    final scheme = Theme.of(context).colorScheme;
    final tones = [
      (scheme.primaryContainer, scheme.onPrimaryContainer),
      (scheme.secondaryContainer, scheme.onSecondaryContainer),
      (scheme.tertiaryContainer, scheme.onTertiaryContainer),
    ];
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          const SliverAppBar.large(title: Text(_appName)),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
              child: Text(
                'Elige qué quieres administrar. También puedes pedírselo al asistente.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 96),
            sliver: SliverGrid.builder(
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 240,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 1.05,
              ),
              itemCount: _sections.length,
              itemBuilder: (context, index) {{
                final section = _sections[index];
                final (background, foreground) = tones[index % tones.length];
                return Card(
                  clipBehavior: Clip.antiAlias,
                  elevation: 0,
                  color: background,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
                  child: InkWell(
                    onTap: () {{
                      Navigator.push(context, MaterialPageRoute(builder: section.builder));
                    }},
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          CircleAvatar(
                            radius: 22,
                            backgroundColor: foreground.withValues(alpha: 0.14),
                            child: section.isRelation
                                ? Icon(Icons.link, color: foreground)
                                : Text(
                                    section.title.isEmpty ? '?' : section.title[0].toUpperCase(),
                                    style: TextStyle(color: foreground, fontSize: 20, fontWeight: FontWeight.w700),
                                  ),
                          ),
                          const Spacer(),
                          Text(
                            section.title,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  color: foreground,
                                  fontWeight: FontWeight.w600,
                                ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            section.subtitle,
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: foreground),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }},
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {{
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const AssistantView()),
          );
        }},
        icon: const Icon(Icons.auto_awesome),
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

    // SliverAppBar.large muestra el titulo dos veces (expandido y contraido).
    expect(find.text(__APP_NAME__), findsWidgets);
  });
}
""".replace('__APP_NAME__', self._dart_string_literal(self._app_name()))
        (base_path / 'test' / 'widget_test.dart').write_text(
            self._sanitize(content),
            encoding="utf-8",
            newline="\n",
        )
    
    def _generate_home_cards(self, intermediate_entities=[]):
        """Genera la lista de secciones del inicio (una por entidad; las tablas de relacion se marcan aparte)."""
        entries = []
        intermediate_names = {ie['name'] for ie in intermediate_entities}

        for clase in self.classes:
            if clase.get('is_intermediate', False) or clase['name'] in intermediate_names:
                continue
            name = clase['name']
            title = self._dart_string_literal(self._plural_label(name))
            entries.append(
                f"  _Section({title}, 'Ver y administrar', (context) => {name}ListView()),"
            )

        for ie in intermediate_entities:
            name = ie['name']
            title = self._dart_string_literal(f"{ie['first_entity']} y {ie['second_entity']}")
            entries.append(
                f"  _Section({title}, 'Relación entre registros', (context) => {name}ListView(), isRelation: true),"
            )

        return '\n'.join(entries)

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
          if rel["from"] == name and rel["kind"] in ["many_to_one", "one_to_one", "one_to_many"] and rel["to"] != name:
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
                  field_name = f"{self._rel_field(rel)}Id"
                  normalized_field = field_name.lower().replace('_', '')
                  if normalized_field not in existing_attr_names:
                      rel_fields.append(f"  final String {field_name};")
                  # Agregar también el objeto completo (nullable, solo para lectura)
                  obj_field_name = self._rel_field(rel)
                  normalized_obj = obj_field_name.lower().replace('_', '')
                  if normalized_obj not in existing_attr_names:
                      rel_fields.append(f"  final {rel['to']}? {obj_field_name};")
              elif rel["kind"] == "one_to_one":
                  # OneToOne: ID (para enviar) + objeto completo opcional (para leer del GET)
                  field_name = f"{self._rel_field(rel)}Id"
                  normalized_field = field_name.lower().replace('_', '')
                  if normalized_field not in existing_attr_names:
                      rel_fields.append(f"  final String {field_name};")
                  # Agregar también el objeto completo (nullable, solo para lectura)
                  obj_field_name = self._rel_field(rel)
                  normalized_obj = obj_field_name.lower().replace('_', '')
                  if normalized_obj not in existing_attr_names:
                      rel_fields.append(f"  final {rel['to']}? {obj_field_name};")
              elif rel["kind"] == "one_to_many":
                  # OneToMany: Lista de objetos completos (solo para lectura desde GET)
                  # El backend devuelve la lista anidada en GET, pero NO se envía en POST/PUT
                  field_name = self._rel_field(rel)
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
                  field_name = f"{self._rel_field(rel)}Id"
                  normalized = field_name.lower().replace('_', '')
                  if normalized not in parent_existing_attrs:
                      super_params_list.append(f"{field_name}: {field_name}")
                      constructor_params_list.append(f"required String {field_name}")
              elif rel["kind"] == "one_to_one":
                  # OneToOne: agregar el ID
                  field_name = f"{self._rel_field(rel)}Id"
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
                  field_name = f"{self._rel_field(rel)}Id"
                  normalized_field = field_name.lower().replace('_', '')
                  if normalized_field not in existing_attr_names_normalized:
                      constructor_params_list.append(f"required this.{field_name}")
                  # Agregar objeto completo (opcional, default null)
                  obj_field_name = self._rel_field(rel)
                  normalized_obj = obj_field_name.lower().replace('_', '')
                  if normalized_obj not in existing_attr_names_normalized:
                      constructor_params_list.append(f"this.{obj_field_name}")
              elif rel["kind"] == "one_to_one":
                  # Agregar FK (ID) para relaciones OneToOne (required)
                  field_name = f"{self._rel_field(rel)}Id"
                  normalized_field = field_name.lower().replace('_', '')
                  if normalized_field not in existing_attr_names_normalized:
                      constructor_params_list.append(f"required this.{field_name}")
                  # Agregar objeto completo (opcional, default null)
                  obj_field_name = self._rel_field(rel)
                  normalized_obj = obj_field_name.lower().replace('_', '')
                  if normalized_obj not in existing_attr_names_normalized:
                      constructor_params_list.append(f"this.{obj_field_name}")
              elif rel["kind"] == "one_to_many":
                  # OneToMany: Lista opcional (vacía por defecto para POST/PUT, poblada en GET)
                  field_name = self._rel_field(rel)
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
              rel_name = self._rel_field(rel)
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
              rel_name = self._rel_field(rel)
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
              rel_name = self._rel_field(rel)
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
              rel_name = self._rel_field(rel)
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
            rel_key = f"{self._rel_var(rel)}"
            if rel_key not in added_relations:
                controllers_list.append(f"String? _selected{self._rel_var(rel)}Id;")
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
            rel_key = f"{self._rel_var(rel)}"
            if rel_key not in initialized_relations:
                field_name = f"{self._rel_field(rel)}Id"
                # Convertir a String y manejar valores vacíos para evitar que sea ""
                # El dropdown espera null o un valor válido que exista en la lista
                init_controllers_list.append(f"if (widget.item!.{field_name}.isNotEmpty) {{ _selected{self._rel_var(rel)}Id = widget.item!.{field_name}; }}")
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
                
                # Una relación con multiplicidad 0..1 no se exige: el padre de una recursiva (0..1) no existe
                # para el primer registro, y sin esta excepción nunca se podría crear.
                required_validator = "" if rel.get("optional") else """
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Este campo es requerido';
                    }
                    return null;
                  },"""
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
                final validValue = _selected{self._rel_var(rel)}Id != null && 
                    uniqueItems.any((e) => e.{related_pk}.toString() == _selected{self._rel_var(rel)}Id)
                    ? _selected{self._rel_var(rel)}Id
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
                      _selected{self._rel_var(rel)}Id = v;
                    }});
                  }},{required_validator}
                );
              }},
            )""")
        
        # Relaciones OneToOne → Dropdown
        for rel in relationships:
            if rel["kind"] == "one_to_one":
                field_name = self._rel_field(rel)
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
                  initialValue: _selected{self._rel_var(rel)}Id,
                  items: snapshot.data!.map((e) => DropdownMenuItem(
                    value: e.{related_pk}.toString(),
                    child: Text(e.{display_attr}.toString()),
                  )).toList(),
                  onChanged: (v) {{
                    setState(() {{
                      _selected{self._rel_var(rel)}Id = v;
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
                    field_name = f"{self._rel_field(rel)}Id"
                    if field_name not in used_field_names:
                        create_object_fields_list.append(f"{field_name}: _selected{self._rel_var(rel)}Id ?? ''")
                        used_field_names.add(field_name)
                elif rel["kind"] == "one_to_one":
                    field_name = f"{self._rel_field(rel)}Id"
                    if field_name not in used_field_names:
                        create_object_fields_list.append(f"{field_name}: _selected{self._rel_var(rel)}Id ?? ''")
                        used_field_names.add(field_name)
                # OneToMany: NO se agrega (no existe en el modelo)
        
        create_object_fields = ',\n          '.join(create_object_fields_list)
        
        # Agregar relaciones many_to_one al objeto
        many_to_one_fields = []
        for rel in relationships:
            if rel["kind"] == "many_to_one":
                field_name = f"{self._rel_field(rel)}Id"
                normalized_field = field_name.lower().replace('_', '')
                if normalized_field not in existing_attr_names_normalized:
                    many_to_one_fields.append(f"{field_name}: _selected{self._rel_var(rel)}Id ?? ''")
        
        if many_to_one_fields:
            if create_object_fields:
                create_object_fields += ',\n          ' + ',\n          '.join(many_to_one_fields)
            else:
                create_object_fields = ',\n          '.join(many_to_one_fields)
        
        # Agregar relaciones OneToOne al objeto (solo IDs)
        one_to_one_fields = []
        for rel in relationships:
            if rel["kind"] == "one_to_one":
                field_name = f"{self._rel_field(rel)}Id"
                normalized_field = field_name.lower().replace('_', '')
                if normalized_field not in existing_attr_names_normalized:
                    one_to_one_fields.append(f"{field_name}: _selected{self._rel_var(rel)}Id ?? ''")
        
        if one_to_one_fields:
            if create_object_fields:
                create_object_fields += ',\n          ' + ',\n          '.join(one_to_one_fields)
            else:
                create_object_fields = ',\n          '.join(one_to_one_fields)
        
        # Generar imports para modelos y servicios relacionados
        related_imports = []
        
        for rel in relationships:
            # Importar servicios para cargar opciones de dropdown (ManyToOne y OneToOne)
            if rel["kind"] in ["one_to_one", "many_to_one"] and rel["to"] != name:
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
                field_name = self._rel_field(rel)
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
                        # Una lista de la misma clase (los hijos de una relación recursiva) nunca es una tabla puente,
                        # aunque la clase tenga justo dos relaciones muchos-a-uno (p. ej. padre y departamento).
                        if len(many_to_one_rels) == 2 and rel['to'] != name:
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
                            other_field = self._rel_field(first_rel)
                            other_entity_name = first_rel['to']
                        elif second_rel['to'] != name:
                            other_rel = second_rel
                            other_field = self._rel_field(second_rel)
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
                field_name = self._rel_field(rel)
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
            rel_snake = self._rel_field(rel)
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
                    # Una relacion 0..1 (p. ej. el padre de una recursiva) no se exige: sin esto el primer
                    # registro no se puede crear. Mismo criterio que el formulario (`optional` al leer las multiplicidades).
                    'required_on_create': not rel.get('optional', False),
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
  /// Nombre de la aplicación (el que se escribió al exportar): la IA lo usa para presentarse.
  static const String appName = __APP_NAME__;

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
  ///
  /// También trata las variantes comunes de guion/raya como un espacio
  /// (p. ej. el dictado de iOS que produce "Coca-Cola" para un registro
  /// guardado como "Coca cola"), y colapsa los espacios repetidos que eso
  /// pueda dejar. Deliberadamente NO hace una limpieza general de
  /// puntuación: solo guiones/rayas, para mantener este fix acotado.
  static String normalize(String value) {
    const from = 'áéíóúÁÉÍÓÚ';
    const to = 'aeiouAEIOU';
    var result = value.trim().toLowerCase();
    for (var i = 0; i < from.length; i++) {
      result = result.replaceAll(from[i], to[i].toLowerCase());
    }
    const dashVariants = ['-', '‐', '‑', '‒', '–', '—', '―'];
    for (final dash in dashVariants) {
      result = result.replaceAll(dash, ' ');
    }
    result = result.replaceAll(RegExp(' +'), ' ').trim();
    return result;
  }
}
'''
        content = content.replace('__ENTITIES__', entities_str)
        content = content.replace('__APP_NAME__', self._dart_string_literal(self._app_name()))
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

  /// Reconoce solo la intención CRUD explícita del primer verbo, sin
  /// interpretar todavía entidad, campos ni valores. El extractor local la
  /// reutiliza como compuerta de seguridad: un LLM nunca puede convertir una
  /// lectura o una entrada ambigua en una mutación.
  static CommandAction? recognizeAction(String rawText) {
    final trimmed = rawText.trim();
    if (trimmed.isEmpty) return null;
    final firstToken = trimmed.split(RegExp(r'\s+')).first;
    return _actionVerbs[AppSchema.normalize(firstToken)];
  }

  ParsedCommandResult parse(String rawText) {
    final trimmed = rawText.trim();
    if (trimmed.isEmpty) {
      return const ParsedCommandResult.failure('Escribe o di un comando.');
    }

    final tokens = _splitWords(trimmed);
    final verbToken = tokens.first;
    final rest = tokens.length > 1 ? tokens.sublist(1).join(' ') : '';

    final action = recognizeAction(trimmed);
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
    final idFilter = _idFilter(leftover, entity);
    if (idFilter != null) {
      filters.addAll(idFilter);
    } else if (leftover.isNotEmpty) {
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

  static final RegExp _idPhrase = RegExp(
    r'^(?:con\s+)?(?:id|n[uú]mero|nro\.?|n°|#)\s*[:=]?\s*(\d+)$',
    caseSensitive: false,
  );

  /// "con id 3", "número 3" o "#3" identifican un registro por su clave primaria; null si no tiene esa forma.
  Map<String, dynamic>? _idFilter(String leftover, AssistantEntitySchema entity) {
    final match = _idPhrase.firstMatch(leftover.trim());
    if (match == null) return null;
    final keys = entity.fields.where((field) => field.isPrimaryKey);
    if (keys.isEmpty) return null;
    final key = keys.first;
    final number = int.parse(match.group(1)!);
    return {key.name: key.dartType == 'int' ? number : number.toString()};
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

    def _generate_assistant_texts(self, base_path):
        """Genera lib/assistant/assistant_texts.dart: respuestas del asistente en español natural, saludos y ayuda.
        Todo se deriva de AppSchema en tiempo de ejecucion (mismo archivo para cualquier esquema)."""
        content = '''import 'app_schema.dart';

/// Estado de la IA local tal como el asistente se lo cuenta a la persona (no depende del motor de inferencia).
enum AssistantAiState { none, downloading, loading, ready }

/// Textos del asistente en español natural. Todo se deriva de AppSchema en
/// tiempo de ejecución: este archivo nunca nombra una entidad ni un campo de
/// un proyecto concreto. Evita artículos y adjetivos con género
/// ("registrados") porque el género de cada entidad no se conoce; solo los
/// ejemplos infieren "un/una" con una regla sencilla.
class AssistantTexts {
  AssistantTexts._();

  /// "DetalleVenta" / "detalle_venta" -> "detalle venta".
  static String humanize(String name) {
    final spaced = name.replaceAllMapped(
      RegExp(r'([a-záéíóúñ0-9])([A-ZÁÉÍÓÚÑ])'),
      (match) => '${match[1]} ${match[2]}',
    );
    return spaced.replaceAll('_', ' ').toLowerCase();
  }

  static String singular(AssistantEntitySchema schema) => humanize(schema.name);

  static String plural(AssistantEntitySchema schema) {
    final word = singular(schema);
    if (word.endsWith('z')) return '${word.substring(0, word.length - 1)}ces';
    if (RegExp(r'[aeiouáéíóú]$').hasMatch(word)) return '${word}s';
    return '${word}es';
  }

  static String _indefinite(String singularWord) {
    const masculineEndingInA = {'problema', 'sistema', 'tema', 'programa', 'diagrama', 'esquema', 'idioma', 'mapa', 'día', 'dia', 'planeta'};
    final noun = singularWord.split(' ').first;
    if (masculineEndingInA.contains(noun)) return 'un';
    final feminine = noun.endsWith('a') ||
        noun.endsWith('ión') ||
        noun.endsWith('dad') ||
        noun.endsWith('tad') ||
        noun.endsWith('tud');
    return feminine ? 'una' : 'un';
  }

  static String _valueText(Object? value) {
    if (value is bool) return value ? 'sí' : 'no';
    return '$value';
  }

  static AssistantFieldSchema? _nameFieldOf(AssistantEntitySchema schema) {
    final candidate = schema.nameField;
    if (candidate == null) return null;
    for (final field in schema.fields) {
      if (field.name == candidate) return field;
    }
    return null;
  }

  /// Texto corto de un registro: su nombre (o su clave si la entidad no tiene un campo de nombre).
  static String rowTitle(AssistantEntitySchema schema, Map<String, dynamic> row) {
    final nameField = _nameFieldOf(schema);
    final value = nameField == null ? null : row[nameField.jsonKey];
    if (value != null && '$value'.trim().isNotEmpty) return _valueText(value);
    final pk = row[schema.pkField.jsonKey];
    return pk == null ? '' : '#${_valueText(pk)}';
  }

  /// Los demás campos de un registro ("edad: 30, ciudad: Quito"), sin la clave ni el nombre.
  static String rowDetails(AssistantEntitySchema schema, Map<String, dynamic> row) {
    final nameField = _nameFieldOf(schema);
    final parts = <String>[];
    for (final field in schema.fields) {
      if (field.isPrimaryKey) continue;
      if (nameField != null && field.name == nameField.name) continue;
      final value = row[field.jsonKey];
      if (value == null || '$value'.trim().isEmpty) continue;
      parts.add('${humanize(field.name)}: ${_valueText(value)}');
    }
    return parts.join(', ');
  }

  /// Resultado de una consulta en lenguaje natural (0, 1 o varios registros).
  static String describeRows(
    AssistantEntitySchema schema,
    List<Map<String, dynamic>> rows, {
    bool filtered = false,
    int maxRows = 5,
  }) {
    if (rows.isEmpty) {
      return filtered
          ? 'No encontré registros de ${plural(schema)} con esos datos.'
          : 'Todavía no hay registros de ${plural(schema)}.';
    }
    if (rows.length == 1) {
      final details = rowDetails(schema, rows.first);
      final suffix = details.isEmpty ? '' : ' ($details)';
      return 'Encontré 1 ${singular(schema)}: ${rowTitle(schema, rows.first)}$suffix.';
    }
    final buffer = StringBuffer('Encontré ${rows.length} ${plural(schema)}:');
    for (final row in rows.take(maxRows)) {
      buffer.write('\\n• ${rowTitle(schema, row)}');
    }
    final remaining = rows.length - maxRows;
    if (remaining > 0) buffer.write('\\ny $remaining más.');
    return buffer.toString();
  }

  static String created(AssistantEntitySchema schema, Map<String, dynamic> row) {
    final title = rowTitle(schema, row);
    final detail = title.isEmpty ? '' : ': «$title»';
    return 'Listo: guardé un nuevo registro de ${singular(schema)}$detail.';
  }

  static String updated(AssistantEntitySchema schema, Map<String, dynamic> row) {
    final title = rowTitle(schema, row);
    final detail = title.isEmpty ? '' : ': «$title»';
    return 'Listo: actualicé el registro de ${singular(schema)}$detail.';
  }

  static const String deleted = 'Listo: eliminé el registro.';

  static String confirmDelete(AssistantEntitySchema schema) =>
      'Confirma que quieres eliminar este registro de ${singular(schema)}.';

  static String notFound(AssistantEntitySchema schema) =>
      'No encontré ningún registro de ${singular(schema)} que coincida.';

  static String ambiguous(AssistantEntitySchema schema, int count) =>
      'Encontré $count registros de ${plural(schema)} que coinciden. Sé más específico, por ejemplo con el nombre completo.';

  // ------------------------------------------------------------------ saludos y ayuda

  static String _entityList() {
    final names = AppSchema.entities.map(plural).toList();
    if (names.isEmpty) return 'tus datos';
    if (names.length == 1) return names.first;
    return '${names.sublist(0, names.length - 1).join(', ')} y ${names.last}';
  }

  /// Tres ejemplos que el asistente sí entiende, con la primera entidad del esquema.
  static String examples() {
    if (AppSchema.entities.isEmpty) return '';
    final first = AppSchema.entities.first;
    final noun = singular(first);
    return '• «muéstrame los ${plural(first)}»\\n'
        '• «crea ${_indefinite(noun)} $noun llamado Ejemplo»\\n'
        '• «elimina $noun Ejemplo»';
  }

  /// Sugerencias para tocar en la pantalla de bienvenida (siempre cosas que el asistente entiende).
  static List<String> suggestions() {
    if (AppSchema.entities.isEmpty) return const ['Ayuda'];
    final first = AppSchema.entities.first;
    final noun = singular(first);
    return [
      'Muéstrame los ${plural(first)}',
      'Crea ${_indefinite(noun)} $noun llamado Ejemplo',
      'Ayuda',
    ];
  }

  static String greeting() =>
      '¡Hola! Soy tu asistente. Puedo ayudarte con ${_entityList()}.\\nPrueba, por ejemplo:\\n${examples()}';

  static String help() =>
      'Puedo ayudarte con ${_entityList()}: consultar, crear, cambiar y eliminar registros.\\nPrueba, por ejemplo:\\n${examples()}';

  static String notUnderstood() =>
      'No logré entender eso. Puedo ayudarte con ${_entityList()}.\\nPrueba, por ejemplo:\\n${examples()}';

  static final RegExp _leadingGreeting = RegExp(
    r'^[\\s¡!]*(hola|holi|hey|ey|saludos|buen[oa]s(?:\\s+(?:d[ií]as|tardes|noches))?|buen\\s+d[ií]a)(?![a-záéíóúñ])[\\s,.!¡?]*',
    caseSensitive: false,
  );

  /// Quita un saludo al inicio: "hola, muéstrame los empleados" -> "muéstrame los empleados".
  static String withoutLeadingGreeting(String raw) => raw.replaceFirst(_leadingGreeting, '').trim();

  static String _plain(String raw) {
    final text = AppSchema.normalize(raw).replaceAll(RegExp(r'[^a-zñü0-9 ]'), ' ');
    return text.replaceAll(RegExp(' +'), ' ').trim();
  }

  static const Set<String> _howAreYou = {'que tal', 'como estas', 'como va', 'como te va', 'como andas', 'como estas hoy'};
  static const Set<String> _goodbyes = {'adios', 'chao', 'chau', 'bye', 'hasta luego', 'hasta pronto', 'nos vemos'};
  static const Set<String> _helpPhrases = {
    'ayuda', 'ayudame', 'help', 'que puedes hacer', 'que sabes hacer', 'como funciona', 'como te uso', 'como se usa',
    'que haces', 'para que sirves', 'que puedo decirte', 'que puedo pedirte', 'ejemplos', 'comandos', 'instrucciones',
    'opciones', 'menu', 'que mas puedes hacer', 'que mas sabes hacer', 'en que me puedes ayudar',
    'con que me puedes ayudar', 'en que puedes ayudarme', 'que puedes hacer por mi',
  };
  static const Set<String> _identityPhrases = {
    'quien eres', 'quien eres tu', 'como te llamas', 'que eres', 'con quien hablo', 'con quien estoy hablando', 'quien me habla',
  };
  static const Set<String> _aiWords = {'ia', 'ai', 'robot', 'bot', 'chatbot', 'humano', 'maquina'};
  static const Set<String> _aboutYouVerbs = {'eres', 'usas', 'tienes', 'funcionas', 'hablo', 'hablas', 'respondes'};

  /// "¿eres una IA?", "¿usas inteligencia artificial?", "¿con quién hablo?". Una frase corta que menciona una entidad del
  /// esquema ("¿tienes un robot llamado R2?") es una orden, no una pregunta sobre el asistente.
  static bool _asksWhatItIs(String rest) {
    if (_identityPhrases.contains(rest)) return true;
    final words = rest.split(' ');
    if (words.length > 8) return false;
    final padded = ' $rest ';
    for (final entity in AppSchema.entities) {
      if (padded.contains(' ${_plain(singular(entity))} ') || padded.contains(' ${_plain(plural(entity))} ')) return false;
    }
    final aboutAi = words.any(_aiWords.contains) || rest.contains('inteligencia artificial');
    return aboutAi && words.any(_aboutYouVerbs.contains);
  }

  /// Quién es el asistente, sin esquivar la pregunta: dice si usa IA según el estado real de la IA local.
  static String aboutMe(AssistantAiState ai) {
    switch (ai) {
      case AssistantAiState.ready:
        return 'Sí: uso una IA que corre dentro de tu teléfono, sin internet, para entender lo que escribes o dices. '
            'Puedes pedirme consultar, crear, cambiar o eliminar ${_entityList()}.';
      case AssistantAiState.loading:
        return 'Soy el asistente de esta app. Estoy preparando la IA local; en unos segundos la usaré. '
            'Mientras tanto entiendo órdenes sencillas, por ejemplo:\\n${examples()}';
      case AssistantAiState.downloading:
        return 'Soy el asistente de esta app. Estoy descargando la IA local; cuando termine la usaré para entender frases más libres. '
            'Mientras tanto entiendo órdenes sencillas, por ejemplo:\\n${examples()}';
      case AssistantAiState.none:
        return 'Soy el asistente de esta app. Todavía no uso IA: entiendo órdenes sencillas, por ejemplo:\\n${examples()}\\n'
            'Para entender frases más libres, toca «Descargar IA local» (unos 1,1 GB, una sola vez).';
    }
  }

  /// Respuesta a un saludo, gracias, despedida, ayuda o "quién eres". Devuelve null si el mensaje es una orden real:
  /// así "hola" ya no se interpreta como una consulta ("Sin resultados").
  static String? smallTalkReply(String raw, {AssistantAiState ai = AssistantAiState.none}) {
    if (_plain(raw).isEmpty) return null;
    final rest = _plain(withoutLeadingGreeting(raw));
    if (rest.isEmpty) return greeting();
    if (_howAreYou.contains(rest)) return '¡Muy bien, gracias por preguntar! ¿Qué necesitas hacer con ${_entityList()}?';
    if (rest.contains('gracias') && rest.split(' ').length <= 4) return 'De nada. Aquí estoy si necesitas algo más.';
    if (_goodbyes.contains(rest)) return '¡Hasta luego! Cuando quieras, aquí estaré.';
    if (_helpPhrases.contains(rest)) return help();
    if (_asksWhatItIs(rest)) return aboutMe(ai);
    return null;
  }

  // ------------------------------------------------------------------ órdenes, charla con la IA y datos reales

  static const Set<String> _orderVerbs = {
    'crea', 'crear', 'agrega', 'agregar', 'añade', 'añadir', 'anade', 'anadir', 'registra', 'registrar',
    'elimina', 'eliminar', 'borra', 'borrar', 'quita', 'quitar', 'actualiza', 'actualizar', 'cambia', 'cambiar',
    'modifica', 'modificar', 'edita', 'editar', 'muestra', 'muestrame', 'mostrar', 'mostrarme', 'lista', 'listar',
    'ver', 'busca', 'buscar', 'encuentra', 'dame', 'enumera', 'consulta', 'consultar',
  };

  static final RegExp _orderFiller = RegExp(
    r'^(?:por\\s+favor|porfa|puedes|podr[ií]as|quisiera|quiero|necesito|me\\s+gustar[ií]a)[\\s,]+',
    caseSensitive: false,
  );

  /// La orden sin cortesías ni rodeos, para que el intérprete la entienda: "por favor, lista todos los empleados" ->
  /// "lista los empleados"; "crea un empleado llamado Ana" -> "crea un empleado Ana"; "borra al empleado Ana" ->
  /// "borra el empleado Ana". No toca "con nombre Ana y edad 3" (el intérprete usa "con" para separar campos).
  static String orderText(String raw) {
    var text = withoutLeadingGreeting(raw);
    var previous = '';
    while (previous != text) {
      previous = text;
      text = text.replaceFirst(_orderFiller, '').trim();
    }
    text = text.replaceAllMapped(RegExp(r'\\b(?:todos|todas)\\s+(los|las)\\b', caseSensitive: false), (m) => m[1]!);
    text = text.replaceAll(
      RegExp(r'\\s+(?:llamad[oa]s?|de\\s+nombre|que\\s+se\\s+llam[ae]|con\\s+el\\s+nombre\\s+de)\\s+', caseSensitive: false),
      ' ',
    );
    text = text.replaceAllMapped(RegExp(r'\\b(un|una)\\s+(?:nuevo|nueva)\\b', caseSensitive: false), (m) => m[1]!);
    text = text.replaceFirstMapped(RegExp(r'^(\\S+)\\s+al\\s+', caseSensitive: false), (m) => '${m[1]} el ');
    return text.replaceAll(RegExp(r'\\s+'), ' ').trim();
  }

  /// true si el mensaje empieza por un verbo de orden sobre los datos (crear, consultar, cambiar, eliminar...).
  /// Todo lo demás (saludos, preguntas, conceptos) es conversación.
  static bool looksLikeOrder(String raw) {
    final words = _plain(orderText(raw)).split(' ');
    return words.isNotEmpty && _orderVerbs.contains(words.first);
  }

  /// true si la persona pide ayuda: su respuesta es un texto exacto (lo que sí entiende), no conversación libre.
  static bool isHelpRequest(String raw) {
    final text = _plain(withoutLeadingGreeting(raw)).replaceFirst(RegExp(r'^(?:muchas\\s+)?gracias\\s+'), '');
    return _helpPhrases.contains(text);
  }

  /// Hechos reales de una entidad para el contexto de la IA: cuántos registros hay y cómo se llaman los primeros.
  static String dataFacts(AssistantEntitySchema schema, List<Map<String, dynamic>> rows, {int maxNames = 12}) {
    final label = plural(schema);
    if (rows.isEmpty) return '- $label: 0 registros.';
    final names = rows.take(maxNames).map((row) => rowTitle(schema, row)).where((title) => title.isNotEmpty).toList();
    final more = rows.length > maxNames ? ' y ${rows.length - maxNames} más' : '';
    final list = names.isEmpty ? '' : ': ${names.join(', ')}$more';
    final noun = rows.length == 1 ? 'registro' : 'registros';
    return '- $label: ${rows.length} $noun$list.';
  }
}
'''
        # Sin _sanitize: ese metodo cambia "¿"/"¡" por "?"/"!" (pensado para YAML) y aqui se necesitan tal cual.
        (base_path / 'lib' / 'assistant' / 'assistant_texts.dart').write_text(
            unicodedata.normalize("NFC", content), encoding="utf-8", newline="\n"
        )

    def _generate_assistant_texts_tests(self, base_path):
        """Genera test/assistant/assistant_texts_test.dart (independiente del esquema: usa AppSchema.entities.first)."""
        content = '''import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/assistant/app_schema.dart';
import 'package:generated_crud_app/assistant/assistant_texts.dart';
import 'package:generated_crud_app/assistant/business_command.dart';
import 'package:generated_crud_app/assistant/command_parser.dart';

void main() {
  final entity = AppSchema.entities.first;
  final plural = AssistantTexts.plural(entity);

  test('a greeting alone gets a friendly reply that names the entities', () {
    for (final greeting in ['hola', '¡Hola!', 'Buenos días', 'buenas tardes', 'hey']) {
      final reply = AssistantTexts.smallTalkReply(greeting);
      expect(reply, isNotNull, reason: greeting);
      expect(reply, contains(plural), reason: greeting);
      expect(reply, isNot(contains('Sin resultados')));
    }
  });

  test('thanks, goodbye, help and "who are you" are answered without running a command', () {
    expect(AssistantTexts.smallTalkReply('muchas gracias'), contains('De nada'));
    expect(AssistantTexts.smallTalkReply('adiós'), contains('Hasta luego'));
    expect(AssistantTexts.smallTalkReply('ayuda'), contains(plural));
    expect(AssistantTexts.smallTalkReply('¿qué puedes hacer?'), contains(plural));
    expect(AssistantTexts.smallTalkReply('hola, ¿cómo estás?'), contains('Muy bien'));
    expect(AssistantTexts.smallTalkReply('¿quién eres?'), contains('asistente'));
  });

  test('a real command is not small talk, with or without a leading greeting', () {
    expect(AssistantTexts.smallTalkReply('lista todos los $plural'), isNull);
    expect(AssistantTexts.smallTalkReply('hola, lista todos los $plural'), isNull);
    expect(AssistantTexts.withoutLeadingGreeting('Hola, lista todos los $plural'), 'lista todos los $plural');
    expect(AssistantTexts.withoutLeadingGreeting('lista todos los $plural'), 'lista todos los $plural');
    expect(AssistantTexts.smallTalkReply('holanda'), isNull);
  });

  test('describeRows speaks plain Spanish for zero, one and many rows', () {
    final empty = AssistantTexts.describeRows(entity, const []);
    expect(empty, contains(plural));
    expect(empty, isNot(contains('resultado')));
    expect(AssistantTexts.describeRows(entity, const [], filtered: true), contains('con esos datos'));

    final pk = entity.pkField.jsonKey;
    final rows = [for (var i = 1; i <= 7; i++) <String, dynamic>{pk: i}];
    final many = AssistantTexts.describeRows(entity, rows);
    expect(many, startsWith('Encontré 7 $plural:'));
    expect(many, contains('y 2 más.'));
    expect(many, isNot(contains('resultado(s)')));
  });

  test('the welcome suggestions are things the assistant understands', () {
    final suggestions = AssistantTexts.suggestions();
    expect(suggestions.first, 'Muéstrame los $plural');
    expect(suggestions, contains('Ayuda'));
    expect(AssistantTexts.smallTalkReply('Ayuda'), isNotNull);
  });

  test('the help examples and the not-understood reply give concrete things to say', () {
    for (final text in [AssistantTexts.help(), AssistantTexts.notUnderstood()]) {
      expect(text, contains('muéstrame los $plural'));
      expect(text, contains('crea'));
    }
  });

  test('asked if it is an AI, the assistant answers the question and tells the truth for each state of the local AI', () {
    const questions = [
      '¿eres una IA?',
      'eres una ia',
      'pero eres una IA si o no??',
      '¿usas inteligencia artificial?',
      '¿tienes IA?',
      '¿eres un robot?',
      '¿con quién hablo?',
      '¿quién eres?',
    ];
    for (final question in questions) {
      for (final state in AssistantAiState.values) {
        expect(AssistantTexts.smallTalkReply(question, ai: state), isNotNull, reason: '$question / $state');
      }
      expect(AssistantTexts.smallTalkReply(question), contains('asistente'), reason: question);
    }

    final none = AssistantTexts.smallTalkReply('¿eres una IA?', ai: AssistantAiState.none)!;
    expect(none, contains('Todavía no uso IA'));
    expect(none, contains('Descargar IA local'));
    expect(none, contains('muéstrame los $plural'));

    final downloading = AssistantTexts.smallTalkReply('¿eres una IA?', ai: AssistantAiState.downloading)!;
    expect(downloading, contains('descargando la IA local'));
    expect(downloading, isNot(contains('Todavía no uso IA')));

    final loading = AssistantTexts.smallTalkReply('¿eres una IA?', ai: AssistantAiState.loading)!;
    expect(loading, contains('preparando la IA local'));

    final ready = AssistantTexts.smallTalkReply('¿eres una IA?', ai: AssistantAiState.ready)!;
    expect(ready, startsWith('Sí'));
    expect(ready, contains('sin internet'));
    expect(ready, isNot(contains('Todavía no uso IA')));
  });

  test('a question about the AI never hijacks a real command', () {
    final noun = AssistantTexts.singular(entity);
    expect(AssistantTexts.smallTalkReply('crea un $noun llamado IA'), isNull);
    expect(AssistantTexts.smallTalkReply('¿tienes un $noun llamado Robot?'), isNull);
    expect(AssistantTexts.smallTalkReply('lista todos los $plural que usas'), isNull);
    expect(AssistantTexts.smallTalkReply('elimina $noun Ejemplo'), isNull);
  });

  test('orders are recognised by their verb and cleaned of politeness and filler words', () {
    final noun = AssistantTexts.singular(entity);
    expect(AssistantTexts.looksLikeOrder('lista todos los $plural'), isTrue);
    expect(AssistantTexts.looksLikeOrder('por favor, crea un $noun llamado Ana'), isTrue);
    expect(AssistantTexts.looksLikeOrder('puedes mostrarme los $plural'), isTrue);
    expect(AssistantTexts.looksLikeOrder('por favor, dame el listado de $plural'), isTrue);
    expect(AssistantTexts.looksLikeOrder('Hola, elimina $noun Ana'), isTrue);
    expect(AssistantTexts.looksLikeOrder('¿qué es un $noun en un sistema de gestión?'), isFalse);
    expect(AssistantTexts.looksLikeOrder('hola'), isFalse);
    expect(AssistantTexts.looksLikeOrder('gracias'), isFalse);
    expect(AssistantTexts.looksLikeOrder(''), isFalse);

    expect(AssistantTexts.orderText('Hola, lista todos los $plural'), 'lista los $plural');
    expect(AssistantTexts.orderText('quiero ver todas las $plural'), 'ver las $plural');
    expect(AssistantTexts.orderText('crea un $noun llamado Ana'), 'crea un $noun Ana');
    expect(AssistantTexts.orderText('agrega un nuevo $noun de nombre Carlos'), 'agrega un $noun Carlos');
    expect(AssistantTexts.orderText('borra al $noun Ana'), 'borra el $noun Ana');
    expect(AssistantTexts.orderText('crea un $noun con nombre Ana y edad 3'), 'crea un $noun con nombre Ana y edad 3');
    expect(AssistantTexts.orderText('  muestra   los $plural  '), 'muestra los $plural');
  });

  test('the rules understand an order given by id and the natural phrasing cleaned by orderText', () {
    final parser = CommandParser();
    final noun = AssistantTexts.singular(entity);
    final key = entity.fields.firstWhere((field) => field.isPrimaryKey);
    final expectedId = key.dartType == 'int' ? 3 : '3';

    final read = parser.parse(AssistantTexts.orderText('muestra el $noun con id 3'));
    expect(read.isSuccess, isTrue, reason: read.error);
    expect(read.command!.action, CommandAction.read);
    expect(read.command!.filters, {key.name: expectedId});

    final delete = parser.parse(AssistantTexts.orderText('borra al $noun número 3'));
    expect(delete.isSuccess, isTrue, reason: delete.error);
    expect(delete.command!.action, CommandAction.delete);
    expect(delete.command!.filters, {key.name: expectedId});

    final all = parser.parse(AssistantTexts.orderText('lista todos los $plural'));
    expect(all.isSuccess, isTrue, reason: all.error);
    expect(all.command!.action, CommandAction.read);
    expect(all.command!.filters, isEmpty);

    final nameField = entity.nameField;
    if (nameField != null) {
      final create = parser.parse(AssistantTexts.orderText('crea un $noun llamado Ana'));
      expect(create.isSuccess, isTrue, reason: create.error);
      expect(create.command!.data, {nameField: 'Ana'});
      final byName = parser.parse(AssistantTexts.orderText('elimina el $noun Ana'));
      expect(byName.command!.filters, {nameField: 'Ana'});
    }
  });

  test('the facts for the AI say how many records exist and name the first ones', () {
    final pk = entity.pkField.jsonKey;
    expect(AssistantTexts.dataFacts(entity, const []), '- $plural: 0 registros.');
    expect(AssistantTexts.dataFacts(entity, [{pk: 1}]), contains('1 registro'));
    final many = AssistantTexts.dataFacts(entity, [for (var i = 1; i <= 15; i++) {pk: i}], maxNames: 3);
    expect(many, contains('15 registros'));
    expect(many, contains('#1'));
    expect(many, contains('y 12 más'));
  });

  test('a help request is recognised so its exact text is kept even when the AI is ready', () {
    expect(AssistantTexts.isHelpRequest('ayuda'), isTrue);
    expect(AssistantTexts.isHelpRequest('Hola, ¿qué puedes hacer?'), isTrue);
    expect(AssistantTexts.isHelpRequest('gracias, ¿qué más puedes hacer?'), isTrue);
    expect(AssistantTexts.isHelpRequest('¿qué más puedes hacer?'), isTrue);
    expect(AssistantTexts.isHelpRequest('¿en qué me puedes ayudar?'), isTrue);
    expect(AssistantTexts.isHelpRequest('hola'), isFalse);
    expect(AssistantTexts.isHelpRequest('lista todos los $plural'), isFalse);
  });
}
'''
        (base_path / 'test' / 'assistant' / 'assistant_texts_test.dart').write_text(
            unicodedata.normalize("NFC", content), encoding="utf-8", newline="\n"
        )

    def _generate_command_router(self, base_path):
        """Genera lib/assistant/command_router.dart (genérico)."""
        content = '''import 'app_schema.dart';
import 'assistant_texts.dart';
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
    return const RouterOutcome(success: true, message: AssistantTexts.deleted);
  }

  Future<RouterOutcome> _executeCreate(
    EntityServiceAdapter adapter,
    AssistantEntitySchema schema,
    BusinessCommand command,
  ) async {
    final jsonData = schema.toJsonKeyed(command.data);
    final created = await adapter.create(jsonData);
    return RouterOutcome(success: true, message: AssistantTexts.created(schema, created), rows: [created]);
  }

  Future<RouterOutcome> _executeRead(
    EntityServiceAdapter adapter,
    AssistantEntitySchema schema,
    BusinessCommand command,
  ) async {
    final all = await adapter.list();
    if (command.filters.isEmpty) {
      return RouterOutcome(success: true, message: AssistantTexts.describeRows(schema, all), rows: all);
    }
    final matches = _matchRows(all, schema, command.filters, exact: false);
    return RouterOutcome(
      success: true,
      message: AssistantTexts.describeRows(schema, matches, filtered: true),
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
      return RouterOutcome(success: false, message: AssistantTexts.notFound(schema));
    }
    if (matches.length > 1) {
      return RouterOutcome(
        success: false,
        message: AssistantTexts.ambiguous(schema, matches.length),
        rows: matches,
      );
    }
    final target = matches.first;
    final pk = target[schema.pkField.jsonKey];
    final merged = Map<String, dynamic>.from(target)..addAll(schema.toJsonKeyed(command.data));
    final updated = await adapter.updateFromMap(pk.toString(), merged);
    return RouterOutcome(success: true, message: AssistantTexts.updated(schema, updated), rows: [updated]);
  }

  Future<RouterOutcome> _resolveDelete(
    EntityServiceAdapter adapter,
    AssistantEntitySchema schema,
    BusinessCommand command,
  ) async {
    final all = await adapter.list();
    final matches = _matchRows(all, schema, command.filters, exact: true);
    if (matches.isEmpty) {
      return RouterOutcome(success: false, message: AssistantTexts.notFound(schema));
    }
    if (matches.length > 1) {
      return RouterOutcome(
        success: false,
        message: AssistantTexts.ambiguous(schema, matches.length),
        rows: matches,
      );
    }
    final target = matches.first;
    final pk = target[schema.pkField.jsonKey].toString();
    return RouterOutcome(
      success: true,
      message: AssistantTexts.confirmDelete(schema),
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
        """Genera lib/assistant/voice_input_controller.dart (generico)."""
        content = '''import 'package:flutter/foundation.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

/// Envoltorio delgado sobre package:speech_to_text. La voz es solo un
/// mecanismo de entrada: lo que se reconoce se entrega al mismo pipeline de
/// CommandParser que usa el texto escrito — nunca se salta la validación.
///
/// Sin internet, iOS solo entiende la voz si el teléfono tiene descargado el
/// dictado del MISMO idioma/región que se le pide; por eso se usa el español
/// del propio teléfono (y no siempre es_ES) y, cuando algo falla, se avisa con
/// una frase clara ([onProblem]) en vez de dejar el micrófono mudo. Este
/// controlador no fuerza ni afirma reconocimiento en el dispositivo.
/// Requiere los permisos de micrófono/reconocimiento de voz nativos (ver la
/// documentación del generador CASE).
///
/// Deliberadamente no se inicializa en Web.
class VoiceInputController {
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _available = false;
  bool _initialized = false;
  String? _localeId;

  /// La pantalla lo usa para mostrar el problema en lenguaje claro. Nunca recibe el código técnico del error.
  void Function(String message)? onProblem;

  bool get isAvailable => _available;
  bool get isListening => _speech.isListening;

  /// Frase clara para un error del reconocimiento de voz.
  @visibleForTesting
  static String friendlyProblem(String errorMsg) {
    switch (errorMsg) {
      case 'error_network':
      case 'error_server':
      case 'error_language_not_supported':
      case 'error_language_unavailable':
        return 'No pude entender tu voz sin conexión. Para usar la voz sin internet, descarga el dictado en español '
            'en tu teléfono (Ajustes > General > Teclado > Dictado). Mientras tanto puedes escribir tu mensaje.';
      case 'error_no_match':
      case 'error_speech_timeout':
        return 'No te escuché bien. Inténtalo de nuevo, un poco más cerca del micrófono.';
      case 'error_permission':
        return 'Falta el permiso del micrófono o del reconocimiento de voz. Actívalo en los Ajustes del teléfono.';
      default:
        return 'No pude usar la voz ahora mismo. Puedes escribir tu mensaje.';
    }
  }

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
        onError: (error) {
          debugPrint('VoiceInputController error: $error');
          onProblem?.call(friendlyProblem(error.errorMsg));
        },
      );
      if (_available) _localeId = await _pickSpanishLocale();
    } catch (error) {
      debugPrint('VoiceInputController initialize failed: $error');
      _available = false;
    }
    _initialized = true;
    return _available;
  }

  /// El español del propio teléfono si lo tiene; si no, el primero disponible entre es_US, es_MX y es_ES.
  Future<String> _pickSpanishLocale() async {
    try {
      final system = await _speech.systemLocale();
      final systemId = system?.localeId ?? '';
      if (systemId.toLowerCase().startsWith('es')) return systemId;
      final locales = await _speech.locales();
      for (final preferred in const ['es_US', 'es_MX', 'es_ES']) {
        for (final locale in locales) {
          if (locale.localeId.replaceAll('-', '_') == preferred) return locale.localeId;
        }
      }
      for (final locale in locales) {
        if (locale.localeId.toLowerCase().startsWith('es')) return locale.localeId;
      }
    } catch (error) {
      debugPrint('VoiceInputController locale lookup failed: $error');
    }
    return 'es_ES';
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
        listenOptions: stt.SpeechListenOptions(localeId: _localeId ?? 'es_ES'),
      );
    } catch (error) {
      debugPrint('VoiceInputController listen failed: $error');
      onProblem?.call(friendlyProblem('error_unknown'));
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

    def _generate_voice_tests(self, base_path):
        """Genera test/assistant/voice_input_controller_test.dart."""
        content = '''import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/assistant/voice_input_controller.dart';

void main() {
  test('network and language errors explain how to use the voice without internet', () {
    for (final code in ['error_network', 'error_server', 'error_language_not_supported']) {
      final message = VoiceInputController.friendlyProblem(code);
      expect(message, contains('sin internet'), reason: code);
      expect(message, contains('Dictado'), reason: code);
    }
  });

  test('other errors get a short plain explanation, never the technical code', () {
    expect(VoiceInputController.friendlyProblem('error_no_match'), contains('Inténtalo de nuevo'));
    expect(VoiceInputController.friendlyProblem('error_permission'), contains('permiso'));
    final unknown = VoiceInputController.friendlyProblem('error_algo_raro');
    expect(unknown, isNot(contains('error_')));
    expect(unknown, contains('escribir'));
  });
}
'''
        (base_path / 'test' / 'assistant' / 'voice_input_controller_test.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_model_downloader(self, base_path):
        """Genera lib/assistant/model_downloader.dart: descarga unica del modelo de IA local, solo por accion explicita."""
        content = '''import 'dart:async';
import 'dart:io';

/// La persona cancelo la descarga: no es un error.
class ModelDownloadCancelled implements Exception {
  const ModelDownloadCancelled();

  @override
  String toString() => 'Descarga cancelada';
}

/// Lo que el gestor del modelo necesita de un descargador (en las pruebas se usa uno falso).
abstract interface class ModelFetcher {
  Future<void> download({
    required Uri url,
    required File destination,
    required void Function(int received, int total) onProgress,
    int? minBytes,
  });

  void cancel();
}

/// Descarga un archivo grande (el modelo .gguf) a un archivo propio de la app. Solo se usa cuando la persona lo pide
/// y lo confirma: la app no descarga nada por su cuenta. Escribe en "<destino>.part" y lo renombra al terminar, asi
/// nunca queda un modelo a medias con el nombre final.
class ModelDownloader implements ModelFetcher {
  /// Qwen2.5-1.5B-Instruct (licencia Apache-2.0), cuantizado Q4_K_M: unos 1,1 GB (1.117.320.736 bytes). Es el menor
  /// que conversa bien en español; el 0,5B de versiones anteriores solo servia para interpretar ordenes.
  static const String defaultUrl =
      'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf';
  static const String defaultFileName = 'qwen2.5-1.5b-instruct-q4_k_m.gguf';

  /// Un modelo real pesa cientos de MB: algo mas pequeno es una pagina de error, no un modelo.
  static const int defaultMinBytes = 500 * 1024 * 1024;

  ModelDownloader({HttpClient Function()? clientFactory}) : _clientFactory = clientFactory ?? HttpClient.new;

  final HttpClient Function() _clientFactory;
  HttpClient? _client;
  bool _cancelled = false;

  @override
  void cancel() {
    _cancelled = true;
    _client?.close(force: true);
  }

  @override
  Future<void> download({
    required Uri url,
    required File destination,
    required void Function(int received, int total) onProgress,
    int? minBytes,
  }) async {
    final part = File('${destination.path}.part');
    final client = _clientFactory();
    _client = client;
    IOSink? sink;
    try {
      if (await part.exists()) await part.delete();
      final request = await client.getUrl(url);
      final response = await request.close();
      if (response.statusCode != HttpStatus.ok) {
        await response.drain<void>();
        throw HttpException('El servidor respondio ${response.statusCode}', uri: url);
      }
      final total = response.contentLength; // -1 si el servidor no lo dice
      sink = part.openWrite();
      var received = 0;
      await for (final chunk in response) {
        if (_cancelled) throw const ModelDownloadCancelled();
        sink.add(chunk);
        received += chunk.length;
        onProgress(received, total);
      }
      await sink.flush();
      await sink.close();
      sink = null;
      if (total > 0 && received != total) {
        throw HttpException('La descarga quedo incompleta ($received de $total bytes)', uri: url);
      }
      if (received < (minBytes ?? defaultMinBytes)) {
        throw HttpException('El archivo descargado es demasiado pequeno para ser un modelo', uri: url);
      }
      if (await destination.exists()) await destination.delete();
      await part.rename(destination.path);
    } catch (error) {
      try {
        await sink?.close();
      } catch (_) {}
      if (await part.exists()) await part.delete();
      if (_cancelled) throw const ModelDownloadCancelled();
      rethrow;
    } finally {
      client.close(force: true);
      _client = null;
    }
  }
}
'''
        (base_path / 'lib' / 'assistant' / 'model_downloader.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_model_download_tests(self, base_path):
        """Genera test/assistant/model_download_test.dart (descargador con un servidor local + gestor con uno falso) y
        test/assistant/assistant_download_view_test.dart (la pantalla). Van en archivos distintos: testWidgets instala
        un HttpOverrides que rechaza toda conexion y arruinaria las pruebas del descargador."""
        content = '''import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/assistant/local_model_manager.dart';
import 'package:generated_crud_app/assistant/model_downloader.dart';
import 'package:llamadart/llamadart.dart';

class _FakeEngine implements LocalModelEngineHandle {
  int loadCalls = 0;

  @override
  LlamaEngine? get engine => null;

  @override
  Future<void> loadModel(String path, {ModelParams? modelParams}) async => loadCalls++;

  @override
  Future<void> dispose() async {}
}

class _FakeFetcher implements ModelFetcher {
  _FakeFetcher({this.error, this.gate});

  final Object? error;
  final Completer<void>? gate;
  bool cancelled = false;
  int downloadCalls = 0;
  Uri? requestedUrl;

  @override
  Future<void> download({
    required Uri url,
    required File destination,
    required void Function(int received, int total) onProgress,
    int? minBytes,
  }) async {
    downloadCalls++;
    requestedUrl = url;
    onProgress(50, 100);
    if (gate != null) await gate!.future;
    if (cancelled) throw const ModelDownloadCancelled();
    if (error != null) throw error!;
    await destination.writeAsBytes([1, 2, 3]);
    onProgress(100, 100);
  }

  @override
  void cancel() => cancelled = true;
}

void main() {
  late Directory directory;

  setUp(() async {
    directory = await Directory.systemTemp.createTemp('model-download-');
  });

  tearDown(() async {
    if (await directory.exists()) await directory.delete(recursive: true);
  });

  Future<HttpServer> serve(Future<void> Function(HttpRequest request) handler) async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen(handler);
    addTearDown(() => server.close(force: true));
    return server;
  }

  Uri urlOf(HttpServer server) => Uri.parse('http://127.0.0.1:${server.port}/modelo.gguf');

  group('ModelDownloader', () {
    test('downloads to a .part file, reports progress and renames it when it ends', () async {
      final bytes = List<int>.generate(300000, (i) => i % 251);
      final server = await serve((request) async {
        request.response.contentLength = bytes.length;
        request.response.add(bytes);
        await request.response.close();
      });
      final destination = File('${directory.path}/model.gguf');
      final received = <int>[];

      await ModelDownloader().download(
        url: urlOf(server),
        destination: destination,
        minBytes: 1000,
        onProgress: (r, total) {
          expect(total, bytes.length);
          received.add(r);
        },
      );

      expect(await destination.readAsBytes(), bytes);
      expect(File('${destination.path}.part').existsSync(), isFalse);
      expect(received.last, bytes.length);
      expect(received, orderedEquals([...received]..sort()));
    });

    test('rejects an error answer and leaves no file behind', () async {
      final server = await serve((request) async {
        request.response.statusCode = HttpStatus.notFound;
        await request.response.close();
      });
      final destination = File('${directory.path}/model.gguf');

      await expectLater(
        ModelDownloader().download(url: urlOf(server), destination: destination, minBytes: 1, onProgress: (_, __) {}),
        throwsA(isA<HttpException>()),
      );
      expect(destination.existsSync(), isFalse);
      expect(File('${destination.path}.part').existsSync(), isFalse);
    });

    test('rejects a download that is cut short and leaves no half model', () async {
      final server = await serve((request) async {
        request.response.contentLength = 100000;
        request.response.add(List<int>.filled(20000, 7));
        try {
          await request.response.close();
        } catch (_) {}
      });
      final destination = File('${directory.path}/model.gguf');

      await expectLater(
        ModelDownloader().download(url: urlOf(server), destination: destination, minBytes: 1, onProgress: (_, __) {}),
        throwsA(isA<Exception>()),
      );
      expect(destination.existsSync(), isFalse);
      expect(File('${destination.path}.part').existsSync(), isFalse);
    });

    test('refuses a file too small to be a model (an error page saved as .gguf)', () async {
      final server = await serve((request) async {
        request.response.contentLength = 5000;
        request.response.add(List<int>.filled(5000, 1));
        await request.response.close();
      });
      final destination = File('${directory.path}/model.gguf');

      await expectLater(
        ModelDownloader().download(url: urlOf(server), destination: destination, onProgress: (_, __) {}),
        throwsA(predicate((e) => e is HttpException && e.message.contains('demasiado pequeno'))),
      );
      expect(destination.existsSync(), isFalse);
    });

    test('cancel stops the download, reports it as cancelled and leaves no file', () async {
      final server = await serve((request) async {
        request.response.contentLength = 60 * 10000;
        for (var i = 0; i < 60; i++) {
          try {
            request.response.add(List<int>.filled(10000, 3));
            await request.response.flush();
          } catch (_) {
            return;
          }
          await Future<void>.delayed(const Duration(milliseconds: 20));
        }
        await request.response.close();
      });
      final destination = File('${directory.path}/model.gguf');
      final downloader = ModelDownloader();

      await expectLater(
        downloader.download(
          url: urlOf(server),
          destination: destination,
          minBytes: 1,
          onProgress: (received, _) {
            if (received > 0) downloader.cancel();
          },
        ),
        throwsA(isA<ModelDownloadCancelled>()),
      );
      expect(destination.existsSync(), isFalse);
      expect(File('${destination.path}.part').existsSync(), isFalse);
    });
  });

  group('LocalModelManager download', () {
    LocalModelManager managerWith(_FakeFetcher fetcher, _FakeEngine engine) => LocalModelManager(
          engineFactory: () => engine,
          modelDirectoryProvider: () async => directory,
          downloaderFactory: () => fetcher,
        );

    test('downloading saves the model, remembers its name and loads it', () async {
      final fetcher = _FakeFetcher();
      final engine = _FakeEngine();
      final manager = managerWith(fetcher, engine);
      final seenProgress = <double?>[];
      var wasDownloading = false;
      manager.addListener(() {
        wasDownloading = wasDownloading || manager.isDownloading;
        seenProgress.add(manager.downloadProgress);
      });

      await manager.downloadDefaultModel();

      expect(fetcher.requestedUrl.toString(), ModelDownloader.defaultUrl);
      expect(wasDownloading, isTrue);
      expect(seenProgress, contains(0.5));
      expect(manager.isDownloading, isFalse);
      expect(manager.state, LocalModelState.ready);
      expect(manager.modelFileNameLabel, ModelDownloader.defaultFileName);
      expect(engine.loadCalls, 1);
      expect(await File('${directory.path}/local_model.gguf').readAsBytes(), [1, 2, 3]);
      expect(await File('${directory.path}/local_model.meta').readAsString(), ModelDownloader.defaultFileName);
    });

    test('a failed download ends in error with a plain message, never the technical one', () async {
      final fetcher = _FakeFetcher(error: const SocketException('Failed host lookup'));
      final engine = _FakeEngine();
      final manager = managerWith(fetcher, engine);

      await manager.downloadDefaultModel();

      expect(manager.isDownloading, isFalse);
      expect(manager.state, LocalModelState.error);
      expect(manager.downloadError, contains('Revisa tu conexión'));
      expect(manager.downloadError, isNot(contains('SocketException')));
      expect(engine.loadCalls, 0);
      expect(File('${directory.path}/local_model.gguf').existsSync(), isFalse);
    });

    test('a failed upgrade keeps the model that already works instead of leaving the assistant without AI', () async {
      await File('${directory.path}/local_model.gguf').writeAsBytes([9, 9, 9]);
      await File('${directory.path}/local_model.meta').writeAsString('qwen2.5-0.5b-instruct-q4_k_m.gguf');
      final fetcher = _FakeFetcher(error: const SocketException('Failed host lookup'));
      final manager = managerWith(fetcher, _FakeEngine());
      await manager.initialize();
      expect(manager.state, LocalModelState.ready);

      await manager.downloadDefaultModel();

      expect(manager.state, LocalModelState.ready);
      expect(manager.downloadError, contains('Revisa tu conexión'));
      expect(manager.modelFileNameLabel, 'qwen2.5-0.5b-instruct-q4_k_m.gguf');
      expect(await File('${directory.path}/local_model.gguf').readAsBytes(), [9, 9, 9]);
    });

    test('a cancelled download leaves everything as it was, without an error', () async {
      final gate = Completer<void>();
      final fetcher = _FakeFetcher(gate: gate);
      final manager = managerWith(fetcher, _FakeEngine());

      final running = manager.downloadDefaultModel();
      while (fetcher.downloadCalls == 0) {
        await Future<void>.delayed(Duration.zero);
      }
      expect(manager.isDownloading, isTrue);
      manager.cancelDownload();
      gate.complete();
      await running;

      expect(manager.isDownloading, isFalse);
      expect(manager.state, LocalModelState.notConfigured);
      expect(manager.downloadError, isNull);
    });

    test('asking twice while one download runs starts only one', () async {
      final gate = Completer<void>();
      final fetcher = _FakeFetcher(gate: gate);
      final manager = managerWith(fetcher, _FakeEngine());

      final first = manager.downloadDefaultModel();
      final second = manager.downloadDefaultModel();
      while (fetcher.downloadCalls == 0) {
        await Future<void>.delayed(Duration.zero);
      }
      gate.complete();
      await Future.wait([first, second]);

      expect(fetcher.downloadCalls, 1);
    });
  });
}
'''
        (base_path / 'test' / 'assistant' / 'model_download_test.dart').write_text(
            unicodedata.normalize("NFC", content), encoding="utf-8", newline="\n"
        )

        view_content = '''import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/assistant/assistant_view.dart';
import 'package:generated_crud_app/assistant/local_llm_chat.dart';
import 'package:generated_crud_app/assistant/local_model_manager.dart';
import 'package:generated_crud_app/assistant/model_downloader.dart';
import 'package:llamadart/llamadart.dart';

class _FakeEngine implements LocalModelEngineHandle {
  @override
  LlamaEngine? get engine => null;

  @override
  Future<void> loadModel(String path, {ModelParams? modelParams}) async {}

  @override
  Future<void> dispose() async {}
}

class _FakeFetcher implements ModelFetcher {
  int downloadCalls = 0;

  @override
  Future<void> download({
    required Uri url,
    required File destination,
    required void Function(int received, int total) onProgress,
    int? minBytes,
  }) async {
    downloadCalls++;
    await destination.writeAsBytes([1, 2, 3]);
  }

  @override
  void cancel() {}
}

class _PendingFetcher implements ModelFetcher {
  final Completer<void> finish = Completer<void>();

  @override
  Future<void> download({
    required Uri url,
    required File destination,
    required void Function(int received, int total) onProgress,
    int? minBytes,
  }) async {
    onProgress(1, 2);
    await finish.future;
    await destination.writeAsBytes([1, 2, 3]);
  }

  @override
  void cancel() {}
}

void main() {
  testWidgets('asked if it is an AI, the assistant tells the truth: no model, downloading, ready', (tester) async {
    final directory = (await tester.runAsync(() => Directory.systemTemp.createTemp('assistant-ai-truth-')))!;
    addTearDown(() => directory.deleteSync(recursive: true));
    final fetcher = _PendingFetcher();
    final manager = LocalModelManager(
      engineFactory: _FakeEngine.new,
      modelDirectoryProvider: () async => directory,
      downloaderFactory: () => fetcher,
    );

    final chat = LocalLlmChat(
      manager,
      inferenceOverride: (system, turns) async => 'Sí, soy una IA que corre en tu teléfono.',
    );
    await tester.pumpWidget(MaterialApp(home: AssistantView(modelManagerFactory: () => manager, chat: chat)));
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 100)));
    await tester.pump();

    Future<void> ask(String text) async {
      await tester.enterText(find.byType(TextField), text);
      await tester.tap(find.byIcon(Icons.send));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
    }

    // 1) sin modelo: dice que todavia no usa IA
    await ask('¿eres una IA?');
    expect(find.textContaining('Todavía no uso IA'), findsOneWidget);

    // 2) descargando: dice que la esta descargando
    await tester.tap(find.text('Descargar IA local'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Descargar'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(manager.isDownloading, isTrue);
    await ask('pero eres una IA si o no??');
    expect(find.textContaining('Estoy descargando la IA local'), findsOneWidget);

    // 3) lista: ahora conversa el modelo (aqui, una inferencia falsa) y la respuesta lleva la etiqueta de IA
    fetcher.finish.complete();
    for (var i = 0; i < 40 && manager.state != LocalModelState.ready; i++) {
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await tester.pump();
    }
    expect(manager.state, LocalModelState.ready);
    await ask('¿usas inteligencia artificial?');
    expect(find.text('Sí, soy una IA que corre en tu teléfono.'), findsOneWidget);
    expect(find.text('IA local'), findsOneWidget);
  });

  testWidgets('offers to download the local AI, asks first, and downloads only when confirmed', (tester) async {
    final directory = (await tester.runAsync(() => Directory.systemTemp.createTemp('assistant-download-')))!;
    addTearDown(() => directory.deleteSync(recursive: true));
    final fetcher = _FakeFetcher();
    final manager = LocalModelManager(
      engineFactory: _FakeEngine.new,
      modelDirectoryProvider: () async => directory,
      downloaderFactory: () => fetcher,
    );

    await tester.pumpWidget(MaterialApp(home: AssistantView(modelManagerFactory: () => manager)));
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 100)));
    await tester.pump();

    expect(find.text('Descargar IA local'), findsOneWidget);
    expect(find.text('Elegir modelo'), findsOneWidget);

    // 1) se cancela en la confirmacion: no se descarga nada
    await tester.tap(find.text('Descargar IA local'));
    await tester.pumpAndSettle();
    expect(find.text('Descargar la IA local'), findsOneWidget);
    await tester.tap(find.text('Cancelar'));
    await tester.pumpAndSettle();
    expect(fetcher.downloadCalls, 0);

    // 2) se confirma: se descarga y el modelo queda listo
    await tester.tap(find.text('Descargar IA local'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Descargar'));
    await tester.pump();
    for (var i = 0; i < 40 && manager.state != LocalModelState.ready; i++) {
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await tester.pump();
    }

    expect(fetcher.downloadCalls, 1);
    expect(manager.state, LocalModelState.ready);
    expect(find.text('IA local lista'), findsOneWidget);
    expect(find.text('Descargar IA local'), findsNothing);
  });
}
'''
        (base_path / 'test' / 'assistant' / 'assistant_download_view_test.dart').write_text(
            unicodedata.normalize("NFC", view_content), encoding="utf-8", newline="\n"
        )

    def _generate_local_model_manager(self, base_path):
        """Genera lib/assistant/local_model_manager.dart (generico): gestiona
        la seleccion, copia a almacenamiento propio de la app, persistencia y
        carga/descarga de un modelo GGUF local. No empaqueta ningun modelo
        con la app ni lo descarga automaticamente: la persona lo descarga
        con una accion explicita (downloadDefaultModel, con confirmacion) o
        importa un .gguf (selectAndImportModel). La red solo se usa en
        ModelDownloader."""
        content = '''import 'dart:async';
import 'dart:io';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/foundation.dart';
import 'package:llamadart/llamadart.dart';
import 'package:path_provider/path_provider.dart';

import 'model_downloader.dart';

/// Estado del ciclo de vida del modelo local.
enum LocalModelState { notConfigured, loading, ready, error }

/// Small injectable lifecycle boundary. Production wraps a real
/// [LlamaEngine]; generated tests use a fake without loading a GGUF.
abstract class LocalModelEngineHandle {
  LlamaEngine? get engine;
  Future<void> loadModel(String path, {ModelParams? modelParams});
  Future<void> dispose();
}

class _LlamaModelEngineHandle implements LocalModelEngineHandle {
  _LlamaModelEngineHandle() : _engine = LlamaEngine(LlamaBackend());

  final LlamaEngine _engine;

  @override
  LlamaEngine get engine => _engine;

  @override
  Future<void> loadModel(String path, {ModelParams? modelParams}) {
    return modelParams == null
        ? _engine.loadModel(path)
        : _engine.loadModel(path, modelParams: modelParams);
  }

  @override
  Future<void> dispose() => _engine.dispose();
}

typedef LocalModelEngineFactory = LocalModelEngineHandle Function();
typedef LocalModelDirectoryProvider = Future<Directory> Function();

/// Administra un modelo GGUF local: seleccion (file_selector), copia a
/// almacenamiento propio de la app (path_provider, no un directorio
/// temporal, para que persista entre reinicios), metadata minima (nombre de
/// archivo original), y el ciclo de vida de carga/descarga del motor de
/// inferencia (llamadart). Solo descarga un modelo cuando la persona lo pide (downloadDefaultModel) y nunca incluye uno
/// empaquetado: [selectAndImportModel] es la unica forma de configurar un
/// modelo, y siempre requiere una accion explicita del usuario/desarrollador
/// eligiendo un archivo .gguf local.
class LocalModelManager extends ChangeNotifier {
  static const _modelFileName = 'local_model.gguf';
  static const _metaFileName = 'local_model.meta';

  LocalModelManager({
    LocalModelEngineFactory? engineFactory,
    LocalModelDirectoryProvider? modelDirectoryProvider,
    ModelFetcher Function()? downloaderFactory,
  })  : _engineFactory = engineFactory ?? _LlamaModelEngineHandle.new,
        _modelDirectoryProvider =
            modelDirectoryProvider ?? getApplicationSupportDirectory,
        _downloaderFactory = downloaderFactory ?? ModelDownloader.new;

  final LocalModelEngineFactory _engineFactory;
  final LocalModelDirectoryProvider _modelDirectoryProvider;
  final ModelFetcher Function() _downloaderFactory;

  ModelFetcher? _activeDownload;
  bool _isDownloading = false;
  double? _downloadProgress;
  String? _downloadError;

  /// true mientras se descarga el modelo (accion explicita de la persona).
  bool get isDownloading => _isDownloading;

  /// Avance de la descarga entre 0 y 1; null si el servidor no dijo el tamano.
  double? get downloadProgress => _downloadProgress;

  /// Frase clara si la ultima descarga fallo (nunca el error tecnico).
  String? get downloadError => _downloadError;

  LocalModelState _state = LocalModelState.notConfigured;
  String? _modelFileNameLabel;
  String? _errorMessage;
  LocalModelEngineHandle? _engine;
  Future<void>? _activeLoad;
  bool _disposed = false;

  LocalModelState get state => _state;
  String? get modelFileNameLabel => _modelFileNameLabel;
  String? get errorMessage => _errorMessage;

  /// Motor listo para inferencia. Solo no nulo cuando [state] es
  /// [LocalModelState.ready] — cualquier otro estado devuelve null, para que
  /// un llamador nunca use por accidente un motor a medio cargar o
  /// descargado.
  LlamaEngine? get engine =>
      _state == LocalModelState.ready ? _engine?.engine : null;

  Future<Directory> _modelDirectory() => _modelDirectoryProvider();

  void _notifyListeners() {
    if (!_disposed) notifyListeners();
  }

  Future<File> _modelFile() async {
    final dir = await _modelDirectory();
    return File('${dir.path}/$_modelFileName');
  }

  Future<File> _metaFile() async {
    final dir = await _modelDirectory();
    return File('${dir.path}/$_metaFileName');
  }

  /// Se llama una vez al iniciar la app (ver AssistantView.initState). Si ya
  /// hay un modelo previamente importado en almacenamiento propio de la
  /// app, lo carga automaticamente para no exigir una nueva seleccion en
  /// cada arranque. Un fallo aqui deja [state] en
  /// [LocalModelState.error]/[LocalModelState.notConfigured]: el asistente
  /// sigue funcionando por completo via el parser determinista.
  Future<void> initialize() async {
    try {
      final modelFile = await _modelFile();
      if (!await modelFile.exists()) {
        _state = LocalModelState.notConfigured;
        _notifyListeners();
        return;
      }
      final metaFile = await _metaFile();
      _modelFileNameLabel =
          await metaFile.exists() ? (await metaFile.readAsString()).trim() : _modelFileName;
      await loadModel();
    } catch (error) {
      _state = LocalModelState.error;
      _errorMessage = 'No se pudo inicializar el modelo local: $error';
      _notifyListeners();
    }
  }

  /// Abre un selector de archivos nativo para elegir un .gguf, lo copia a
  /// almacenamiento propio de la app y lo carga. Cualquier fallo (usuario
  /// cancela, archivo invalido, error de carga) deja [state] en
  /// [LocalModelState.error] sin lanzar una excepcion no controlada.
  Future<void> selectAndImportModel() async {
    try {
      // iOS's file_selector_ios requires a non-empty uniformTypeIdentifiers
      // list (extensions alone are not enough on iOS, unlike other
      // platforms); 'public.data' is the closest system UTI for an
      // unregistered custom extension like .gguf, and extensions is kept so
      // non-iOS platforms still filter by it.
      const typeGroup = XTypeGroup(
        label: 'GGUF',
        extensions: ['gguf'],
        uniformTypeIdentifiers: ['public.data'],
      );
      final picked = await openFile(acceptedTypeGroups: [typeGroup]);
      if (picked == null) {
        return;
      }

      _state = LocalModelState.loading;
      _errorMessage = null;
      _notifyListeners();

      await unloadModel();

      final sourceBytes = await picked.readAsBytes();
      final destination = await _modelFile();
      await destination.writeAsBytes(sourceBytes, flush: true);

      _modelFileNameLabel = picked.name;
      final metaFile = await _metaFile();
      await metaFile.writeAsString(picked.name, flush: true);

      await loadModel();
    } catch (error) {
      _state = LocalModelState.error;
      _errorMessage = 'No se pudo importar el modelo: $error';
      _notifyListeners();
    }
  }

  /// Descarga el modelo por defecto (Qwen2.5-1.5B, ~1,1 GB) a almacenamiento propio de la app y lo carga. Solo se
  /// llama por una accion explicita de la persona (la pantalla pide confirmacion antes). Si se cancela, todo queda como
  /// estaba y sin error; si falla, [state] pasa a error con [downloadError] en lenguaje claro.
  Future<void> downloadDefaultModel() async {
    if (_isDownloading || _disposed) return;
    _isDownloading = true;
    _downloadProgress = 0;
    _downloadError = null;
    _errorMessage = null;
    _notifyListeners();
    final fetcher = _downloaderFactory();
    _activeDownload = fetcher;
    var downloaded = false;
    try {
      final destination = await _modelFile();
      await fetcher.download(
        url: Uri.parse(ModelDownloader.defaultUrl),
        destination: destination,
        onProgress: (received, total) {
          _downloadProgress = total > 0 ? received / total : null;
          _notifyListeners();
        },
      );
      downloaded = true;
    } on ModelDownloadCancelled {
      // la persona cancelo: queda como estaba, sin error
    } catch (error) {
      _downloadError = 'No se pudo descargar la IA local. Revisa tu conexión e inténtalo de nuevo.';
      _errorMessage = 'Descarga fallida: $error';
      // Quien ya tiene un modelo que funciona (actualizando al nuevo) no se queda sin IA por una descarga fallida.
      if (_state != LocalModelState.ready) _state = LocalModelState.error;
    } finally {
      _isDownloading = false;
      _downloadProgress = null;
      _activeDownload = null;
      _notifyListeners();
    }
    if (!downloaded || _disposed) return;
    _modelFileNameLabel = ModelDownloader.defaultFileName;
    try {
      await (await _metaFile()).writeAsString(ModelDownloader.defaultFileName, flush: true);
    } catch (_) {}
    await loadModel();
  }

  /// Cancela la descarga en curso, si la hay.
  void cancelDownload() => _activeDownload?.cancel();

  /// Carga el modelo ya copiado en almacenamiento propio de la app. No hace
  /// ninguna llamada de red: solo lee el archivo local.
  Future<void> loadModel() {
    final active = _activeLoad;
    if (active != null) return active;

    final operation = _loadModelOnce();
    _activeLoad = operation;
    return operation.whenComplete(() {
      if (identical(_activeLoad, operation)) _activeLoad = null;
    });
  }

  Future<void> _loadModelOnce() async {
    try {
      _state = LocalModelState.loading;
      _errorMessage = null;
      _notifyListeners();

      final modelFile = await _modelFile();
      if (!await modelFile.exists()) {
        _state = LocalModelState.notConfigured;
        _notifyListeners();
        return;
      }

      await _disposeCurrentEngine();

      Object? primaryError;
      try {
        await _loadCandidate(modelFile.path);
      } catch (error) {
        primaryError = error;
      }

      if (primaryError != null) {
        try {
          await _loadCandidate(
            modelFile.path,
            modelParams: const ModelParams(
              preferredBackend: GpuBackend.cpu,
            ),
          );
        } catch (fallbackError) {
          _state = LocalModelState.error;
          _errorMessage =
              'No se pudo cargar el modelo: $fallbackError';
          _notifyListeners();
          return;
        }
      }

      _state = LocalModelState.ready;
      _notifyListeners();
    } catch (error) {
      await _disposeCurrentEngine();
      _state = LocalModelState.error;
      _errorMessage = 'No se pudo cargar el modelo: $error';
      _notifyListeners();
    }
  }

  Future<void> _loadCandidate(
    String path, {
    ModelParams? modelParams,
  }) async {
    LocalModelEngineHandle? candidate;
    try {
      candidate = _engineFactory();
      _engine = candidate;
      await candidate.loadModel(path, modelParams: modelParams);
    } catch (_) {
      if (identical(_engine, candidate)) _engine = null;
      if (candidate != null) {
        try {
          await candidate.dispose();
        } catch (_) {
          // The failed candidate is detached even if native cleanup reports.
        }
      }
      rethrow;
    }
  }

  Future<void> _disposeCurrentEngine() async {
    final engine = _engine;
    _engine = null;
    if (engine == null) return;
    try {
      await engine.dispose();
    } catch (_) {
      // The manager must drop failed native resources even if cleanup reports.
    }
  }

  Future<void> unloadModel() async {
    final active = _activeLoad;
    if (active != null) {
      try {
        await active;
      } catch (_) {
        // The load path owns its error state and candidate cleanup.
      }
    }
    await _disposeCurrentEngine();
  }

  @override
  void dispose() {
    if (_disposed) return;
    _disposed = true;
    _activeDownload?.cancel();
    unawaited(unloadModel());
    super.dispose();
  }
}
'''
        (base_path / 'lib' / 'assistant' / 'local_model_manager.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_local_llm_chat(self, base_path):
        """Genera lib/assistant/local_llm_chat.dart: conversación en lenguaje natural con el modelo local, especializada
        en sistemas de gestión (prompt armado con AppSchema en tiempo de ejecución: el archivo es idéntico para cualquier
        esquema)."""
        content = '''import 'dart:async';

import 'package:llamadart/llamadart.dart';

import 'app_schema.dart';
import 'assistant_texts.dart';
import 'local_model_manager.dart';

/// Un turno de la conversación: lo que dijo la persona o lo que respondió el asistente.
class ChatTurn {
  final String text;
  final bool isUser;
  const ChatTurn(this.text, {required this.isUser});
}

/// Inferencia de texto libre: recibe el prompt de sistema y los turnos y devuelve la respuesta. Inyectable en pruebas.
typedef LocalLlmChatInference = Future<String> Function(String systemPrompt, List<ChatTurn> turns);

/// Conversación en lenguaje natural con el modelo local, especializada en sistemas de gestión.
///
/// El modelo recibe un prompt de sistema armado en tiempo de ejecución con lo que la app realmente tiene (nombre,
/// entidades y campos del esquema, lo que sí y lo que no puede hacer) y, cuando la pregunta nombra una entidad, los
/// datos reales (cuántos registros hay y cómo se llaman). Así conversa sin inventar capacidades ni datos. Este archivo
/// nunca nombra una entidad ni un campo de un proyecto concreto.
///
/// Las órdenes sobre los datos (crear, cambiar, eliminar, consultar) NO pasan por aquí: siguen por el camino seguro
/// (extractor + validador + router). Esta clase solo conversa. [reply] devuelve null si no hay modelo listo, si falla,
/// si tarda más del tiempo permitido o si no dice nada; el llamador entonces usa los textos fijos de siempre.
class LocalLlmChat {
  LocalLlmChat(
    this.modelManager, {
    LocalLlmChatInference? inferenceOverride,
    this.timeout = const Duration(seconds: 40),
    this.maxTurns = 8,
  }) : _inferenceOverride = inferenceOverride;

  final LocalModelManager modelManager;
  final LocalLlmChatInference? _inferenceOverride;
  final Duration timeout;

  /// Cuántos turnos recientes se recuerdan (el prompt se mantiene pequeño: el modelo corre en el teléfono).
  final int maxTurns;

  final List<ChatTurn> _history = [];

  List<ChatTurn> get history => List.unmodifiable(_history);

  /// Anota un intercambio que no pasó por el modelo (por ejemplo, el resultado de una orden) para dar contexto.
  void remember(String userText, String assistantText) => _add(userText, assistantText);

  void clear() => _history.clear();

  void _add(String userText, String assistantText) {
    _history
      ..add(ChatTurn(userText, isUser: true))
      ..add(ChatTurn(assistantText, isUser: false));
    while (_history.length > maxTurns) {
      _history.removeAt(0);
    }
  }

  /// Respuesta del modelo a [userText]. [dataContext] son hechos reales de los datos de la app (ver
  /// [AssistantTexts.dataFacts]). Devuelve null si no se pudo conversar (sin modelo, error, tiempo agotado o vacío).
  Future<String?> reply(String userText, {String dataContext = ''}) async {
    final text = userText.trim();
    if (text.isEmpty) return null;
    final override = _inferenceOverride;
    if (override == null && modelManager.state != LocalModelState.ready) return null;
    final turns = [..._history, ChatTurn(text, isUser: true)];
    try {
      final run = override ?? _runRealInference;
      final raw = await run(systemPrompt(dataContext: dataContext), turns).timeout(timeout);
      final answer = clean(raw);
      if (answer.isEmpty) return null;
      _add(text, answer);
      return answer;
    } catch (_) {
      return null;
    }
  }

  /// Quita espacios, una etiqueta de hablante al inicio ("Asistente: ...") y saltos de línea de más.
  static String clean(String raw) {
    var text = raw.trim();
    text = text.replaceFirst(RegExp(r'^(?:asistente|ia|respuesta)\\s*:\\s*', caseSensitive: false), '');
    text = text.replaceAll(RegExp(r'\\n{3,}'), '\\n\\n');
    return text.trim();
  }

  /// Quién es el asistente, qué sabe de esta app, qué puede y qué no puede hacer, y los datos reales de la consulta.
  static String systemPrompt({String dataContext = ''}) {
    final buffer = StringBuffer();
    buffer.writeln(
      'Eres el asistente de la aplicación «${AppSchema.appName}», un sistema de gestión. '
      'Hablas en español, de forma clara, amable y breve (máximo 3 frases). '
      'Conoces los sistemas de gestión en general (contabilidad, inventario, ventas, personal, escolares...) '
      'y explicas sus conceptos con sencillez.',
    );
    buffer.writeln('Los datos de esta aplicación son: ${_entitiesDescription()}.');
    buffer.writeln(
      'Lo que SÍ puedes hacer: conversar, explicar conceptos de gestión, guiar a la persona en esta app y responder '
      'usando los datos reales que aparecen abajo. Las órdenes sobre los datos las ejecuta la app cuando la persona '
      'las escribe así: ${_exampleOrders()}.',
    );
    buffer.writeln(
      'Cuando pregunten cómo hacer algo con los datos, responde con la orden exacta que deben escribir '
      '(por ejemplo: ${_exampleOrders()}); no inventes menús, botones ni pantallas.',
    );
    buffer.writeln(
      'Lo que NO puedes hacer: NO puedes buscar en internet, enviar mensajes o correos, programar eventos ni nada '
      'fuera de esta app. Si te lo piden, dilo con claridad.',
    );
    buffer.writeln(
      'No inventes datos ni registros: usa solo los datos reales de abajo; si no los tienes, dilo y sugiere una orden. '
      'Eres una IA local: funcionas dentro del teléfono, sin internet.',
    );
    if (dataContext.trim().isNotEmpty) {
      buffer.writeln('Datos reales ahora mismo:');
      buffer.writeln(dataContext.trim());
    }
    return buffer.toString().trim();
  }

  static String _entitiesDescription() {
    if (AppSchema.entities.isEmpty) return 'ninguno todavía';
    return AppSchema.entities.map((entity) {
      final fields = entity.fields.where((f) => !f.isPrimaryKey).map((f) => f.name).join(', ');
      return fields.isEmpty ? entity.name : '${entity.name} (campos: $fields)';
    }).join('; ');
  }

  static String _exampleOrders() {
    if (AppSchema.entities.isEmpty) return 'consultar, crear, cambiar o eliminar registros';
    return AssistantTexts.suggestions().take(2).map((s) => '«$s»').join(', ');
  }

  Future<String> _runRealInference(String system, List<ChatTurn> turns) async {
    final engine = modelManager.engine;
    if (engine == null) {
      throw StateError('El modelo local no esta listo.');
    }
    final messages = <LlamaChatMessage>[
      LlamaChatMessage.fromText(role: LlamaChatRole.system, text: system),
      for (final turn in turns)
        LlamaChatMessage.fromText(
          role: turn.isUser ? LlamaChatRole.user : LlamaChatRole.assistant,
          text: turn.text,
        ),
    ];
    final buffer = StringBuffer();
    await for (final chunk in engine.create(
      messages,
      params: const GenerationParams(temp: 0.4, maxTokens: 200, penalty: 1.1),
    )) {
      if (chunk.choices.isEmpty) continue;
      final content = chunk.choices.first.delta.content;
      if (content != null) buffer.write(content);
    }
    return buffer.toString();
  }
}
'''
        (base_path / 'lib' / 'assistant' / 'local_llm_chat.dart').write_text(
            unicodedata.normalize("NFC", content), encoding="utf-8", newline="\n"
        )

    def _generate_local_llm_chat_tests(self, base_path):
        """Genera las pruebas del chat (unitarias) y de la pantalla (ruta orden/charla, etiqueta de origen, respaldo)."""
        chat_test = '''import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/assistant/app_schema.dart';
import 'package:generated_crud_app/assistant/assistant_texts.dart';
import 'package:generated_crud_app/assistant/local_llm_chat.dart';
import 'package:generated_crud_app/assistant/local_model_manager.dart';

void main() {
  final plural = AssistantTexts.plural(AppSchema.entities.first);

  test('the system prompt makes it a management assistant that knows the app, its data and its limits', () {
    final prompt = LocalLlmChat.systemPrompt(dataContext: '- $plural: 2 registros: Uno, Dos.');
    expect(prompt, contains(AppSchema.appName));
    expect(prompt, contains('sistema de gestión'));
    expect(prompt, contains('NO puedes buscar en internet'));
    expect(prompt, contains('Eres una IA local'));
    expect(prompt, contains('No inventes'));
    for (final entity in AppSchema.entities) {
      expect(prompt, contains(entity.name));
    }
    expect(prompt, contains('Muéstrame los $plural'));
    expect(prompt, contains('Datos reales ahora mismo:'));
    expect(prompt, contains('- $plural: 2 registros: Uno, Dos.'));
    expect(LocalLlmChat.systemPrompt(), isNot(contains('Datos reales ahora mismo:')));
  });

  test('replies with the model text, remembers the conversation and sends it back next time', () async {
    final seen = <List<ChatTurn>>[];
    final chat = LocalLlmChat(
      LocalModelManager(),
      inferenceOverride: (system, turns) async {
        seen.add(List.of(turns));
        return 'Respuesta ${seen.length}';
      },
    );
    expect(await chat.reply('hola'), 'Respuesta 1');
    expect(await chat.reply('¿y tú?'), 'Respuesta 2');
    expect(seen.last.map((t) => t.text), ['hola', 'Respuesta 1', '¿y tú?']);
    expect(seen.last.map((t) => t.isUser), [true, false, true]);
  });

  test('passes the real data and the system prompt to the model on every question', () async {
    String? seenSystem;
    final chat = LocalLlmChat(
      LocalModelManager(),
      inferenceOverride: (system, turns) async {
        seenSystem = system;
        return 'Hay dos.';
      },
    );
    await chat.reply('¿cuántos hay?', dataContext: '- $plural: 2 registros: Uno, Dos.');
    expect(seenSystem, contains('- $plural: 2 registros: Uno, Dos.'));
    expect(seenSystem, contains('NO puedes buscar en internet'));
  });

  test('remembers an exchange that did not go through the model, to give the next question some context', () async {
    final seen = <List<ChatTurn>>[];
    final chat = LocalLlmChat(
      LocalModelManager(),
      inferenceOverride: (system, turns) async {
        seen.add(List.of(turns));
        return 'ok';
      },
    );
    chat.remember('muéstrame los $plural', 'Encontré 2 $plural.');
    await chat.reply('¿y cuál es el primero?');
    expect(seen.single.map((t) => t.text), ['muéstrame los $plural', 'Encontré 2 $plural.', '¿y cuál es el primero?']);
    chat.clear();
    expect(chat.history, isEmpty);
  });

  test('keeps only the most recent turns so the prompt stays small', () async {
    final seen = <List<ChatTurn>>[];
    final chat = LocalLlmChat(
      LocalModelManager(),
      maxTurns: 4,
      inferenceOverride: (system, turns) async {
        seen.add(List.of(turns));
        return 'ok';
      },
    );
    for (var i = 1; i <= 5; i++) {
      await chat.reply('pregunta $i');
    }
    expect(seen.last.length, 5);
    expect(seen.last.first.text, 'pregunta 3');
    expect(chat.history.length, 4);
  });

  test('returns null so the caller can use the fixed texts: no model, failure, empty answer or timeout', () async {
    expect(await LocalLlmChat(LocalModelManager()).reply('hola'), isNull);
    expect(await LocalLlmChat(LocalModelManager(), inferenceOverride: (s, t) async => '   ').reply('hola'), isNull);
    final failing = LocalLlmChat(LocalModelManager(), inferenceOverride: (s, t) async => throw StateError('boom'));
    expect(await failing.reply('hola'), isNull);
    expect(failing.history, isEmpty);
    final slow = LocalLlmChat(
      LocalModelManager(),
      timeout: const Duration(milliseconds: 20),
      inferenceOverride: (s, t) async {
        await Future<void>.delayed(const Duration(milliseconds: 300));
        return 'tarde';
      },
    );
    expect(await slow.reply('hola'), isNull);
    expect(await LocalLlmChat(LocalModelManager(), inferenceOverride: (s, t) async => 'x').reply('   '), isNull);
  });

  test('cleans the answer: trims, drops a speaker label and collapses blank lines', () async {
    expect(LocalLlmChat.clean('  Asistente:   Hola  '), 'Hola');
    expect(LocalLlmChat.clean('Uno\\n\\n\\n\\nDos'), 'Uno\\n\\nDos');
    final chat = LocalLlmChat(LocalModelManager(), inferenceOverride: (s, t) async => 'IA: Con gusto.');
    expect(await chat.reply('hola'), 'Con gusto.');
  });
}
'''
        view_test = '''import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/assistant/app_schema.dart';
import 'package:generated_crud_app/assistant/assistant_texts.dart';
import 'package:generated_crud_app/assistant/assistant_view.dart';
import 'package:generated_crud_app/assistant/command_router.dart';
import 'package:generated_crud_app/assistant/local_llm_chat.dart';
import 'package:generated_crud_app/assistant/local_model_manager.dart';
import 'package:generated_crud_app/assistant/model_downloader.dart';
import 'package:llamadart/llamadart.dart';

class _FakeEngine implements LocalModelEngineHandle {
  @override
  LlamaEngine? get engine => null;

  @override
  Future<void> loadModel(String path, {ModelParams? modelParams}) async {}

  @override
  Future<void> dispose() async {}
}

Future<LocalModelManager> _manager(WidgetTester tester, {required bool withModel, String? label}) async {
  final directory = (await tester.runAsync(() => Directory.systemTemp.createTemp('assistant-chat-')))!;
  addTearDown(() => directory.deleteSync(recursive: true));
  if (withModel) File('${directory.path}/local_model.gguf').writeAsBytesSync([1, 2, 3]);
  if (withModel && label != null) File('${directory.path}/local_model.meta').writeAsStringSync(label);
  return LocalModelManager(engineFactory: _FakeEngine.new, modelDirectoryProvider: () async => directory);
}

Future<void> _open(WidgetTester tester, LocalModelManager manager, LocalLlmChat chat, {required bool withModel}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: AssistantView(
        router: CommandRouter(registry: const {}),
        modelManagerFactory: () => manager,
        chat: chat,
      ),
    ),
  );
  // la carga del modelo usa archivos reales: se alterna espera real y pump hasta que termine
  for (var i = 0; i < 40; i++) {
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
    await tester.pump();
    if (!withModel || manager.state == LocalModelState.ready) return;
  }
}

Future<void> _ask(WidgetTester tester, String text) async {
  await tester.enterText(find.byType(TextField), text);
  await tester.tap(find.byIcon(Icons.send));
  await tester.pump();
  await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 80)));
  await tester.pump(const Duration(milliseconds: 50));
  await tester.pump();
}

void main() {
  final noun = AssistantTexts.singular(AppSchema.entities.first);

  testWidgets('conversation goes to the AI and the answer is marked as AI', (tester) async {
    final manager = await _manager(tester, withModel: true);
    final systems = <String>[];
    final chat = LocalLlmChat(
      manager,
      inferenceOverride: (system, turns) async {
        systems.add(system);
        return 'Con gusto: te explico qué es eso.';
      },
    );
    await _open(tester, manager, chat, withModel: true);
    expect(manager.state, LocalModelState.ready);

    await _ask(tester, 'hola');
    expect(find.text('Con gusto: te explico qué es eso.'), findsOneWidget);
    expect(find.textContaining('Soy tu asistente'), findsNothing);
    expect(find.text('IA local'), findsOneWidget);

    await _ask(tester, '¿qué es un $noun en un sistema de gestión?');
    expect(find.text('Con gusto: te explico qué es eso.'), findsNWidgets(2));
    expect(find.text('IA local'), findsNWidgets(2));
    expect(systems.length, 2);
    expect(systems.last, contains('NO puedes buscar en internet'));
  });

  testWidgets('a help request keeps its exact text even when the AI is ready', (tester) async {
    final manager = await _manager(tester, withModel: true);
    var calls = 0;
    final chat = LocalLlmChat(
      manager,
      inferenceOverride: (system, turns) async {
        calls++;
        return 'no debería usarse';
      },
    );
    await _open(tester, manager, chat, withModel: true);
    expect(manager.state, LocalModelState.ready);

    await _ask(tester, 'ayuda');
    expect(calls, 0);
    expect(find.textContaining('muéstrame los'), findsWidgets);
    expect(find.text('Respuesta de la app'), findsOneWidget);
  });

  testWidgets('without a model the fixed texts are used and marked as app replies', (tester) async {
    final manager = await _manager(tester, withModel: false);
    var calls = 0;
    final chat = LocalLlmChat(
      manager,
      inferenceOverride: (system, turns) async {
        calls++;
        return 'no debería usarse';
      },
    );
    await _open(tester, manager, chat, withModel: false);
    expect(manager.state, LocalModelState.notConfigured);

    await _ask(tester, 'hola');
    expect(calls, 0);
    expect(find.textContaining('Soy tu asistente'), findsOneWidget);
    expect(find.text('Respuesta de la app'), findsOneWidget);
    expect(find.text('IA local'), findsNothing);
  });

  testWidgets('a person with the smaller model of earlier versions is offered the improved AI', (tester) async {
    final manager = await _manager(tester, withModel: true, label: 'qwen2.5-0.5b-instruct-q4_k_m.gguf');
    final chat = LocalLlmChat(manager, inferenceOverride: (system, turns) async => 'ok');
    await _open(tester, manager, chat, withModel: true);
    expect(manager.state, LocalModelState.ready);
    expect(find.text('Descargar IA mejorada'), findsOneWidget);
  });

  testWidgets('a person who already has the current model is not offered anything to download', (tester) async {
    final manager = await _manager(tester, withModel: true, label: ModelDownloader.defaultFileName);
    final chat = LocalLlmChat(manager, inferenceOverride: (system, turns) async => 'ok');
    await _open(tester, manager, chat, withModel: true);
    expect(manager.state, LocalModelState.ready);
    expect(find.text('Descargar IA mejorada'), findsNothing);
    expect(find.text('IA local lista'), findsOneWidget);
  });

  testWidgets('when the AI fails, the assistant falls back to the fixed help instead of leaving the person without an answer', (tester) async {
    final manager = await _manager(tester, withModel: true);
    final chat = LocalLlmChat(manager, inferenceOverride: (system, turns) async => throw StateError('boom'));
    await _open(tester, manager, chat, withModel: true);
    expect(manager.state, LocalModelState.ready);

    await _ask(tester, '¿qué es un $noun en un sistema de gestión?');
    expect(find.textContaining('No logré entender'), findsOneWidget);
  });
}
'''
        (base_path / 'test' / 'assistant' / 'local_llm_chat_test.dart').write_text(
            unicodedata.normalize("NFC", chat_test), encoding="utf-8", newline="\n"
        )
        (base_path / 'test' / 'assistant' / 'assistant_chat_view_test.dart').write_text(
            unicodedata.normalize("NFC", view_test), encoding="utf-8", newline="\n"
        )

    def _generate_local_llm_command_extractor(self, base_path):
        """Genera lib/assistant/local_llm_command_extractor.dart (generico:
        construye el prompt a partir de AppSchema en tiempo de ejecucion, sin
        ningun nombre de entidad especifico del proyecto en este generador).
        Devuelve un BusinessCommand propuesto o un fallo; NUNCA ejecuta nada
        directamente ni llama a CommandRouter/EntityServiceAdapter."""
        content = '''import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:llamadart/llamadart.dart';

import 'app_schema.dart';
import 'business_command.dart';
import 'command_parser.dart';
import 'local_model_manager.dart';

/// Resultado de intentar extraer un comando usando el modelo local. Misma
/// forma que ParsedCommandResult (CommandParser) a proposito: ambos caminos
/// producen, en caso de exito, exactamente el mismo BusinessCommand que
/// CommandValidator/CommandRouter ya saben consumir sin cambios.
class LocalLlmExtractionResult {
  final BusinessCommand? command;
  final String? error;

  const LocalLlmExtractionResult.success(BusinessCommand command)
      : command = command,
        error = null;

  const LocalLlmExtractionResult.failure(String error)
      : command = null,
        error = error;

  bool get isSuccess => command != null;
}

/// Resultado interno de _normalizeByAction: data/filters ya filtrados segun
/// el esquema real y la accion declarada.
class _NormalizedCommandFields {
  final Map<String, dynamic> data;
  final Map<String, dynamic> filters;

  const _NormalizedCommandFields(this.data, this.filters);
}

/// Funcion de inferencia cruda inyectable: unicamente para pruebas, permite
/// sustituir la llamada real al motor local por un doble de prueba
/// (respuesta valida, JSON malformado, excepcion, o una promesa que nunca
/// resuelve dentro del timeout de prueba) sin necesitar un archivo .gguf
/// real ni el motor nativo.
typedef LocalLlmRawInference = Future<String> Function(String prompt);

/// Convierte texto (escrito o transcrito) en un BusinessCommand propuesto,
/// usando el modelo GGUF cargado en [modelManager] y el esquema real de la
/// app (AppSchema) para construir el prompt. Nunca hardcodea el nombre de
/// ninguna entidad: itera AppSchema.entities en tiempo de ejecucion, por lo
/// que funciona igual para cualquier esquema UML generado.
///
/// Esta clase SOLO propone un comando: no valida contra reglas de negocio
/// (eso lo hace CommandValidator, sin cambios) ni ejecuta nada (eso lo hace
/// CommandRouter, sin cambios). Ante cualquier fallo — timeout, JSON
/// malformado, forma invalida, excepcion del motor, modelo no listo —
/// devuelve un fallo limpio; nunca lanza una excepcion no controlada y nunca
/// produce un BusinessCommand parcial.
class LocalLlmCommandExtractor {
  final LocalModelManager modelManager;
  final LocalLlmRawInference? _rawInferenceOverride;
  final Duration _timeout;

  const LocalLlmCommandExtractor(
    this.modelManager, {
    @visibleForTesting LocalLlmRawInference? rawInferenceOverride,
    Duration timeout = const Duration(seconds: 8),
  })  : _rawInferenceOverride = rawInferenceOverride,
        _timeout = timeout;

  static const List<String> _allowedActions = [
    'create',
    'read',
    'update',
    'delete',
    'unknown',
  ];

  Future<LocalLlmExtractionResult> extract(String rawText) async {
    final trimmed = rawText.trim();
    if (trimmed.isEmpty) {
      return const LocalLlmExtractionResult.failure('Escribe o di un comando.');
    }
    if (modelManager.state != LocalModelState.ready && _rawInferenceOverride == null) {
      return const LocalLlmExtractionResult.failure('El modelo local no esta listo.');
    }

    final prompt = _buildPrompt(trimmed);

    try {
      final raw = await _runInference(prompt).timeout(_timeout);
      return _parseAndBuildCommand(raw, trimmed);
    } on TimeoutException {
      return const LocalLlmExtractionResult.failure(
          'La inferencia local tardo demasiado.');
    } catch (error) {
      return LocalLlmExtractionResult.failure(
          'Error de inferencia local: $error');
    }
  }

  Future<String> _runInference(String prompt) {
    final override = _rawInferenceOverride;
    if (override != null) {
      return override(prompt);
    }
    return _runRealInference(prompt);
  }

  /// Camino real (no usado en pruebas): pide JSON estricto (cualquier objeto
  /// JSON valido, forzado por el grammar constraint del motor) y devuelve el
  /// texto ya decodificado como String para que _parseAndBuildCommand lo
  /// procese exactamente igual que la salida de una funcion de prueba
  /// inyectada.
  Future<String> _runRealInference(String prompt) async {
    final engine = modelManager.engine;
    if (engine == null) {
      throw StateError('El modelo local no esta listo.');
    }
    final result = await engine.createStructuredJson<Map<String, dynamic>>(
      [
        LlamaChatMessage.fromText(
          role: LlamaChatRole.system,
          text: _systemInstructions(),
        ),
        LlamaChatMessage.fromText(role: LlamaChatRole.user, text: prompt),
      ],
      output: LlamaStructuredOutput<Map<String, dynamic>>.jsonObject(
        decoder: (json) => json,
      ),
      params: const GenerationParams(temp: 0.1, maxTokens: 256),
    );
    return jsonEncode(result);
  }

  String _systemInstructions() {
    return 'Traduces instrucciones en espanol a un unico objeto JSON con '
        'EXACTAMENTE estas claves: "action" (uno de create, read, update, '
        'delete, unknown), "entity" (nombre de una entidad conocida; es el '
        'tipo de registro o tabla, nunca el valor de un registro), '
        '"data" (objeto con los campos a escribir) y "filters" (objeto con '
        'los campos para ubicar el registro objetivo). Para read, data debe '
        'estar vacio y el valor buscado debe ir en filters. No respondas '
        'nada mas que ese objeto JSON.';
  }

  /// Construye el prompt a partir de AppSchema.entities en tiempo de
  /// ejecucion. A proposito no contiene ningun literal de entidad/campo de
  /// ningun proyecto: describe lo que el esquema actual tenga, sea el que
  /// sea.
  String _buildPrompt(String rawText) {
    final buffer = StringBuffer();
    buffer.writeln('Entidades disponibles:');
    for (final entity in AppSchema.entities) {
      final fieldDescriptions = entity.allWritableFields
          .map((f) => '${f.name}:${f.dartType}${f.isPrimaryKey ? " (pk)" : ""}')
          .join(', ');
      final nameFieldDescription = entity.nameField == null
          ? 'sin campo de nombre'
          : 'campo de nombre: ${entity.nameField}';
      buffer.writeln(
          '- ${entity.name}: $fieldDescriptions; $nameFieldDescription');
    }
    buffer.writeln();
    buffer.writeln(
        '"entity" debe ser EXACTAMENTE una de las entidades disponibles: '
        '${AppSchema.entities.map((entity) => entity.name).join(", ")}.');
    buffer.writeln(
        '"entity" identifica el tipo de registro o tabla; nunca es el valor '
        'de un registro. Un nombre, codigo u otro valor solicitado debe ir '
        'en "filters" bajo un campo real de la entidad elegida.');
    buffer.writeln(
        'Si una lectura no nombra el tipo explicitamente, infiere cual de '
        'las entidades disponibles describe mejor el valor solicitado, pero '
        'mantiene ese valor dentro de "filters".');
    buffer.writeln('Para READ usa "data": {}. Formas READ validas:');
    for (final entity in AppSchema.entities) {
      final nameField = entity.nameField;
      if (nameField == null) continue;
      buffer.writeln('- ${jsonEncode({
        'action': 'read',
        'entity': entity.name,
        'data': <String, dynamic>{},
        'filters': {nameField: '<valor solicitado>'},
      })}');
    }
    buffer.writeln(
        'En esas formas reemplaza <valor solicitado> por el valor real de '
        'la instruccion; no lo copies en "entity".');
    // Formas de CREATE / UPDATE / DELETE con los nombres de campo reales: sin ellas el modelo adivina nombres de campo
    // ("nombre" en vez del campo real) y la orden se rechaza. Solo una entidad de ejemplo: el prompt debe seguir corto.
    final example = AppSchema.entities.where((entity) => entity.nameField != null).firstOrNull;
    if (example != null) {
      final nameField = example.nameField!;
      final pk = example.pkField.name;
      buffer.writeln(
          'Formas de las demas acciones (con los nombres de campo reales; para cada entidad usa SUS campos):');
      buffer.writeln('- ${jsonEncode({
        'action': 'create',
        'entity': example.name,
        'data': {nameField: '<valor>'},
        'filters': <String, dynamic>{},
      })}');
      buffer.writeln('- ${jsonEncode({
        'action': 'update',
        'entity': example.name,
        'data': {nameField: '<nuevo valor>'},
        'filters': {pk: '<id>'},
      })}');
      buffer.writeln('- ${jsonEncode({
        'action': 'delete',
        'entity': example.name,
        'data': <String, dynamic>{},
        'filters': {pk: '<id>'},
      })}');
      buffer.writeln(
          'Si la persona da un numero para identificar un registro, ese numero es el id y va en "filters" bajo la '
          'clave primaria. Reemplaza lo que esta entre < > por el valor real de la instruccion; nunca inventes valores '
          'que la persona no dijo.');
    }
    buffer.writeln();
    buffer.writeln('Instruccion del usuario: "$rawText"');
    buffer.writeln(
        'Responde SOLO el objeto JSON descrito, sin texto adicional ni '
        'bloques de codigo.');
    return buffer.toString();
  }

  LocalLlmExtractionResult _parseAndBuildCommand(String raw, String rawText) {
    final decoded = _extractJsonObject(raw);
    if (decoded == null) {
      return const LocalLlmExtractionResult.failure(
          'El modelo local no devolvio JSON valido.');
    }

    final actionRaw = decoded['action'];
    if (actionRaw is! String || !_allowedActions.contains(actionRaw)) {
      return const LocalLlmExtractionResult.failure(
          'El modelo local devolvio una accion no reconocida.');
    }

    final entityRaw = decoded['entity'];
    if (entityRaw is! String || entityRaw.trim().isEmpty) {
      return const LocalLlmExtractionResult.failure(
          'El modelo local no indico una entidad.');
    }

    final data = _asStringKeyedMap(decoded['data']);
    final filters = _asStringKeyedMap(decoded['filters']);
    if (data == null || filters == null) {
      return const LocalLlmExtractionResult.failure(
          'El modelo local devolvio "data"/"filters" con una forma invalida.');
    }

    final action = CommandAction.values.firstWhere(
      (a) => a.name == actionRaw,
      orElse: () => CommandAction.unknown,
    );
    final entity = AppSchema.resolveEntity(entityRaw);

    final normalized = _normalizeByAction(
      action: action,
      entity: entity,
      data: data,
      filters: filters,
      rawText: rawText,
    );
    if (normalized == null) {
      // El modelo local no propuso un comando confiable para esta accion
      // (ver _normalizeByAction): en vez de dejar pasar un BusinessCommand
      // potencialmente inseguro o incompleto, esto se trata igual que
      // cualquier otro fallo de extraccion -- el llamador (AssistantView)
      // cae automaticamente al CommandParser determinista existente, que ya
      // sabe interpretar texto en espanol (incluida la accion de lectura)
      // de forma segura y sin inventar datos.
      return const LocalLlmExtractionResult.failure(
          'El modelo local no propuso un comando confiable.');
    }

    return LocalLlmExtractionResult.success(BusinessCommand(
      action: action,
      entity: entity!.name,
      data: normalized.data,
      filters: normalized.filters,
      rawText: rawText,
    ));
  }

  /// Normaliza data/filters segun la accion declarada, usando unicamente el
  /// esquema real (AssistantEntitySchema) -- nunca un nombre de
  /// campo/entidad fijo de ningun proyecto -- y devuelve null cuando la
  /// salida del modelo local no es confiable para esa accion, en cuyo caso
  /// [extract] falla limpiamente (ver arriba) en vez de proponer un
  /// BusinessCommand inseguro. Reglas por accion:
  /// - READ/DELETE: [data] nunca participa, siempre queda vacio; [filters]
  ///   solo conserva claves que sean campos reales del esquema, sin valores
  ///   nulos/vacios (un filtro nulo no es una restriccion real del usuario).
  /// - UPDATE: [data] solo conserva campos escribibles reales que no sean
  ///   la clave primaria; [filters] igual que arriba. Si alguno queda vacio,
  ///   se rechaza antes de llegar al validador.
  /// - CREATE: [data] solo conserva campos escribibles reales (la clave
  ///   primaria autoincremental nunca se acepta, aunque el modelo la
  ///   incluya); TODO campo requerido en creacion debe estar presente (si
  ///   falta o vino nulo, se rechaza -- visto fisicamente: el modelo a
  ///   veces envia null en vez de omitir el campo); y cada valor propuesto
  ///   (salvo booleano, dificil de mapear a texto libre de forma generica)
  ///   debe tener respaldo textual real en lo que el usuario efectivamente
  ///   escribio o dijo -- el modelo no puede inventar un precio/cantidad/
  ///   etc. que no aparece en absoluto en la entrada (visto fisicamente: el
  ///   modelo alucino precio/stock completos para una entrada que no los
  ///   mencionaba en absoluto). El respaldo textual se limita a valores
  ///   numericos, que son el patron fisicamente reproducido.
  /// Toda accion mutante (CREATE/UPDATE/DELETE) debe coincidir con la
  /// intencion explicita que CommandParser reconoce en el primer verbo del
  /// texto crudo. Una entidad desconocida o una mutacion no respaldada se
  /// rechaza para activar el fallback determinista sin ejecutar nada.
  _NormalizedCommandFields? _normalizeByAction({
    required CommandAction action,
    required AssistantEntitySchema? entity,
    required Map<String, dynamic> data,
    required Map<String, dynamic> filters,
    required String rawText,
  }) {
    if (entity == null) return null;

    final isMutation = action == CommandAction.create ||
        action == CommandAction.update ||
        action == CommandAction.delete;
    if (isMutation && CommandParser.recognizeAction(rawText) != action) {
      return null;
    }

    // Valores que son solo simbolos comodin ("*", "%", "?"...): el modelo pequeno los usa para decir "cualquiera"
    // (visto en un iPhone real: "lista todos los departamentos" llegaba con filters {titulo: "*"}, la app lo aplicaba
    // al pie de la letra y respondia "Sin resultados"). Se descartan SOLO en filtros, nunca en data: un registro
    // puede llamarse "*todos*". Un DELETE/UPDATE que quede sin filtros se rechaza mas abajo: nunca borra "todo".
    final wildcardOnly = RegExp(r'^[*%?_.\\s]+$');
    // Un valor como "<valor solicitado>" es texto de la plantilla del prompt copiado tal cual por el modelo
    // (visto con el modelo real): no es un dato de la persona, en ningun campo ni accion.
    final placeholder = RegExp(r'^\\s*<[^>]*>\\s*$');

    // El modelo pequeno manda numeros como texto ("id": "3"): se aceptan como numero en los campos numericos.
    // Un valor que la persona nunca dijo no es suyo: el modelo pequeno copia valores de los ejemplos del prompt
    // (visto con el modelo real: "muestra los X" llegaba con filters {id: 3}) o los inventa. Cada valor debe aparecer
    // en lo que dijo o escribio (sin mayusculas ni acentos); si no, se descarta y la orden se rechaza o queda mas amplia.
    String flat(String text) => AppSchema.normalize(text).replaceAll(',', '.');
    final spoken = flat(rawText);
    bool grounded(Object? value) {
      if (value is bool) return true;
      final text = flat('$value').trim();
      return text.isNotEmpty && spoken.contains(text);
    }

    Object? coerce(AssistantFieldSchema field, Object? value) {
      if (value is String && field.dartType == 'int') return int.tryParse(value.trim()) ?? value;
      if (value is String && field.dartType == 'double') return double.tryParse(value.trim().replaceAll(',', '.')) ?? value;
      return value;
    }

    Map<String, dynamic> keepKnownNonEmptyFields(
      Map<String, dynamic> source, {
      bool writableOnly = false,
      bool dropWildcards = false,
    }) {
      final result = <String, dynamic>{};
      for (final entry in source.entries) {
        if (entry.value == null) continue;
        if (entry.value is String && (entry.value as String).trim().isEmpty) continue;
        if (entry.value is String && placeholder.hasMatch(entry.value as String)) continue;
        if (!grounded(entry.value)) continue;
        if (dropWildcards && entry.value is String && wildcardOnly.hasMatch(entry.value as String)) continue;
        final field = entity.fieldByName(entry.key);
        if (field != null && (!writableOnly || field.writable)) {
          result[entry.key] = coerce(field, entry.value);
        }
      }
      return result;
    }

    switch (action) {
      case CommandAction.read:
        return _NormalizedCommandFields(const {}, keepKnownNonEmptyFields(filters, dropWildcards: true));

      case CommandAction.delete:
        final cleanFilters = keepKnownNonEmptyFields(filters, dropWildcards: true);
        if (cleanFilters.isEmpty) return null;
        return _NormalizedCommandFields(const {}, cleanFilters);

      case CommandAction.update:
        var dataSource = data;
        var filterSource = filters;
        if (data.isEmpty) {
          // Visto con el modelo real: "data" vacio y el valor nuevo junto al id en "filters". Si hay una clave primaria,
          // ella ubica el registro y lo demas es el valor nuevo.
          final keys = <String, dynamic>{};
          final values = <String, dynamic>{};
          for (final entry in filters.entries) {
            final field = entity.fieldByName(entry.key);
            if (field != null && field.isPrimaryKey) {
              keys[entry.key] = entry.value;
            } else {
              values[entry.key] = entry.value;
            }
          }
          if (keys.isNotEmpty && values.isNotEmpty) {
            dataSource = values;
            filterSource = keys;
          }
        }
        final cleanData = <String, dynamic>{};
        for (final entry in keepKnownNonEmptyFields(dataSource, writableOnly: true).entries) {
          if (entity.fieldByName(entry.key)!.isPrimaryKey) continue;
          cleanData[entry.key] = entry.value;
        }
        final cleanFilters = keepKnownNonEmptyFields(filterSource, dropWildcards: true);
        if (cleanData.isEmpty || cleanFilters.isEmpty) return null;
        return _NormalizedCommandFields(cleanData, cleanFilters);

      case CommandAction.create:
        final cleanData = <String, dynamic>{};
        // El modelo pequeno a veces pone los campos del registro nuevo en "filters" y deja "data" vacio (visto con el
        // modelo real: "crea un X Valor" -> filters {campo: Valor}). Los valores salen de la frase; "data" manda.
        for (final entry in keepKnownNonEmptyFields({...filters, ...data}, writableOnly: true).entries) {
          final field = entity.fieldByName(entry.key)!;
          if (field.isPrimaryKey && field.isAutoIncrement) continue;
          cleanData[entry.key] = entry.value;
        }
        for (final field in entity.allWritableFields) {
          if (!field.requiredOnCreate) continue;
          if (field.isPrimaryKey && field.isAutoIncrement) continue;
          if (!cleanData.containsKey(field.name)) return null;
        }
        // El respaldo textual solo se exige para campos numericos: es
        // exactamente el patron de alucinacion observado fisicamente
        // (precio/stock inventados de la nada). Un campo de texto (p.ej. el
        // nombre) no se exige aqui -- ya viene acotado por otras vias (debe
        // coincidir con un campo real del esquema) y exigirle respaldo
        // textual literal seria fragil (variantes de formato/orden) para un
        // patron de alucinacion que la evidencia fisica no mostro en texto.
        final rawNumbers = RegExp(r'-?\\d+(?:[.,]\\d+)?')
            .allMatches(rawText)
            .map((match) => match.group(0)!.replaceAll(',', '.'))
            .map(num.tryParse)
            .whereType<num>()
            .toList();
        for (final entry in cleanData.entries) {
          final field = entity.fieldByName(entry.key)!;
          if (field.dartType != 'int' && field.dartType != 'double') continue;
          final proposed = entry.value is num
              ? entry.value as num
              : num.tryParse(entry.value.toString().replaceAll(',', '.'));
          if (proposed == null) return null;
          final grounded = rawNumbers.any((candidate) => candidate == proposed);
          if (!grounded) return null;
        }
        return _NormalizedCommandFields(cleanData, const {});

      case CommandAction.unknown:
        return _NormalizedCommandFields(const {}, const {});
    }
  }

  Map<String, dynamic>? _asStringKeyedMap(dynamic value) {
    if (value == null) return <String, dynamic>{};
    if (value is Map) {
      return value.map((key, v) => MapEntry(key.toString(), v));
    }
    return null;
  }

  /// Extrae y decodifica el primer objeto JSON valido de una respuesta de
  /// texto libre: tolera cercas de markdown (```json ... ```), texto
  /// sobrante antes/despues, y recorta al primer '{' .. ultimo '}'
  /// balanceado antes de rendirse. El camino real ya pide JSON estricto via
  /// grammar constraint, pero esta funcion es la misma para el camino real
  /// y para las funciones de inferencia de prueba, que pueden devolver
  /// deliberadamente salidas mal formadas.
  Map<String, dynamic>? _extractJsonObject(String raw) {
    final direct = _tryDecodeObject(raw);
    if (direct != null) return direct;

    final fenced = raw.replaceAll(RegExp(r'```(json)?'), '');
    final fencedResult = _tryDecodeObject(fenced);
    if (fencedResult != null) return fencedResult;

    final start = raw.indexOf('{');
    final end = raw.lastIndexOf('}');
    if (start == -1 || end == -1 || end <= start) return null;
    return _tryDecodeObject(raw.substring(start, end + 1));
  }

  Map<String, dynamic>? _tryDecodeObject(String candidate) {
    try {
      final decoded = jsonDecode(candidate.trim());
      if (decoded is Map<String, dynamic>) return decoded;
      if (decoded is Map) {
        return decoded.map((key, v) => MapEntry(key.toString(), v));
      }
      return null;
    } catch (_) {
      return null;
    }
  }
}
'''
        (base_path / 'lib' / 'assistant' / 'local_llm_command_extractor.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_local_llm_tests(self, base_path, original_classes):
        """Genera test/assistant/local_llm_command_extractor_test.dart. Usa
        SIEMPRE un backend de inferencia falso inyectado (rawInferenceOverride):
        ninguna prueba automatizada requiere un archivo .gguf real ni el motor
        nativo. Adaptado al esquema UML real igual que _generate_assistant_tests,
        para no hardcodear ningun nombre de entidad de ningun proyecto
        especifico en este generador."""
        manager_test_content = '''import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/assistant/assistant_view.dart';
import 'package:generated_crud_app/assistant/local_model_manager.dart';
import 'package:llamadart/llamadart.dart';

class _FakeEngine implements LocalModelEngineHandle {
  _FakeEngine({this.loadError, this.loadGate});

  final Object? loadError;
  final Completer<void>? loadGate;
  int loadCalls = 0;
  int disposeCalls = 0;
  ModelParams? receivedParams;
  String? receivedPath;

  @override
  LlamaEngine? get engine => null;

  @override
  Future<void> loadModel(String path, {ModelParams? modelParams}) async {
    loadCalls++;
    receivedPath = path;
    receivedParams = modelParams;
    if (loadGate != null) await loadGate!.future;
    if (loadError != null) throw loadError!;
  }

  @override
  Future<void> dispose() async {
    disposeCalls++;
  }
}

void main() {
  late Directory directory;

  setUp(() async {
    directory = await Directory.systemTemp.createTemp('local-model-manager-');
  });

  tearDown(() async {
    if (await directory.exists()) await directory.delete(recursive: true);
  });

  Future<void> seedPersistedModel() async {
    await File('${directory.path}/local_model.gguf').writeAsBytes([1, 2, 3]);
    await File('${directory.path}/local_model.meta').writeAsString('model.gguf');
  }

  LocalModelManager managerFor(List<_FakeEngine> engines) {
    var nextEngine = 0;
    return LocalModelManager(
      engineFactory: () => engines[nextEngine++],
      modelDirectoryProvider: () async => directory,
    );
  }

  test('failed primary is disposed and one CPU fallback ends ready', () async {
    await seedPersistedModel();
    final primary = _FakeEngine(loadError: Exception('primary failed'));
    final fallback = _FakeEngine();
    final manager = managerFor([primary, fallback]);

    await manager.initialize();

    expect(manager.state, LocalModelState.ready);
    expect(primary.loadCalls, 1);
    expect(primary.receivedParams, isNull);
    expect(primary.disposeCalls, 1);
    expect(fallback.loadCalls, 1);
    expect(fallback.receivedParams!.preferredBackend, GpuBackend.cpu);
    expect(fallback.disposeCalls, 0);
    expect(fallback.receivedPath, '${directory.path}/local_model.gguf');
  });

  test('primary and CPU fallback failure end error and dispose both', () async {
    await seedPersistedModel();
    final primary = _FakeEngine(loadError: Exception('primary failed'));
    final fallback = _FakeEngine(loadError: Exception('fallback failed'));
    final manager = managerFor([primary, fallback]);

    await manager.initialize();

    expect(manager.state, LocalModelState.error);
    expect(primary.loadCalls, 1);
    expect(fallback.loadCalls, 1);
    expect(primary.disposeCalls, 1);
    expect(fallback.disposeCalls, 1);
  });

  test('concurrent load calls share one primary attempt', () async {
    await seedPersistedModel();
    final gate = Completer<void>();
    final primary = _FakeEngine(loadGate: gate);
    final manager = managerFor([primary]);

    final first = manager.loadModel();
    final second = manager.loadModel();
    while (primary.loadCalls == 0) {
      await Future<void>.delayed(Duration.zero);
    }

    expect(primary.loadCalls, 1);
    gate.complete();
    await Future.wait([first, second]);
    expect(manager.state, LocalModelState.ready);
  });

  test('persisted model autoload needs no import or copy', () async {
    await seedPersistedModel();
    final primary = _FakeEngine();
    final manager = managerFor([primary]);

    await manager.initialize();

    expect(manager.state, LocalModelState.ready);
    expect(primary.loadCalls, 1);
    expect(await File('${directory.path}/local_model.gguf').readAsBytes(), [1, 2, 3]);
  });

  test('manager disposal releases the successful engine', () async {
    await seedPersistedModel();
    final primary = _FakeEngine();
    final manager = managerFor([primary]);
    await manager.initialize();

    manager.dispose();
    await Future<void>.delayed(Duration.zero);

    expect(primary.disposeCalls, 1);
  });

  testWidgets('AssistantView disposes its owned manager and engine', (tester) async {
    // El disco es real: dentro de testWidgets (tiempo simulado) hay que esperarlo con runAsync, si no la prueba se cuelga.
    await tester.runAsync(seedPersistedModel);
    final primary = _FakeEngine();
    final manager = managerFor([primary]);

    await tester.pumpWidget(MaterialApp(
      home: AssistantView(modelManagerFactory: () => manager),
    ));
    // initialize() encadena varias lecturas de disco reales: cada una necesita tiempo real y luego un pump.
    for (var i = 0; i < 40 && manager.state != LocalModelState.ready; i++) {
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await tester.pump();
    }
    expect(manager.state, LocalModelState.ready);

    await tester.pumpWidget(const MaterialApp(home: SizedBox()));
    await tester.pump();

    expect(primary.disposeCalls, 1);
  });
}
'''
        (base_path / 'test' / 'assistant' / 'local_model_manager_test.dart').write_text(
            self._sanitize(manager_test_content), encoding="utf-8", newline="\n"
        )

        metas = [self._assistant_entity_metadata(c) for c in original_classes]
        def supports_complete_create(meta):
            fields = meta['fields']
            if not meta['name_field'] or not fields or fields[0]['dart_type'] == 'double':
                return False
            required = [
                *[field for field in fields if field['required_on_create']],
                *[rel for rel in meta['relations'] if rel['required_on_create']],
            ]
            return all(field['writable'] for field in required)

        create_subjects = [m for m in metas if supports_complete_create(m)]
        subject = next(
            (
                m for m in create_subjects
                if any(
                    field['required_on_create']
                    and not field['is_primary_key']
                    and field['dart_type'] in ('int', 'double')
                    for field in m['fields']
                )
            ),
            create_subjects[0] if create_subjects else None,
        )
        if subject is None:
            content = (
                "import 'package:flutter_test/flutter_test.dart';\n\n"
                "void main() {\n"
                "  test('no assistant-writable entity in this schema', () {\n"
                "    expect(true, isTrue);\n"
                "  });\n"
                "}\n"
            )
            (base_path / 'test' / 'assistant' / 'local_llm_command_extractor_test.dart').write_text(
                self._sanitize(content), encoding="utf-8", newline="\n"
            )
            return

        entity_name = subject['name']
        entity_literal = self._assistant_dart_string_literal(entity_name)
        name_field = subject['name_field']
        writable_extra = [
            f for f in subject['fields']
            if f['writable'] and not f['is_primary_key'] and f['name'] != name_field
        ]
        update_field = writable_extra[0]['name'] if writable_extra else name_field
        pk_dart_type = subject['fields'][0]['dart_type']
        pk_json_literal = "1" if pk_dart_type == 'int' else "'seed-1'"

        content = '''import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:generated_crud_app/assistant/app_schema.dart';
import 'package:generated_crud_app/assistant/business_command.dart';
import 'package:generated_crud_app/assistant/command_parser.dart';
import 'package:generated_crud_app/assistant/command_router.dart';
import 'package:generated_crud_app/assistant/command_validator.dart';
import 'package:generated_crud_app/assistant/entity_service_adapter.dart';
import 'package:generated_crud_app/assistant/local_llm_command_extractor.dart';
import 'package:generated_crud_app/assistant/local_model_manager.dart';

class _FakeAdapter extends EntityServiceAdapter {
  _FakeAdapter(super.schema, this.rows);
  final List<Map<String, dynamic>> rows;
  int deleteCalls = 0;
  Map<String, dynamic>? lastCreatedMap;

  @override
  Future<List<Map<String, dynamic>>> list() async => rows;

  @override
  Future<Map<String, dynamic>> create(Map<String, dynamic> jsonData) async {
    lastCreatedMap = jsonData;
    return jsonData;
  }

  @override
  Future<Map<String, dynamic>> updateFromMap(String id, Map<String, dynamic> mergedJsonData) async =>
      mergedJsonData;

  @override
  Future<void> deleteById(String id) async {
    deleteCalls++;
  }
}

dynamic _sampleRequiredValue(AssistantFieldSchema field, int seed) {
  return switch (field.dartType) {
    'int' => 10 + seed,
    'double' => 10.5 + seed,
    'bool' => true,
    _ => 'Ejemplo $seed',
  };
}

Map<String, dynamic> _completeCreateData(AssistantEntitySchema schema) {
  final result = <String, dynamic>{};
  var seed = 1;
  for (final field in schema.allWritableFields) {
    if (!field.requiredOnCreate) continue;
    if (field.isPrimaryKey && field.isAutoIncrement) continue;
    result[field.name] = _sampleRequiredValue(field, seed++);
  }
  return result;
}

String _groundedCreateText(
  AssistantEntitySchema schema,
  Map<String, dynamic> data, {
  Set<String> omittedFields = const {},
}) {
  final values = data.entries
      .where((entry) => !omittedFields.contains(entry.key))
      .map((entry) => entry.value)
      .join(' ');
  return 'agrega ${schema.name.toLowerCase()} $values';
}

void main() {
  final schema = AppSchema.entities.firstWhere((e) => e.name == __ENTITY__);
  final pkJsonKey = schema.pkField.jsonKey;
  final nameJsonKey = schema.fieldByName(__NAME_FIELD__)!.jsonKey;

  test('with no model ready and no fake backend injected, behaves exactly like having no local AI at all', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(manager);
    final result = await extractor.extract('cualquier texto');
    expect(result.isSuccess, isFalse);
  });

  test('extracts a valid CREATE JSON into a BusinessCommand', () async {
    final manager = LocalModelManager();
    final createData = _completeCreateData(schema);
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async {
        // The prompt must be schema-driven: it names the entity under test
        // because AppSchema.entities says so at runtime, never because the
        // generator hardcoded it.
        expect(prompt, contains(__ENTITY__));
        return jsonEncode({
          'action': 'create',
          'entity': __ENTITY__,
          'data': createData,
          'filters': <String, dynamic>{},
        });
      },
    );
    final result = await extractor.extract(_groundedCreateText(schema, createData));
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.action, CommandAction.create);
    expect(result.command!.entity, __ENTITY__);
    expect(result.command!.data, createData);
  });

  test('strips a hallucinated auto-increment primary key from CREATE data before it reaches CommandValidator', () async {
    final manager = LocalModelManager();
    final pkFieldName = schema.pkField.name;
    if (!schema.pkField.isAutoIncrement) return;
    final createData = _completeCreateData(schema)..[pkFieldName] = __PK_JSON__;
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'create',
        'entity': __ENTITY__,
        'data': createData,
        'filters': <String, dynamic>{},
      }),
    );
    final result = await extractor.extract(_groundedCreateText(
      schema,
      createData,
      omittedFields: {pkFieldName},
    ));
    expect(result.isSuccess, isTrue, reason: result.error);
    // The auto-increment primary key must never reach the validator/router,
    // even though the local model hallucinated it in its own JSON output.
    expect(result.command!.data.containsKey(pkFieldName), isFalse);

    final validated = CommandValidator().validate(result.command!);
    expect(validated.isValid, isTrue, reason: validated.error);
  });

  test('extracts a valid READ JSON into a BusinessCommand', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async =>
          '{"action":"read","entity":__ENTITY_JSON__,"data":{},"filters":{__NAME_FIELD_JSON__:"Ejemplo Uno"}}',
    );
    final result = await extractor.extract('muestrame ese Ejemplo Uno');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.action, CommandAction.read);
    expect(result.command!.filters[__NAME_FIELD__], 'Ejemplo Uno');
  });

  test('READ keeps the schema entity separate from the requested record value', () async {
    final nameField = schema.nameField;
    if (nameField == null) return;
    const recordValue = 'Registro Objetivo';
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async {
        final expectedShape = jsonEncode({
          'action': 'read',
          'entity': schema.name,
          'data': <String, dynamic>{},
          'filters': {nameField: '<valor solicitado>'},
        });
        expect(prompt, contains(expectedShape));
        expect(prompt, contains('nunca es el valor de un registro'));
        return jsonEncode({
          'action': 'read',
          'entity': schema.name,
          'data': <String, dynamic>{},
          'filters': {nameField: recordValue},
        });
      },
    );

    final result = await extractor.extract('busca $recordValue');

    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.action, CommandAction.read);
    expect(result.command!.entity, schema.name);
    expect(result.command!.data, isEmpty);
    expect(result.command!.filters, {nameField: recordValue});
  });

  test('entity aliases are canonicalized through AppSchema', () async {
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'read',
        'entity': schema.name.toLowerCase(),
        'data': <String, dynamic>{},
        'filters': <String, dynamic>{},
      }),
    );

    final result = await extractor.extract('lista ${schema.name.toLowerCase()}');

    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.entity, schema.name);
  });

  test('a record value emitted as entity is rejected instead of becoming a command', () async {
    const recordValue = 'Registro Objetivo';
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'read',
        'entity': recordValue,
        'data': <String, dynamic>{},
        'filters': <String, dynamic>{},
      }),
    );

    final result = await extractor.extract('busca $recordValue');

    expect(result.isSuccess, isFalse);
    expect(result.command, isNull);
  });

  test('extracts a valid UPDATE JSON into a BusinessCommand', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async =>
          '{"action":"update","entity":__ENTITY_JSON__,"data":{__UPDATE_FIELD_JSON__:"nuevo"},"filters":{__NAME_FIELD_JSON__:"Ejemplo Uno"}}',
    );
    final result = await extractor.extract('actualiza ese Ejemplo Uno a nuevo');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.action, CommandAction.update);
    expect(result.command!.data[__UPDATE_FIELD__], 'nuevo');
  });

  test('extracts a valid DELETE JSON, and CommandRouter still requires explicit two-phase confirmation before deleting anything', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async =>
          '{"action":"delete","entity":__ENTITY_JSON__,"data":{},"filters":{__NAME_FIELD_JSON__:"Ejemplo Uno"}}',
    );
    final result = await extractor.extract('elimina ese Ejemplo Uno');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.action, CommandAction.delete);

    final validated = CommandValidator().validate(result.command!);
    expect(validated.isValid, isTrue, reason: validated.error);

    final adapter = _FakeAdapter(schema, [
      {pkJsonKey: __PK_JSON__, nameJsonKey: 'Ejemplo Uno'},
    ]);
    final router = CommandRouter(registry: {__ENTITY__: adapter});
    final outcome = await router.execute(validated.command!);

    // Phase 1 only: a pending delete is proposed, nothing was deleted yet.
    expect(outcome.success, isTrue);
    expect(outcome.pendingDelete, isNotNull);
    expect(adapter.deleteCalls, 0);

    // Phase 2: only an explicit confirmDelete(pending) call — using the
    // exact PendingDelete already returned above, never re-derived from
    // filters — actually deletes.
    final confirmed = await router.confirmDelete(outcome.pendingDelete!);
    expect(confirmed.success, isTrue);
    expect(adapter.deleteCalls, 1);
  });

  test('falls back cleanly when the local model returns malformed JSON', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async => 'esto no es JSON en absoluto',
    );
    final result = await extractor.extract('cualquier texto');
    expect(result.isSuccess, isFalse);
    expect(result.error, isNotNull);
  });

  test('extracts JSON even when wrapped in a markdown code fence with extra prose', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async =>
          'Claro, aqui esta:\\n```json\\n{"action":"read","entity":__ENTITY_JSON__,"data":{},"filters":{}}\\n```\\nEspero que ayude.',
    );
    final result = await extractor.extract('lista todos');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.action, CommandAction.read);
  });

  test('falls back cleanly when local inference throws', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async => throw Exception('simulated engine failure'),
    );
    final result = await extractor.extract('cualquier texto');
    expect(result.isSuccess, isFalse);
    expect(result.error, isNotNull);
  });

  test('falls back cleanly when local inference times out', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) => Future.delayed(const Duration(seconds: 5), () => '{}'),
      timeout: const Duration(milliseconds: 20),
    );
    final result = await extractor.extract('cualquier texto');
    expect(result.isSuccess, isFalse);
    expect(result.error, isNotNull);
  });

  test('rejects an unknown action string in the model output (shape check)', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async =>
          '{"action":"teleport","entity":__ENTITY_JSON__,"data":{},"filters":{}}',
    );
    final result = await extractor.extract('cualquier texto');
    expect(result.isSuccess, isFalse);
  });

  test('an unresolvable entity is rejected by extraction so AppSchema remains authoritative', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async =>
          '{"action":"create","entity":"NoExisteEnEsteEsquema","data":{},"filters":{}}',
    );
    final result = await extractor.extract('crea un marciano');
    expect(result.isSuccess, isFalse);
    expect(result.command, isNull);
  });

  test('an unknown field from the model is dropped by extractor normalization; with no real required data left, extraction now fails closed instead of reaching CommandValidator', () async {
    final manager = LocalModelManager();
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async =>
          '{"action":"create","entity":__ENTITY_JSON__,"data":{"campoInventadoXYZ":"1"},"filters":{}}',
    );
    final result = await extractor.extract('crea uno con un campo inventado');
    // The unknown field is stripped by _normalizeByAction (it is not a real
    // schema field), which leaves no real required CREATE data behind, so
    // this is now correctly rejected at the extraction layer -- the same
    // outcome (this command never mutates anything) as before, just caught
    // one layer earlier, and with the existing deterministic-parser
    // fallback available to the caller instead of a doomed command reaching
    // CommandValidator.
    expect(result.isSuccess, isFalse);
    expect(result.error, isNotNull);
  });

  test('CREATE with a fabricated value that has no grounding in the raw user text is rejected at extraction (physically reproduced: model hallucinated precio/stock for input that never mentioned them)', () async {
    final manager = LocalModelManager();
    final numericFields = schema.allWritableFields.where((field) =>
        field.requiredOnCreate &&
        !field.isPrimaryKey &&
        (field.dartType == 'int' || field.dartType == 'double')).toList();
    if (numericFields.isEmpty) return;
    final fabricatedField = numericFields.first;
    final createData = _completeCreateData(schema)
      ..[fabricatedField.name] = 989898989;
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'create',
        'entity': __ENTITY__,
        'data': createData,
        'filters': <String, dynamic>{},
      }),
    );
    final result = await extractor.extract(_groundedCreateText(
      schema,
      createData,
      omittedFields: {fabricatedField.name},
    ));
    expect(result.isSuccess, isFalse);
    expect(result.error, isNotNull);
  });

  test('numeric grounding compares complete values instead of accepting a substring match', () async {
    final numericFields = schema.allWritableFields.where((field) =>
        field.requiredOnCreate &&
        !field.isPrimaryKey &&
        (field.dartType == 'int' || field.dartType == 'double')).toList();
    if (numericFields.isEmpty) return;
    final numericField = numericFields.first;
    const proposedValue = 989898989;
    final createData = _completeCreateData(schema)
      ..[numericField.name] = proposedValue;
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'create',
        'entity': __ENTITY__,
        'data': createData,
        'filters': <String, dynamic>{},
      }),
    );
    final result = await extractor.extract(
      '${_groundedCreateText(schema, createData, omittedFields: {numericField.name})} '
      '${proposedValue}0',
    );
    expect(result.isSuccess, isFalse);
  });

  test('CREATE is rejected at extraction when a required field is present but null (physically reproduced: model sent null instead of omitting the field)', () async {
    final manager = LocalModelManager();
    final requiredFields = schema.allWritableFields.where((field) =>
        field.requiredOnCreate &&
        !(field.isPrimaryKey && field.isAutoIncrement)).toList();
    if (requiredFields.isEmpty) return;
    final requiredField = requiredFields.last;
    final createData = _completeCreateData(schema)..[requiredField.name] = null;
    final extractor = LocalLlmCommandExtractor(
      manager,
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'create',
        'entity': __ENTITY__,
        'data': createData,
        'filters': <String, dynamic>{},
      }),
    );
    final result = await extractor.extract(_groundedCreateText(
      schema,
      createData,
      omittedFields: {requiredField.name},
    ));
    expect(result.isSuccess, isFalse);
    expect(result.error, isNotNull);
  });

  test('READ never lets data participate and drops hallucinated/unknown/empty filters', () async {
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async =>
          '{"action":"read","entity":__ENTITY_JSON__,'
          '"data":{__NAME_FIELD_JSON__:"no deberia importar"},'
          '"filters":{__NAME_FIELD_JSON__:"Ejemplo Uno","campoInventadoXYZ":"1",'
          '"otroCampo":null}}',
    );
    final result = await extractor.extract(
        'muestra ${schema.name.toLowerCase()} Ejemplo Uno');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.data, isEmpty);
    expect(result.command!.filters, {__NAME_FIELD__: 'Ejemplo Uno'});
  });

  test('READ drops a wildcard filter such as "*" (the small model uses it to mean "all")', () async {
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async =>
          '{"action":"read","entity":__ENTITY_JSON__,'
          '"data":{},"filters":{__NAME_FIELD_JSON__:"*"}}',
    );
    final result = await extractor.extract(
        'lista todos ${schema.name.toLowerCase()}');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.filters, isEmpty);
  });

  test('READ drops a template placeholder such as "<valor solicitado>" copied from the prompt', () async {
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async =>
          '{"action":"read","entity":__ENTITY_JSON__,'
          '"data":{},"filters":{__NAME_FIELD_JSON__:"<valor solicitado>"}}',
    );
    final result = await extractor.extract('necesito ver ${schema.name.toLowerCase()}');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.filters, isEmpty);
  });

  test('DELETE with only a template placeholder is rejected, never a mass delete', () async {
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async =>
          '{"action":"delete","entity":__ENTITY_JSON__,'
          '"data":{},"filters":{__NAME_FIELD_JSON__:"<id>"}}',
    );
    final result = await extractor.extract('elimina ${schema.name.toLowerCase()} Ejemplo');
    expect(result.isSuccess, isFalse);
  });

  test('the prompt teaches the model the real field names for every action, not only READ', () async {
    String? seen;
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async {
        seen = prompt;
        return '{"action":"unknown","entity":__ENTITY_JSON__,"data":{},"filters":{}}';
      },
    );
    await extractor.extract('hola');
    expect(seen, contains('"action":"create"'));
    expect(seen, contains('"action":"update"'));
    expect(seen, contains('"action":"delete"'));
    expect(seen, contains('Formas de las demas acciones'));
    expect(seen, contains(__NAME_FIELD_JSON__));
    expect(seen, contains(schema.pkField.name));
  });

  test('CREATE accepts the fields the small model put under "filters" instead of "data" (seen with the real model)', () async {
    final createData = _completeCreateData(schema);
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'create',
        'entity': __ENTITY__,
        'data': <String, dynamic>{},
        'filters': createData,
      }),
    );
    final result = await extractor.extract(_groundedCreateText(schema, createData));
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.data, createData);
    expect(result.command!.filters, isEmpty);
  });

  test('UPDATE with the new value next to the id under "filters" is split: the key locates, the rest is the new data', () async {
    final key = schema.pkField;
    final nameField = schema.fieldByName(__NAME_FIELD__)!;
    if (key.name == nameField.name) return;
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'update',
        'entity': __ENTITY__,
        'data': <String, dynamic>{},
        'filters': {key.name: '1', nameField.name: 'Nuevo'},
      }),
    );
    final result = await extractor.extract('actualiza ${schema.name.toLowerCase()} 1 a Nuevo');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.action, CommandAction.update);
    expect(result.command!.filters, {key.name: key.dartType == 'int' ? 1 : '1'});
    expect(result.command!.data, {nameField.name: 'Nuevo'});
  });

  test('a numeric id sent as text is accepted as a number', () async {
    if (schema.pkField.dartType != 'int') return;
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'read',
        'entity': __ENTITY__,
        'data': <String, dynamic>{},
        'filters': {schema.pkField.name: '3'},
      }),
    );
    final result = await extractor.extract('muestra ${schema.name.toLowerCase()} 3');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.filters, {schema.pkField.name: 3});
  });

  test('READ drops a filter value the person never said (the small model copies example values from the prompt)', () async {
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'read',
        'entity': __ENTITY__,
        'data': <String, dynamic>{},
        'filters': {__NAME_FIELD__: 'Inventado XYZ'},
      }),
    );
    final result = await extractor.extract('muestra ${schema.name.toLowerCase()}');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.filters, isEmpty);
  });

  test('DELETE with a value the person never said is rejected, never a delete of something else', () async {
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'delete',
        'entity': __ENTITY__,
        'data': <String, dynamic>{},
        'filters': {schema.pkField.name: 3},
      }),
    );
    final result = await extractor.extract('elimina ${schema.name.toLowerCase()} Ejemplo');
    expect(result.isSuccess, isFalse);
  });

  test('a value is accepted when the person said it, ignoring case and accents', () async {
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'read',
        'entity': __ENTITY__,
        'data': <String, dynamic>{},
        'filters': {__NAME_FIELD__: 'Pérez'},
      }),
    );
    final result = await extractor.extract('MUESTRA ${schema.name.toLowerCase()} perez');
    expect(result.isSuccess, isTrue, reason: result.error);
    expect(result.command!.filters, {__NAME_FIELD__: 'Pérez'});
  });

  test('the prompt carries no example numbers or values the model could copy as if the person had said them', () async {
    String? seen;
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async {
        seen = prompt;
        return '{"action":"unknown","entity":__ENTITY_JSON__,"data":{},"filters":{}}';
      },
    );
    await extractor.extract('hola');
    final promptWithoutTheSentence = seen!.split('Instruccion del usuario:').first;
    expect(RegExp(r'\\b(?:id|numero|registro)\\s+\\d').hasMatch(promptWithoutTheSentence), isFalse);
    expect(promptWithoutTheSentence, contains('nunca inventes valores'));
  });

  test('DELETE with only a wildcard filter is rejected, never a mass delete', () async {
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async =>
          '{"action":"delete","entity":__ENTITY_JSON__,'
          '"data":{},"filters":{__NAME_FIELD_JSON__:"*"}}',
    );
    final result = await extractor.extract(
        'elimina ${schema.name.toLowerCase()} *');
    expect(result.isSuccess, isFalse);
  });

  test('a supported Spanish READ falls back to CommandParser when the LLM proposes CREATE', () async {
    final createData = _completeCreateData(schema);
    final rawText = 'muestra ${schema.name.toLowerCase()} Ejemplo Uno';
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'create',
        'entity': __ENTITY__,
        'data': createData,
        'filters': <String, dynamic>{},
      }),
    );

    final llmResult = await extractor.extract(rawText);
    expect(llmResult.isSuccess, isFalse);

    final fallback = CommandParser().parse(rawText);
    expect(fallback.isSuccess, isTrue, reason: fallback.error);
    expect(fallback.command!.action, CommandAction.read);
    expect(fallback.command!.data, isEmpty);
  });

  test('an ambiguous request cannot become CREATE, UPDATE, or DELETE', () async {
    final createData = _completeCreateData(schema);
    final rawText = 'consulta ${schema.name.toLowerCase()} Ejemplo Uno';
    final extractor = LocalLlmCommandExtractor(
      LocalModelManager(),
      rawInferenceOverride: (prompt) async => jsonEncode({
        'action': 'create',
        'entity': __ENTITY__,
        'data': createData,
        'filters': <String, dynamic>{},
      }),
    );

    final llmResult = await extractor.extract(rawText);
    final fallback = CommandParser().parse(rawText);
    expect(llmResult.command, isNull);
    expect(fallback.command, isNull);
  });
}
'''
        content = (
            content
            # JSON-text placeholders MUST be substituted before the
            # Dart-expression placeholders below, since e.g. __ENTITY_JSON__
            # contains __ENTITY__ as a substring and would otherwise be
            # corrupted by the broader replacement running first.
            .replace('__ENTITY_JSON__', json.dumps(entity_name))
            .replace('__NAME_FIELD_JSON__', json.dumps(name_field))
            .replace('__UPDATE_FIELD_JSON__', json.dumps(update_field))
            .replace('__ENTITY__', entity_literal)
            .replace('__NAME_FIELD__', self._assistant_dart_string_literal(name_field))
            .replace('__UPDATE_FIELD__', self._assistant_dart_string_literal(update_field))
            .replace('__PK_JSON__', pk_json_literal)
        )
        (base_path / 'test' / 'assistant' / 'local_llm_command_extractor_test.dart').write_text(
            self._sanitize(content), encoding="utf-8", newline="\n"
        )

    def _generate_assistant_view(self, base_path):
        """Genera lib/assistant/assistant_view.dart (genérico)."""
        content = '''import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'app_schema.dart';
import 'assistant_texts.dart';
import 'business_command.dart';
import 'command_parser.dart';
import 'command_router.dart';
import 'command_validator.dart';
import 'local_llm_chat.dart';
import 'local_llm_command_extractor.dart';
import 'local_model_manager.dart';
import 'model_downloader.dart';
import 'voice_input_controller.dart';

class AssistantHistoryEntry {
  final String text;
  final bool isError;

  /// Solo true para el mensaje de RESULTADO de un comando que realmente se
  /// interpreto con el modelo local (no el eco del texto del usuario, ni un
  /// resultado producido por el parser determinista). Nunca se marca en
  /// true para un fallback, sin importar la razon del fallback.
  final bool usedLocalAi;

  /// true para lo que escribio o dijo la persona; false para las respuestas del asistente.
  final bool isUser;

  /// true para el aviso "Pensando…" mientras el asistente trabaja (no es una respuesta: sin etiqueta de origen).
  final bool isPending;

  const AssistantHistoryEntry(
    this.text, {
    this.isError = false,
    this.usedLocalAi = false,
    this.isUser = false,
    this.isPending = false,
  });
}

/// Punto de entrada global del asistente consciente del esquema. Acepta
/// texto escrito (siempre disponible) y, en plataformas nativas
/// compatibles, entrada hablada que se transcribe a texto y se procesa por
/// exactamente el mismo pipeline de interpretación — la voz nunca se salta
/// la validación.
///
/// Si hay un modelo GGUF local listo (LocalModelManager), se intenta
/// primero interpretar el texto con LocalLlmCommandExtractor; ante
/// CUALQUIER fallo (modelo no configurado, error de carga, timeout, JSON
/// malformado, forma invalida) se cae automaticamente al CommandParser
/// determinista existente, que sigue siendo el camino obligatorio cuando no
/// hay modelo local. Todo lo que ocurre despues de obtener un
/// BusinessCommand — validacion, ejecucion, confirmacion de DELETE en dos
/// fases — es exactamente el mismo camino sin cambios, sin importar de cual
/// de los dos caminos vino el comando.
class AssistantView extends StatefulWidget {
  /// Only meant for tests: injects a CommandRouter (e.g. backed by fake
  /// adapters) instead of the real one, so failure paths can be exercised
  /// without a live service/database. Production code should never pass
  /// this.
  final CommandRouter? router;

  /// Only meant for tests: injects a LocalModelManager (e.g. one whose
  /// state/engine is fully controlled by the test) instead of the real one.
  /// Production code should never pass this.
  final LocalModelManager? modelManager;

  /// Only meant for tests: creates an owned manager whose disposal can be
  /// observed without exposing production internals.
  final LocalModelManager Function()? modelManagerFactory;

  /// Only meant for tests: injects the conversation with the local AI (e.g. with a fake inference).
  final LocalLlmChat? chat;

  const AssistantView({
    super.key,
    this.router,
    this.modelManager,
    this.modelManagerFactory,
    this.chat,
  });

  @override
  State<AssistantView> createState() => _AssistantViewState();
}

class _AssistantViewState extends State<AssistantView> {
  final _controller = TextEditingController();
  final _scroll = ScrollController();
  final _parser = CommandParser();
  final _validator = CommandValidator();
  late final CommandRouter _router = widget.router ?? CommandRouter();
  late final bool _ownsModelManager = widget.modelManager == null;
  late final LocalModelManager _modelManager =
      widget.modelManager ??
      widget.modelManagerFactory?.call() ??
      LocalModelManager();
  late final LocalLlmCommandExtractor _localLlmExtractor =
      LocalLlmCommandExtractor(_modelManager);
  late final LocalLlmChat _chat = widget.chat ?? LocalLlmChat(_modelManager);
  String? _lastUserText;
  final _voice = VoiceInputController();
  final List<AssistantHistoryEntry> _history = [];
  bool _voiceAvailable = false;
  bool _isListening = false;
  bool _isBusy = false;

  @override
  void initState() {
    super.initState();
    _voice.onProblem = _showVoiceProblem;
    _initVoice();
    _modelManager.addListener(_onModelManagerChanged);
    unawaited(_modelManager.initialize());
  }

  void _onModelManagerChanged() {
    if (mounted) setState(() {});
  }

  void _showVoiceProblem(String message) {
    if (!mounted) return;
    setState(() => _isListening = false);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), duration: const Duration(seconds: 7)),
    );
  }

  Future<void> _initVoice() async {
    if (kIsWeb) return;
    final available = await _voice.initialize();
    if (mounted) setState(() => _voiceAvailable = available);
  }

  @override
  void dispose() {
    _modelManager.removeListener(_onModelManagerChanged);
    if (_ownsModelManager) _modelManager.dispose();
    _voice.dispose();
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  /// Lo que el asistente cuenta de su IA cuando le preguntan "¿eres una IA?": sale del estado real del modelo.
  AssistantAiState get _aiState {
    if (_modelManager.isDownloading) return AssistantAiState.downloading;
    switch (_modelManager.state) {
      case LocalModelState.ready:
        return AssistantAiState.ready;
      case LocalModelState.loading:
        return AssistantAiState.loading;
      case LocalModelState.notConfigured:
      case LocalModelState.error:
        return AssistantAiState.none;
    }
  }

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isBusy) return;
    setState(() {
      _isBusy = true;
      _history.add(AssistantHistoryEntry(text, isUser: true));
    });
    _scrollToEnd();
    _controller.clear();

    _lastUserText = text;
    final aiReady = _modelManager.state == LocalModelState.ready;
    // Sin IA (o con la ayuda, que es un texto exacto), saludos, gracias y ayuda se contestan con textos fijos:
    // "hola" nunca es una consulta.
    if (!aiReady || AssistantTexts.isHelpRequest(text)) {
      final smallTalk = AssistantTexts.smallTalkReply(text, ai: _aiState);
      if (smallTalk != null) {
        _appendResult(smallTalk);
        return;
      }
    }
    // "por favor, lista todos los empleados": sin cortesias ni rodeos para que lo entienda el interprete.
    final commandText = AssistantTexts.orderText(text);

    // Con la IA lista, lo que no es una orden sobre los datos es conversacion: la responde el modelo.
    var aiTried = false;
    if (aiReady && !AssistantTexts.looksLikeOrder(text)) {
      aiTried = true;
      if (await _talkWithAi(text)) return;
    }

    try {
      BusinessCommand? command;
      var usedLocalAi = false;

      if (_modelManager.state == LocalModelState.ready) {
        final llmResult = await _localLlmExtractor.extract(commandText);
        if (llmResult.isSuccess) {
          command = llmResult.command;
          usedLocalAi = true;
        }
        // Cualquier fallo del modelo local (incluido llmResult.error) cae
        // silenciosamente al parser determinista debajo: nunca se le
        // muestra al usuario un error de inferencia local por separado del
        // resultado final.
      }

      final parsed = command == null ? _parser.parse(commandText) : null;
      if (command == null) {
        if (!parsed!.isSuccess) {
          // Ni el modelo ni las reglas entendieron una orden: con la IA lista se conversa en vez de rendirse.
          if (aiReady && !aiTried && await _talkWithAi(text)) return;
          // El mensaje tecnico del interprete ("No conozco la entidad ...") se cambia por ayuda con ejemplos.
          _appendResult(AssistantTexts.notUnderstood());
          return;
        }
        command = parsed.command!;
        usedLocalAi = false;
      }

      final validated = _validator.validate(command);
      if (!validated.isValid) {
        _appendResult(validated.error!, isError: true, usedLocalAi: usedLocalAi);
        return;
      }

      final validCommand = validated.command!;
      if (validCommand.action == CommandAction.delete) {
        final outcome = await _router.execute(validCommand);
        if (!outcome.success || outcome.pendingDelete == null) {
          _appendResult(outcome.message, isError: !outcome.success, usedLocalAi: usedLocalAi);
          return;
        }
        if (!mounted) return;
        final confirmed = await _confirmDelete(outcome.pendingDelete!);
        if (confirmed != true) {
          _appendResult('Eliminación cancelada.');
          return;
        }
        final result = await _router.confirmDelete(outcome.pendingDelete!);
        _appendResult(result.message, isError: !result.success, usedLocalAi: usedLocalAi);
        return;
      }

      final outcome = await _router.execute(validCommand);
      _appendResult(outcome.message, isError: !outcome.success, usedLocalAi: usedLocalAi);
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

  /// Responde con el modelo local. Devuelve false si no pudo (sin modelo, error o tiempo agotado) para que el
  /// llamador siga por el camino de siempre.
  Future<bool> _talkWithAi(String text) async {
    final context = await _dataContextFor(text);
    final answer = await _chat.reply(text, dataContext: context);
    if (answer == null || !mounted) return false;
    _appendResult(answer, usedLocalAi: true, remember: false);
    return true;
  }

  /// Datos reales que la IA necesita para contestar sobre ellos: de cada entidad que la persona nombra, cuantos
  /// registros hay y como se llaman. Nunca falla: si no se pueden leer, la IA contesta sin ellos.
  Future<String> _dataContextFor(String text) async {
    final mentioned = <AssistantEntitySchema>{};
    for (final word in text.split(RegExp(r'[^\\wáéíóúñüÁÉÍÓÚÑÜ]+'))) {
      if (word.isEmpty) continue;
      final entity = AppSchema.resolveEntity(word);
      if (entity != null) mentioned.add(entity);
    }
    final lines = <String>[];
    for (final entity in mentioned) {
      try {
        final outcome = await _router.execute(
          BusinessCommand(
            action: CommandAction.read,
            entity: entity.name,
            data: const {},
            filters: const {},
            rawText: text,
          ),
        );
        if (outcome.success) lines.add(AssistantTexts.dataFacts(entity, outcome.rows));
      } catch (_) {
        // sin datos: la IA responde sin ellos
      }
    }
    return lines.join('\\n');
  }

  void _appendResult(String message, {bool isError = false, bool usedLocalAi = false, bool remember = true}) {
    if (!mounted) return;
    final userText = _lastUserText;
    if (remember && !isError && userText != null) _chat.remember(userText, message);
    setState(() {
      _history.add(AssistantHistoryEntry(message, isError: isError, usedLocalAi: usedLocalAi));
      _isBusy = false;
    });
    _scrollToEnd();
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
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

  Widget _statusRow({
    Widget? leading,
    required String text,
    Color? color,
    String? tooltip,
    List<(String, VoidCallback)> actions = const [],
  }) {
    final style = Theme.of(context).textTheme.bodySmall?.copyWith(color: color);
    Widget label = Text(text, style: style, overflow: TextOverflow.ellipsis);
    if (tooltip != null) label = Tooltip(message: tooltip, child: label);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Row(
        children: [
          if (leading != null) ...[leading, const SizedBox(width: 8)],
          Expanded(child: label),
          for (final (caption, onPressed) in actions)
            TextButton(
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              onPressed: onPressed,
              child: Text(caption, style: const TextStyle(fontSize: 12)),
            ),
        ],
      ),
    );
  }

  Future<void> _confirmDownload() async {
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Descargar la IA local'),
        content: const Text(
          'Se descargará el modelo de IA (unos 1,1 GB) una sola vez. Conviene usar Wi-Fi. '
          'Después el asistente conversa sin internet.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Descargar')),
        ],
      ),
    );
    if (accepted == true) unawaited(_modelManager.downloadDefaultModel());
  }

  Widget _buildLocalAiStatus() {
    final scheme = Theme.of(context).colorScheme;
    if (_modelManager.isDownloading) {
      final progress = _modelManager.downloadProgress;
      final percent = progress == null ? '' : ' ${(progress * 100).round()} %';
      return _statusRow(
        leading: SizedBox(
          width: 14,
          height: 14,
          child: CircularProgressIndicator(strokeWidth: 2, value: progress),
        ),
        text: 'Descargando la IA local…$percent',
        actions: [('Cancelar', _modelManager.cancelDownload)],
      );
    }
    switch (_modelManager.state) {
      case LocalModelState.notConfigured:
        return _statusRow(
          leading: Icon(Icons.auto_awesome_outlined, size: 14, color: scheme.outline),
          text: 'IA local: sin modelo',
          actions: [
            ('Descargar IA local', _confirmDownload),
            ('Elegir modelo', _modelManager.selectAndImportModel),
          ],
        );
      case LocalModelState.loading:
        return _statusRow(
          leading: const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2)),
          text: 'Preparando la IA local…',
        );
      case LocalModelState.ready:
        // Quien ya tiene un modelo anterior (mas pequeno, solo servia para interpretar ordenes) puede bajar el actual,
        // que conversa mejor. Si esa descarga falla, el modelo que ya funciona sigue y se avisa en esta misma fila.
        final canUpgrade = _modelManager.modelFileNameLabel != ModelDownloader.defaultFileName;
        final problem = _modelManager.downloadError;
        return _statusRow(
          leading: Icon(problem == null ? Icons.check_circle : Icons.error_outline, size: 14, color: problem == null ? scheme.primary : scheme.error),
          text: problem ?? 'IA local lista',
          color: problem == null ? null : scheme.error,
          tooltip: _modelManager.modelFileNameLabel,
          actions: [
            if (canUpgrade) ('Descargar IA mejorada', _confirmDownload),
            ('Cambiar modelo', _modelManager.selectAndImportModel),
          ],
        );
      case LocalModelState.error:
        return _statusRow(
          leading: Icon(Icons.error_outline, size: 14, color: scheme.error),
          text: _modelManager.downloadError ?? 'IA local no disponible',
          color: scheme.error,
          actions: [
            ('Descargar IA local', _confirmDownload),
            ('Elegir modelo', _modelManager.selectAndImportModel),
          ],
        );
    }
  }

  Widget _buildBubble(AssistantHistoryEntry entry) {
    final scheme = Theme.of(context).colorScheme;
    final isUser = entry.isUser;
    final background = isUser
        ? scheme.primaryContainer
        : (entry.isError ? scheme.errorContainer : scheme.surfaceContainerHighest);
    final foreground = isUser
        ? scheme.onPrimaryContainer
        : (entry.isError ? scheme.onErrorContainer : scheme.onSurface);
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: background,
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(18),
              topRight: const Radius.circular(18),
              bottomLeft: Radius.circular(isUser ? 18 : 4),
              bottomRight: Radius.circular(isUser ? 4 : 18),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (!isUser && !entry.isError && !entry.isPending)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(entry.usedLocalAi ? Icons.auto_awesome : Icons.rule, size: 12, color: foreground),
                      const SizedBox(width: 4),
                      Text(
                        entry.usedLocalAi ? 'IA local' : 'Respuesta de la app',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: foreground),
                      ),
                    ],
                  ),
                ),
              Text(entry.text, style: TextStyle(color: foreground)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildWelcome() {
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 32, 24, 16),
      children: [
        Icon(Icons.auto_awesome, size: 40, color: theme.colorScheme.primary),
        const SizedBox(height: 12),
        Text('\\u00bfEn qué te ayudo?', textAlign: TextAlign.center, style: theme.textTheme.headlineSmall),
        const SizedBox(height: 8),
        Text(
          'Escribe o dime lo que necesitas, con tus palabras. Por ejemplo:',
          textAlign: TextAlign.center,
          style: theme.textTheme.bodyMedium,
        ),
        const SizedBox(height: 16),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final suggestion in AssistantTexts.suggestions())
              ActionChip(
                label: Text(suggestion),
                onPressed: () {
                  _controller.text = suggestion;
                  _controller.selection = TextSelection.collapsed(offset: suggestion.length);
                },
              ),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Asistente')),
      body: Column(
        children: [
          _buildLocalAiStatus(),
          const Divider(height: 1),
          Expanded(
            child: _history.isEmpty
                ? _buildWelcome()
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(12),
                    itemCount: _history.length + (_isBusy ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == _history.length) {
                        return _buildBubble(const AssistantHistoryEntry('Pensando…', isPending: true));
                      }
                      return _buildBubble(_history[index]);
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
                      hintText: 'Escribe o dime lo que necesitas…',
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

            router_test_blocks.append('''  test('AppSchema.normalize() treats common dash/hyphen variants as a plain space (voice-recognition artifact, e.g. iOS dictating "Coca-Cola")', () {
    final base = AppSchema.normalize('Coca cola');
    expect(base, 'coca cola');
    expect(AppSchema.normalize('Coca-Cola'), base);
    expect(AppSchema.normalize('Coca‐Cola'), base);
    expect(AppSchema.normalize('Coca‑Cola'), base);
    expect(AppSchema.normalize('Coca‒Cola'), base);
    expect(AppSchema.normalize('Coca–Cola'), base);
    expect(AppSchema.normalize('Coca—Cola'), base);
    expect(AppSchema.normalize('Coca―Cola'), base);
  });''')

            router_test_blocks.append('''  test('AppSchema.normalize() collapses repeated whitespace left by dash substitution into a single space', () {
    expect(AppSchema.normalize('Coca---Cola'), 'coca cola');
    expect(AppSchema.normalize('Coca   cola'), 'coca cola');
  });''')

            router_test_blocks.append(f"""  test('DELETE reuses the same normalized matching as UPDATE (AppSchema.normalize) to find a dash-written filter against a space-stored value', () async {{
    final adapter = _FakeAdapter(schema, [
      {{pkJsonKey: {pk_seed_1}, nameJsonKey: 'Coca cola'}},
    ]);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final outcome = await router.execute(BusinessCommand(
      action: CommandAction.delete,
      entity: {entity_literal},
      data: const {{}},
      filters: {self._assistant_render_dart_map([(name_field, 'Coca-Cola')])},
      rawText: 'test',
    ));
    expect(outcome.success, isTrue);
    expect(outcome.pendingDelete, isNotNull);
    expect(outcome.pendingDelete!.pk, {pk_string_1});
  }});""")

            # Datos de CREATE para el enrutador: los campos y relaciones OBLIGATORIOS de la entidad (si no, el test
            # falla en cualquier esquema donde la entidad elegida tenga una relacion obligatoria), mas los extra.
            router_create_data = list(self._assistant_required_create_data(subject))
            router_keys = {key for key, _ in router_create_data}
            router_create_data = [entry for entry in create_data if entry[0] not in router_keys] + router_create_data
            router_test_blocks.append(f"""  test('CREATE validates and sends values under normalized backend JSON keys, PK omitted', () async {{
    final adapter = _FakeAdapter(schema, []);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final validated = CommandValidator().validate(BusinessCommand(
      action: CommandAction.create,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map(router_create_data)},
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

            router_test_blocks.append(f"""  test('READ result message shows the actual matched field values dynamically, not just a count', () async {{
    // Seed a row using every scalar field the real schema defines for this
    // entity (besides the PK and name field, already set) with a distinct
    // sample value each -- so this proves the message is built dynamically
    // from AssistantEntitySchema/the returned row data, never from a fixed
    // field/entity name of any specific project.
    final row = <String, dynamic>{{pkJsonKey: {pk_seed_1}, nameJsonKey: 'Ejemplo Uno'}};
    final expectedSnippets = <String>['Ejemplo Uno'];
    var sampleNumber = 1;
    for (final field in schema.fields) {{
      if (field.isPrimaryKey || field.name == {self._assistant_dart_string_literal(name_field)}) continue;
      final dynamic value = switch (field.dartType) {{
        'int' => sampleNumber,
        'double' => sampleNumber.toDouble(),
        'bool' => true,
        _ => 'Valor$sampleNumber',
      }};
      row[field.jsonKey] = value;
      expectedSnippets.add(value is bool ? 'sí' : '$value');
      sampleNumber++;
    }}

    final adapter = _FakeAdapter(schema, [row]);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final outcome = await router.execute(BusinessCommand(
      action: CommandAction.read,
      entity: {entity_literal},
      data: const {{}},
      filters: {self._assistant_render_dart_map([(name_field, 'Ejemplo Uno')])},
      rawText: 'test',
    ));

    expect(outcome.success, isTrue);
    for (final snippet in expectedSnippets) {{
      expect(outcome.message, contains(snippet));
    }}
  }});""")

            router_test_blocks.append(f"""  test('READ result message handles zero and multiple matches compactly', () async {{
    final adapter = _FakeAdapter(schema, [
      {{pkJsonKey: {pk_seed_1}, nameJsonKey: 'Ejemplo Uno'}},
      {{pkJsonKey: {pk_seed_2}, nameJsonKey: 'Ejemplo Dos'}},
      {{pkJsonKey: 3, nameJsonKey: 'Ejemplo Tres'}},
      {{pkJsonKey: 4, nameJsonKey: 'Ejemplo Cuatro'}},
      {{pkJsonKey: 5, nameJsonKey: 'Ejemplo Cinco'}},
      {{pkJsonKey: 6, nameJsonKey: 'Ejemplo Seis'}},
    ]);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});

    final noMatch = await router.execute(BusinessCommand(
      action: CommandAction.read,
      entity: {entity_literal},
      data: const {{}},
      filters: {self._assistant_render_dart_map([(name_field, 'No Existe')])},
      rawText: 'test',
    ));
    expect(noMatch.success, isTrue);
    expect(noMatch.message, contains('No encontré'));

    final allRows = await router.execute(BusinessCommand(
      action: CommandAction.read,
      entity: {entity_literal},
      data: const {{}},
      filters: const {{}},
      rawText: 'test',
    ));
    expect(allRows.success, isTrue);
    expect(allRows.message, contains('Ejemplo Uno'));
    expect(allRows.message, contains('Ejemplo Dos'));
    expect(allRows.message, contains('Ejemplo Cinco'));
    expect(allRows.message, isNot(contains('Ejemplo Seis')));
    expect(allRows.message, contains('y 1 más.'));
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

                router_test_blocks.append(f"""  test('UPDATE finds a row stored with a plain space using a filter written with a dash (iOS dictation artifact)', () async {{
    final adapter = _FakeAdapter(schema, [
      {{pkJsonKey: {pk_seed_1}, nameJsonKey: 'Coca cola'}},
    ]);
    final router = CommandRouter(registry: {{{entity_literal}: adapter}});
    final validated = CommandValidator().validate(BusinessCommand(
      action: CommandAction.update,
      entity: {entity_literal},
      data: {self._assistant_render_dart_map([(update_field['name'], update_raw)])},
      filters: {self._assistant_render_dart_map([(name_field, 'Coca-Cola')])},
      rawText: 'test',
    ));
    expect(validated.isValid, isTrue, reason: validated.error);
    final outcome = await router.execute(validated.command!);
    expect(outcome.success, isTrue);
    expect(adapter.updateCalls, 1);
    expect(adapter.lastUpdatedId, {pk_string_1});
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
    def _rel_field(self, rel):
        """Nombre del campo que la relación agrega a su clase (el de Spring, sin separadores, al pasar por _to_backend_json_key).

        Por defecto es el nombre de la clase destino; una relación recursiva o repetida lleva uno propio (padre, hijos,
        aeropuerto2) porque dos campos con el mismo nombre no compilan. Lo calcula _parse_relationships."""
        return rel.get("field") or self._to_snake_case(rel["to"])

    def _rel_var(self, rel):
        """Sufijo de las variables de estado del formulario de una relación: la clase destino, salvo nombre propio."""
        field = self._rel_field(rel)
        if field == self._to_snake_case(rel["to"]):
            return rel["to"]
        return "".join(part[:1].upper() + part[1:] for part in field.split("_"))

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
