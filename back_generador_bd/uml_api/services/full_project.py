"""Descarga unica: backend (Spring Boot) + app movil (Flutter) + script SQL + instrucciones, todo a partir del diagrama.

El generador de Spring es un servicio aparte (otro contenedor): aqui se llama por HTTP con `fetch_spring_zip`; en las
pruebas se inyecta una funcion falsa, asi el armado del ZIP se prueba sin servidor.
"""
import io
import re
import tempfile
import unicodedata
import zipfile
from pathlib import Path

import requests
from django.conf import settings

from .flutter_generator import FlutterCRUDGenerator
from .uml_kinds import code_entities


class SpringUnavailable(Exception):
    """El generador de backend (Spring Boot) no respondio o devolvio un error."""


def fetch_spring_zip(payload):
    """Pide al generador de Spring el ZIP del backend para el diagrama `payload` ({classes, relationships})."""
    try:
        response = requests.post(settings.SPRING_GENERATOR_URL, json=payload, timeout=180)
        response.raise_for_status()
    except requests.RequestException as error:
        raise SpringUnavailable(str(error)) from error
    return response.content


def _slug(name):
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or "mi-aplicacion"


def _readme(app_name, entities, has_sql):
    entity_lines = "\n".join(f"- {name}" for name in entities)
    sql_line = (
        "- `base_de_datos/esquema.sql`: script SQL (PostgreSQL) del diagrama.\n" if has_sql else ""
    )
    return f"""# {app_name}

Proyecto generado desde el diagrama de clases. Contiene:

- `backend/`: API REST en Spring Boot 3.5 (Java 21) con PostgreSQL y la colección de Postman.
- `app_movil/`: aplicación Flutter (iPhone y Android) con base local SQLite, que funciona sin conexión, y un asistente
  con IA local.
{sql_line}
## Entidades del diagrama

{entity_lines}

## 1. Base de datos y backend

1. Crea una base de datos PostgreSQL vacía{" y ejecuta `base_de_datos/esquema.sql`" if has_sql else ""}.
2. Entra a `backend/`, ajusta la conexión a PostgreSQL en `src/main/resources/application.properties` y ejecuta
   (necesita Java 21 y Maven instalados): `mvn spring-boot:run`
3. Importa `backend/generated-app-postman-collection.json` en Postman para probar la API.

## 2. Aplicación móvil

Necesitas Flutter 3.38 o más nuevo y, para iPhone, Xcode.

```bash
cd app_movil
flutter create . --platforms=ios,android --org com.tuorganizacion
flutter pub get
sh tool/configure_ios_local_ai.sh   # permisos de voz, iOS 16.4, nombre e icono de la app
flutter run --release               # con el teléfono conectado
```

En iPhone, la primera vez abre `ios/Runner.xcworkspace` en Xcode y elige tu equipo de desarrollo en
Signing & Capabilities.

## 3. IA local (sin internet)

El asistente funciona sin la IA local con un intérprete básico. Para activarla, abre el **Asistente** y toca
**«Descargar IA local»** (una sola vez, necesita internet y ~0,5 GB). También puedes tocar **«Elegir modelo»** y
seleccionar un archivo `.gguf`. Después responde sin conexión.

Para usar la voz sin internet, descarga el dictado en español en el teléfono
(Ajustes > General > Teclado > Dictado).
"""


def build_full_project_zip(uml_json, spring_fetch):
    """Devuelve (bytes del ZIP, nombre de archivo). `spring_fetch(payload)` devuelve el ZIP del backend o lanza
    SpringUnavailable."""
    uml_json = code_entities(uml_json)  # las interfaces y las enumeraciones no son tablas ni entidades
    app_name = " ".join(str(uml_json.get("appName") or uml_json.get("projectName") or "").split())[:40]
    app_name = app_name or FlutterCRUDGenerator.DEFAULT_APP_NAME
    sql_script = str(uml_json.get("sqlScript") or "").strip()
    diagram = {"classes": uml_json.get("classes", []), "relationships": uml_json.get("relationships", [])}

    backend_zip = spring_fetch(diagram)  # primero lo que puede fallar por red

    with tempfile.TemporaryDirectory() as temp:
        project_dir = Path(temp) / "app_movil"
        FlutterCRUDGenerator(dict(uml_json, appName=app_name)).generate_project(output_dir=project_dir)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            entities = [c["name"] for c in diagram["classes"]]
            archive.writestr("LEEME.md", _readme(app_name, entities, bool(sql_script)))
            try:
                with zipfile.ZipFile(io.BytesIO(backend_zip)) as backend:
                    for member in backend.infolist():
                        if member.is_dir():
                            continue
                        archive.writestr(f"backend/{member.filename}", backend.read(member))
            except zipfile.BadZipFile as error:
                raise SpringUnavailable("el generador de backend no devolvio un ZIP valido") from error
            for path in sorted(project_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, f"app_movil/{path.relative_to(project_dir).as_posix()}")
            if sql_script:
                archive.writestr("base_de_datos/esquema.sql", sql_script + "\n")
    return buffer.getvalue(), f"{_slug(app_name)}.zip"
