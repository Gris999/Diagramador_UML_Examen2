# Disciplina de Prueba

Artefactos: **plan de prueba**, **casos de prueba**, **procedimientos de prueba**, **defectos** y **evaluación de prueba**.

## 1. Plan de prueba

### 1.1 Estrategia

| Nivel | Qué se verifica | Herramienta | Cuándo |
|---|---|---|---|
| Unidad | Servicios del cliente, utilidades puras, servicios Python | Jasmine/Karma (Angular), `manage.py test` (Django), JUnit (Spring) | En cada cambio |
| Integración | WebSocket con `WebsocketCommunicator` y almacenes simulados; generadores de punta a punta; compilación real del proyecto Spring generado | Django, JUnit | En cada cambio que toque colaboración o generadores |
| Sistema | Dos o tres navegadores en la misma sala; Enterprise Architect; generación y ejecución del proyecto Flutter | Prueba física con el navegador y las herramientas externas | Al cerrar cada iteración |
| Despliegue | El sitio responde, el WebSocket negocia, los puertos internos están cerrados | `curl`, `nc`, navegador | Después de cada despliegue |

Críticos que **exigen** pruebas automáticas (`AGENTS.md`): importación/exportación XMI, colaboración y sincronización, permisos y roles, reconexión y recuperación de estado, generadores de código, transformaciones UML y persistencia offline.

### 1.2 Criterios

- **Entrada de una iteración a `develop`:** compila, pasan las pruebas relevantes, sin secretos en el cambio, sin regresiones en roles/expulsión/XMI/exportaciones.
- **Aceptación de cada iteración:** los criterios de la sección 8 del [plan](../PLAN_PUDS_IA_PARTICIPANTE.md) verificados con evidencia.
- **Ejecución de las pruebas que usan base de datos:** dentro del contenedor de Django; no se considera fallo de la aplicación que el host de macOS no resuelva el nombre `postgres`.

## 2. Casos de prueba

| ID | CU | Entradas / acciones | Resultado esperado | Evidencia |
|---|---|---|---|---|
| CP-01 | CU-14 | Tres navegadores entran a la misma sala | El primero es host, el resto participantes; todos convergen al mismo diagrama | Prueba física con 3 clientes (GAP_MATRIX); `collab/tests/test_roles.py` |
| CP-02 | CU-15 | Un no-host intenta expulsar | El servidor rechaza (`remove_rejected`); nadie sale | `test_roles.py`; prueba física |
| CP-03 | CU-15 | El host expulsa a un participante | Se cierra su conexión y la presencia se actualiza | `test_roles.py`; prueba física |
| CP-04 | CU-14 | El host se desconecta | El participante más antiguo es host; al reconectar, el anterior entra como participante | `test_roles.py`; prueba física |
| CP-05 | CU-14 | Un participante borra una clase y otro recarga | La clase borrada no reaparece; sus relaciones desaparecen y las demás se conservan | Validación física con dos pestañas |
| CP-06 | CU-10 | Dibujar asociación con `*` en ambos extremos | Se crea la entidad intermedia `A_B` con `id: int` y dos relaciones 1:N | `diagram.service.junction.spec.ts` |
| CP-07 | CU-10 | Dos M:N paralelas entre las mismas clases; una M:N reflexiva | Entidades distintas (`A_B`, `A_B_2`); la reflexiva genera dos patas | `diagram.service.junction.spec.ts` |
| CP-08 | CU-10 | Agregación, composición o dependencia con `*` en ambos extremos | No se transforman | `diagram.service.junction.spec.ts` |
| CP-09 | CU-10 | Editar la multiplicidad de una pata generada para que deje de ser "muchos" | Se restaura la asociación original; no desaparece ninguna relación | `diagram.service.junction.spec.ts` |
| CP-10 | CU-10 / CU-14 | Crear M:N con dos clientes conectados | Ambos tienen las mismas entidades y marcas; aplicar dos veces no duplica | `collaboration.service.spec.ts` |
| CP-11 | CU-16 | Exportar un diagrama con clase asociativa | La exportación no falla y omite los conectores auxiliares | `xmi.service.spec.ts` |
| CP-12 | CU-16 / CU-17 | Ida y vuelta con Enterprise Architect 17.2 | Clases, atributos, operaciones, asociaciones y multiplicidades se conservan | Validación física (GAP_MATRIX); `test_xmi_enterprise_architect.py` |
| CP-13 | CU-17 | Importar XMI con `DOCTYPE`/entidad externa | Se rechaza sin leer archivos ni abrir conexiones | `test_xmi_service.py`, `test_xmi_api.py` |
| CP-14 | CU-18 | Generar el backend de un diagrama | Se descarga un `.zip` que compila con Maven | `ProjectGeneratorCompileTest` |
| CP-15 | CU-19 | Generar Flutter con M:N y entidad intermedia | El código generado es coherente (sin referencias a campos inexistentes) | `test_flutter_generator.py` |
| CP-16 | CU-19 | Ejecutar la app Flutter generada sin red | El CRUD funciona y los datos persisten | Validación física en dispositivo |
| CP-17 | CU-20 | Exportar a imagen | Fondo claro, diagrama visible y sin elementos de la aplicación | Validación física |
| CP-18 | CU-01 | Entrar con nombre; un tercero entra después | Los nombres aparecen para todos, incluido el que llega tarde | 🔄 Pruebas de `hello` y presencia (I1) |
| CP-19 | CU-02 | Un participante agrega una clase | El evento aparece en la actividad de todos | 🔄 Aceptación I1 |
| CP-20 | CU-02 | Mover/redimensionar; editar texto repetido en 5 s | No se registran; la edición repetida es un solo evento | 🔄 Pruebas de lista blanca y fusión (I1) |
| CP-21 | CU-01 | `hello` inválido o cliente sin `hello` | Se ignora sin cerrar el socket; el cliente sigue funcionando | 🔄 Pruebas (I1) |
| CP-22 | CU-03 | Dos personas usan su chat con la IA | Ninguna lee el chat de la otra | 📋 I2 |
| CP-23 | CU-03…05 | El proveedor de IA falla | Mensaje claro; el diagrama no cambia | 📋 I2/I3 |
| CP-24 | CU-04 | Modo Preguntar | El diagrama no cambia | 📋 I3 |
| CP-25 | CU-04 | Modo Pedir cambio | Cambio aplicado y visible para todos con la etiqueta "IA, a pedido de X" | 📋 I3 |
| CP-26 | — | Después de desplegar | HTTPS 200; WebSocket negocia (101); puertos 4200/7001/8000 cerrados al exterior | ✅ 2026-10-21 |

## 3. Procedimientos de prueba

1. **Frontend:** `cd front_generador_bd && npx --no-install ng build` y luego `npx --no-install ng test --watch=false --browsers=ChromeHeadless --no-progress`.
2. **Django sin base de datos:** `back_generador_bd/.venv/bin/python back_generador_bd/manage.py test collab uml_api.tests.test_services_gemini uml_api.tests.test_xmi_service uml_api.tests.test_xmi_layout uml_api.tests.test_flutter_generator` (con `DJANGO_SECRET_KEY` y `POSTGRES_PASSWORD` de prueba en el entorno).
3. **Django con base de datos:** `docker exec django_backend_UML python manage.py test`.
4. **Spring:** `cd back_generator_uml && ./mvnw test` (incluye la compilación real del proyecto generado).
5. **Sala con varios navegadores:** abrir la misma sala en 2–3 ventanas; verificar roles, edición, borrado, recarga y expulsión.
6. **Despliegue:** `curl -sI https://diagramador.dev/`, negociación del WebSocket y `nc -z` a 4200/7001/8000 desde fuera (deben fallar). Pasos completos en [`../DESPLIEGUE.md`](../DESPLIEGUE.md).

## 4. Defectos conocidos

| ID | Defecto | Impacto | Estado |
|---|---|---|---|
| D-01 | Tres pruebas del frontend fallan desde antes del trabajo actual: `App should render title`, `Diagram should create`, `LandinPage should create` (falta Zone.js en la configuración de pruebas / texto esperado desactualizado) | Ninguno en producción; ruido en el resultado | 📋 Por corregir |
| D-02 | La contraseña anterior de PostgreSQL sigue en el historial público de git | Riesgo si se reutiliza en otro sitio | Mitigado: ya no está en el compose; cambiar la contraseña si se usó en otro lugar |
| D-03 | Las pruebas de Django que necesitan base de datos no corren en el host de macOS | Hay que correrlas en el contenedor | Documentado |

## 5. Evaluación de prueba *(corte del 2026-10-21, `develop`)*

| Suite | Resultado | Comando |
|---|---|---|
| Frontend (Karma) | 93 ejecutadas: **90 correctas**, 3 fallan (D-01) | `ng test` (rama `fix/junction-revision`, ya integrada) |
| Frontend (compilación) | Correcta, con 2 avisos de módulos CommonJS (`backbone`, `file-saver`) | `ng build` |
| Django sin base de datos | **60 correctas**, 0 fallos (colaboración 6, Gemini 7, XMI 14, diseño de XMI 1, Flutter 32) | ver procedimiento 2 |
| Spring | Cubierto por `ProjectGeneratorCompileTest` y las pruebas de CORS | Verificado en iteraciones anteriores; se vuelve a ejecutar antes del congelamiento |
| Sitio desplegado | HTTPS 200, WebSocket 101, 4200/7001/8000 cerrados | Pruebas de humo del 2026-10-21 |

**Pendiente antes de la entrega:** repetir toda la evaluación sobre la versión congelada (≈ 2026-11-02), cerrar D-01, añadir las pruebas de I1–I4 y repetir la prueba física con tres navegadores y con el móvil.
