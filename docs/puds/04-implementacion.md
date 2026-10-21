# Disciplina de Implementación

Artefactos: **modelo de implementación** (componentes y su relación con las clases de diseño), **plan de integración de construcciones** y **convenciones**.

## 1. Modelo de implementación

| Componente | Ruta | Tecnología | Realiza (diseño) | Pruebas |
|---|---|---|---|---|
| Editor y servicios de diagrama | `front_generador_bd/src/app/diagram`, `src/services/diagram/` | Angular 20, JointJS | Edición de diagramas, entidad intermedia, clase asociativa | `diagram.service*.spec.ts`, `association-class.util.spec.ts`, `edition.service.spec.ts` |
| Panel lateral | `front_generador_bd/src/app/side-panel` | Angular, Tailwind | Edición de nombre, atributos, métodos y multiplicidades | — |
| Colaboración (cliente) | `front_generador_bd/src/services/colaboration/` | TypeScript, WebSocket | Señalización, presencia, operaciones, estado completo | `signaling`, `p2p.*`, `collaboration.service.spec.ts`, `ws-host.util.spec.ts` |
| Panel de participantes | `front_generador_bd/src/app/participants-panel` | Angular | Presencia, roles, expulsión | `p2p.roles.spec.ts` |
| Exportaciones | `front_generador_bd/src/services/exports/` | TypeScript | SQL, imagen, respaldo, llamada al generador Spring | `sql-export.service.spec.ts`, `backend-generator.service.spec.ts` |
| XMI (cliente) | `front_generador_bd/src/services/interop/xmi.service.ts` | TypeScript | Exportar e importar XMI | `xmi.service.spec.ts` |
| IA asistida (cliente) | `front_generador_bd/src/services/IA/`, `src/services/imports/` | TypeScript | Texto, imagen y voz | — |
| API Django | `back_generador_bd/uml_api/` | Django 5, DRF | IA con Gemini, respaldo, XMI, Flutter | `uml_api/tests/` |
| Colaboración (servidor) | `back_generador_bd/collab/` | Channels, Daphne, Redis | `CanvasConsumer`, roles, (I1) identidad y actividad | `collab/tests/` |
| XMI (servidor) | `back_generador_bd/uml_api/services/xmi_service.py` | Python | Convertir diagrama ↔ XMI 2.1 con seguridad XXE | `test_xmi_*.py` |
| Generador Flutter | `back_generador_bd/uml_api/services/flutter_generator.py` | Python | Proyecto Flutter con SQLite y asistente local | `test_flutter_generator.py` |
| Generador Spring | `back_generator_uml/` | Spring Boot 3.5, Java 21, Mustache | Proyecto Spring + PostgreSQL + Postman | `ProjectGeneratorCompileTest`, `SecurityConfiguration*Test` |
| Orquestación | `docker-compose.app.yml`, `docker-compose.db.yml`, `back_generador_bd/docker-compose.yml`, `Dockerfile` por servicio | Docker Compose | Modelo de despliegue | Prueba de humo ([`../DESPLIEGUE.md`](../DESPLIEGUE.md)) |

## 2. Plan de integración de construcciones

Cada iteración produce una **construcción** que se integra en `develop`. Reglas (de [`AGENTS.md`](../../AGENTS.md)):

1. Una rama por tarea (`feat/…`, `fix/…`, `docs/…`); un agente o persona por rama.
2. Commits pequeños y con un solo propósito; no se reescribe historia compartida.
3. Antes de integrar: compila, pasan las pruebas relevantes y no hay secretos (`.env`, claves, contraseñas) en el cambio.
4. Se integra con *merge* a `develop` y se sube; el despliegue se hace desde `develop` siguiendo el runbook.
5. Si cambia el estado de un requisito, se actualiza `docs/GAP_MATRIX.md`.

| Construcción | Contenido | Estado |
|---|---|---|
| C0 | Línea base del primer parcial (`baseline-fournext` + correcciones de colaboración, XMI, Flutter, Spring) | ✅ |
| C1 | Entidad intermedia M:N con revisión de hallazgos (asociación solo; paralelas y reflexivas; restauración; operaciones colaborativas), endpoints en tiempo de ejecución, CORS configurable de Spring, despliegue con dominio y HTTPS | ✅ en `develop` |
| C2 | I1: identidad de participantes y registro de actividad (backend + panel) | 🔄 rama `feat/identidad-actividad` |
| C3 | I2: chat individual con la IA | 📋 |
| C4 | I3: acciones, sugerencias y revisión | 📋 |
| C5 | I4 y I5: sesiones continuas y vista móvil | 📋 |
| C6 | I7: congelamiento, despliegue final y entrega | 📋 |

## 3. Convenciones

- **Frontend:** componentes independientes de Angular con señales; Tailwind para estilos; sin acceso a `window` ni `localStorage` al cargar el módulo (compatibilidad con renderizado en servidor).
- **Backend:** vistas DRF o JSON simples en el estilo de `uml_api/views.py`; persistencia y almacenes inyectables para poder probar sin base de datos.
- **Mensajes de colaboración:** se añaden campos nuevos sin cambiar los existentes; los clientes que no los conocen los ignoran.
- **Puertos:** 4200 (Angular), 4000 (Angular en contenedor), 8000 (Django), 6379 (Redis), 5433 (PostgreSQL en el host), 5432 (en el contenedor), 7001 (Spring). No se cambian sin una razón concreta.
- **Secretos:** solo en archivos `.env` fuera de git; la documentación nombra las variables, nunca sus valores.
- **Comentarios de código:** en español, explicando el porqué cuando no es evidente.

## 4. Cómo construir y ejecutar

| Qué | Comando |
|---|---|
| Frontend (compilar) | `cd front_generador_bd && npx --no-install ng build` |
| Frontend (pruebas) | `cd front_generador_bd && npx --no-install ng test --watch=false --browsers=ChromeHeadless --no-progress` |
| Django (pruebas sin base de datos) | `back_generador_bd/.venv/bin/python back_generador_bd/manage.py test <etiqueta>` |
| Django (pruebas con base de datos) | `docker exec django_backend_UML python manage.py test` |
| Spring (pruebas) | `cd back_generator_uml && ./mvnw test` |
| Stack completo | `docker-compose -f docker-compose.db.yml up -d` y luego `docker-compose -f docker-compose.app.yml up -d --build` |
