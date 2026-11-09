# Lista final de entrega — segundo parcial (sobre la versión 1.0)

| | |
|---|---|
| **Proyecto** | Diagramador UML colaborativo con IA como integrante de la sala (Ingeniería de Software I, grupo 29) |
| **Versión** | `v1.0` es el primer parcial (etiqueta en `develop`). El segundo parcial entró a `develop` con el pull request 2 (commit de fusión `ac1efb6`), todavía sin etiqueta |
| **Repositorio** | https://github.com/Gris999/Diagramador_UML_Examen2 (la rama por defecto es `develop`: es la que abre el código QR de GitHub de la carátula) |
| **Sitio desplegado** | https://diagramador.dev (AWS EC2, HTTPS). Desplegado el 2026-11-04 con el segundo parcial (chat compartido, avisos, asistente de ayuda) y actualizado el 2026-11-07 con la clase asociativa UML y las relaciones recursivas, más tarde ese día con el arreglo del proyecto Flutter con IA local, y esa noche con la app móvil pulida (asistente en español natural, pantalla principal genérica con el nombre y el icono de la app, descarga de la IA local dentro de la app) y el botón «Descargar proyecto completo» y, esa noche, con el asistente que responde con la verdad sobre su IA y con el asistente que conversa con una IA local de 1,5B usando los datos reales de la app y, la misma noche, con el rediseño de la interfaz (una sola paleta, íconos SVG y componentes compartidos; `docs/DISENO_UI.md`) y los mensajes en español claro del asistente móvil, el 2026-11-08 con los avisos en iPhone, con el rediseño oscuro con «Compartir» y, esa noche, con el chat único de la IA (propone y pide permiso, historial por persona y selector de modelo) (`develop` = `32e8ebc`). La actividad y la conversación con la IA se guardan en MongoDB Atlas (nube, plan gratuito) desde ese día |
| **Fecha de entrega** | Martes **2026-11-10, a más tardar a las 8 a.m.**, en la plataforma (de *DOCUMENTACION DEL 2DO PARCIAL.docx*). La fecha de una presentación oral, si la hay, no está confirmada |
| **Estado al 2026-11-08** | Pull requests 2 a 23 fusionados en `develop` (`32e8ebc`); desplegado en AWS con la prueba de humo en orden; informe de 334 páginas generado; pruebas físicas pendientes (sección 5) |

## 1. Qué se entrega

| Entrega | Dónde está |
|---|---|
| Código fuente (frontend, backend, generador Spring) | Repositorio: `develop` (pull request 2 fusionado) |
| Informe del segundo parcial (PDF y Word) y el modelo de Enterprise Architect | `informe/build/Informe.pdf`, `informe/build/Informe.docx` y `informe/build/ea/modelo.qea` (no se versionan; se suben a la plataforma). Se generan con lo que hay en `informe/` |
| Plan del segundo parcial (fases, decisiones, calendario) | [`PLAN_SEGUNDO_PARCIAL.md`](PLAN_SEGUNDO_PARCIAL.md) |
| Aplicación funcionando | https://diagramador.dev (segundo parcial desplegado el 2026-11-04) y, en local, `develop` |
| Documentación PUDS por disciplina | El informe (sección 2) y [`puds/`](puds/README.md) |
| Plan de trabajo PUDS de la IA integrante | [`PLAN_PUDS_IA_PARTICIPANTE.md`](PLAN_PUDS_IA_PARTICIPANTE.md) |
| Estado de cada requisito | [`GAP_MATRIX.md`](GAP_MATRIX.md) y [`REQUIREMENTS.md`](REQUIREMENTS.md) |
| Despliegue (AWS, dominio, HTTPS, seguridad, pruebas de humo, MongoDB) | [`DESPLIEGUE.md`](DESPLIEGUE.md) y `scripts/smoke-test.sh` |
| IA local (instalación, evaluación 10/10) | [`IA_LOCAL.md`](IA_LOCAL.md) y `scripts/evaluar_ia.py` |
| Guion de la demostración | [`DEMO.md`](DEMO.md) |
| Evidencia de pruebas y defectos | Sección 2.5 del informe y [`puds/05-pruebas.md`](puds/05-pruebas.md) |

## 2. Requisitos: resumen

Todos los requisitos de `REQUIREMENTS.md` figuran como **hechos** salvo los que se indican (ver [`GAP_MATRIX.md`](GAP_MATRIX.md) para el detalle y la evidencia):

| Grupo | Estado |
|---|---|
| Editor UML manual, texto → UML, imagen → UML, voz → UML | Hecho |
| Colaboración de 2–3 personas, host/participantes, expulsar, reconexión y recuperación de estado | Hecho |
| XMI con Enterprise Architect (en ambos sentidos, con pruebas de seguridad) | Hecho en el primer parcial; **por repetir** tras los cambios del segundo |
| Generación Spring Boot + PostgreSQL, colección Postman, proyecto Flutter con SQLite sin conexión | Hecho; el Flutter sin red en un dispositivo está **por repetir** |
| IA como integrante de la sala: identidad, actividad, chat (**una sola conversación para toda la sala** desde el segundo parcial), cambios a pedido **con permiso** (un solo chat: la IA propone y espera «Aplicar»; el historial de cada persona se responde del registro de actividad; el modelo de la sala, nube o local, se elige en el chat), revisión con ideas aplicables, sesiones continuas, vista móvil | Hecho (RF-23 a RF-32) |
| Avisos en la vista del celular (RF-34), asistente de ayuda (RF-35) y MongoDB para la actividad y la conversación (RNF-08) | Hecho y desplegado, con MongoDB Atlas activo desde el 2026-11-04; el 2026-11-07 se vio una notificación real del sistema en un emulador de Android (Chrome, Android 16) y en Chrome contra el sitio publicado. En iPhone los avisos solo existen si la página se agrega a la pantalla de inicio (iOS 16.4 o más; en una pestaña de Safari no hay avisos y la vista lo explica): el 2026-11-08 se corrigió que la app no los mostraba (en iPhone `new Notification()` no falla pero no muestra nada; ahora el aviso sale siempre por el service worker) y en el simulador de iPhone 17 Pro, con la app agregada a Inicio desde el sitio publicado, llegó el aviso real «Ana · añadió la clase Entidad» con la app abierta, en segundo plano y con el teléfono bloqueado. Límites: no hay servidor de avisos push, así que funcionan mientras la página siga viva, y el simulador no imita la suspensión de iOS: en un iPhone físico bloqueado mucho rato puede no recibirlos; en un teléfono físico está sin probar |
| IA local (Ollama + Qwen 3.5 9B) y modelo de 4 mil millones de parámetros reentrenado | Hecho: 10/10 pedidos correctos (RF-33); el reentrenado, en los anexos del informe |
| Despliegue en AWS con dominio y HTTPS | Parcial: manual y repetible; sin infraestructura como código ni CI/CD |
| IA local **dentro de la app móvil generada** | Parcial: la app descarga el modelo `.gguf` (Qwen2.5-1.5B, unos 1,1 GB) una sola vez por una acción explícita (botón «Descargar IA local», con confirmación y progreso; «Descargar IA mejorada» para quien tiene el modelo pequeño anterior) o lo importa con «Elegir modelo», y lo usa sin internet. Con el modelo listo **conversa** sobre sistemas de gestión usando el esquema y los datos reales de la app, y sus órdenes (crear, consultar, cambiar, eliminar) las interpreta el modelo con protecciones; cada respuesta lleva la etiqueta «IA local» o «Respuesta de la app». Comprobado el 2026-11-07 con el modelo real en macOS (tabla de resultados en `docs/FLUTTER_ASSISTANT_SETUP.md`) y la descarga dentro de la app en un iPhone 17 Pro Max; falta medir la conversación del 1,5B en el iPhone. Es un modelo pequeño: puede explicar conceptos de forma imprecisa. Sin modelo, o si la IA falla, usa textos fijos y el intérprete determinista |
| Cobertura de pruebas / formalidad UML 2.5 | Parcial: ver §4 |

## 3. Estado de las pruebas (2026-11-07)

| Suite | Resultado |
|---|---|
| Frontend (Karma) | 365 correctas, 0 fallos; `ng build` sin errores |
| Django (`manage.py test` con `settings_test`, sin Docker) | 473 pruebas, todas pasan; 19 de ellas se omiten sin un MongoDB real (`MONGO_TEST_URL`) y pasaron con él el 2026-10-26 |
| Spring (incluye compilar de verdad el proyecto generado) | 12 correctas, 0 fallos |
| Proyecto Flutter generado (`flutter test` y `flutter analyze` en un proyecto de ejemplo) | 111 correctas, 0 fallos; el analizador no da errores ni advertencias (2026-11-07) |
| Asistente móvil con el modelo real (Qwen2.5-1.5B, en un Mac) | 15 frases por las reglas y por el modelo: consultar, crear, cambiar por id y borrar por número dan el comando correcto; la charla usa los datos reales y reconoce sus límites. Tabla en `docs/FLUTTER_ASSISTANT_SETUP.md` (2026-11-07) |
| Sitio desplegado | `scripts/smoke-test.sh` el 2026-11-07 (tras cada despliegue del día, el último con el servidor en `556204b`): 12 comprobaciones, todo en orden (el 2026-11-04 también, antes y después de activar MongoDB Atlas). La ayuda respondió una pregunta real y rechazó una fuera de tema; `/api/chatbot/` (eliminado) da 404 |
| MongoDB Atlas | Las 19 pruebas de los adaptadores contra Atlas (MongoDB 8.0), desde el servidor: pasan. Se copiaron 34 eventos y 10 mensajes con `migrar_a_mongo` (iguales a los de PostgreSQL salvo la hora a milisegundos y el nombre de autor de los mensajes viejos). Prueba de punta a punta: una edición por WebSocket y una pregunta a la IA se guardaron y se leyeron de Atlas, y PostgreSQL no creció |
| Modelos del informe contra el repositorio | Pasan los seis validadores: 69 clases de diseño, 74 asociaciones, 226 mensajes de secuencia, 66 casos de prueba (uno por camino de los 14 casos de uso) y 243 pruebas citadas |
| Pruebas manuales | 21 procedimientos ejecutados en el navegador con Gemini real (2026-10-26 y 27) y, el 2026-10-22, tres identidades + vista móvil sobre el sitio desplegado |
| Revisión de código | Dos rondas independientes antes del primer parcial, la revisión automática antes de cada commit y la revisión del pull request 2: 9 hallazgos, uno corregido (el 3, MongoDB) y ocho aplazados |
| Escaneo de secretos | 2026-10-22, árbol y 131 commits, sin hallazgos; no se repitió desde entonces |

Comandos exactos: [`puds/05-pruebas.md`](puds/05-pruebas.md) §3.

## 4. Limitaciones conocidas (decirlas con honestidad)

1. **Sin cuentas:** el código de la sala es la capacidad de acceso; la vista móvil es de solo lectura pero **no** es un permiso separado (`DESPLIEGUE.md` §7).
2. **La conversación con la IA es de toda la sala** (decisión del docente): cualquiera que tenga el código la lee. Antes era privada por persona.
3. **Atribución a la IA** (`via_ia`) la declara el navegador: es transparencia, no auditoría a prueba de manipulación.
4. **Servidor pequeño** (2 vCPU, ~2 GB): la IA local no corre allí; la nube (Gemini) sí. MongoDB no corre en el servidor sino en MongoDB Atlas (plan gratuito, 512 MB), para no usar la memoria de la máquina (`DESPLIEGUE.md` §8). Si el servidor se reinicia, las personas conectadas pierden la conexión y deben volver a entrar; el diagrama se recupera desde el respaldo.
5. **Dominio** `diagramador.dev` vence el 2027-10-21 (renovación automática apagada a propósito).
6. **Pruebas en dispositivos reales pendientes:** la vista móvil y los avisos se probaron en una ventana del tamaño de un celular, no en un teléfono; la app Flutter sin red y el XMI con Enterprise Architect no se repitieron tras los cambios del segundo parcial.
7. **Sin topes de uso propios** en las rutas de imagen y de audio (el chat y la ayuda sí los tienen).
8. **Calidad de la IA:** depende de Gemini o del modelo local; las respuestas pueden fallar o equivocarse; en ese caso el chat muestra el error y el diagrama no cambia, y los cambios que eliminan elementos piden confirmación.
9. **Marca de agua:** los diagramas exportados llevan la de la versión de prueba de Enterprise Architect. Además, los diagramas de despliegue y de contenedores siguen dibujando `mongo_db` como un contenedor del servidor; el informe aclara que en producción es MongoDB Atlas.
10. **Atlas solo acepta la IP del servidor** (`18.188.167.127`): si esa IP cambia, el chat compartido y el registro de actividad fallan hasta agregar la IP nueva en Atlas o volver a PostgreSQL con dos variables. Lo escrito en Atlas no se copia de vuelta a PostgreSQL. Los datos de las salas están en una nube de un tercero (`DESPLIEGUE.md` §8).

## 5. Lo que tiene que hacer una persona antes de entregar

- [x] **Pull request 2 fusionado a `develop`** el 2026-11-04 (`ac1efb6`): el código QR de GitHub de la carátula ya muestra el segundo parcial.
- [x] **Desplegado en AWS** el 2026-11-04: migración `collab/0005_chatmessage_author_name` aplicada, memoria medida y `scripts/smoke-test.sh` en orden (`DESPLIEGUE.md` §4).
- [x] **MongoDB Atlas activado en el servidor** el 2026-11-04 (`DESPLIEGUE.md` §8).
- [ ] **Pruebas físicas:** exportar e importar XMI con Enterprise Architect, generar el Flutter y usarlo sin red en un dispositivo, recibir una notificación en un celular físico, Android o iPhone con la página agregada a Inicio (en un emulador de Android, en el simulador de iPhone y en Chrome ya se vio) y trabajar con tres personas reales en tres navegadores sobre el sitio desplegado.
- [ ] **Revisar el PDF página por página** e imprimir las dos carátulas.
- [ ] **Confirmar con el docente** si hay presentación oral y qué día.
- [ ] **Ensayar la demostración** con las personas reales (`DEMO.md`), cada una en su propio navegador o perfil.
- [ ] **Subir a la plataforma** `Informe.pdf`, `Informe.docx` y `modelo.qea` antes del martes 2026-11-10 a las 8 a.m. (idealmente la noche del 9).
- [ ] **Reservar una IP fija en AWS (IP elástica)** si el servidor se llegara a apagar: sin ella la IP cambia y hay que actualizar el DNS y la lista de IP permitidas de MongoDB Atlas (`DESPLIEGUE.md` §5 y §8).
- [ ] **Restringir el puerto 22 a la IP de quien administra** (opcional; riesgo: quedarse sin acceso si la IP cambia).
- [ ] **Decidir si se baja la IA local o se muestra solo Gemini** en la demostración (`DEMO.md` §4).

## 6. Antes de empezar la demostración (30 minutos antes)

1. `scripts/smoke-test.sh` → debe decir "Todo en orden."
2. Abrir https://diagramador.dev en Chrome, crear una sala de prueba, agregar una clase, abrir el chat y hacer una pregunta (comprueba la IA y la base de datos).
3. Tener a mano: Enterprise Architect abierto, una imagen de un diagrama de clases, el celular con el enlace de seguimiento.
4. Si algo falla: crear una sala nueva; el plan B está en `DEMO.md`.

## 7. Cómo correr todo en un computador (si piden ver el código funcionando)

```bash
# red y base de datos
docker network create backend            # solo la primera vez
docker compose -f docker-compose.db.yml up -d
# aplicación (Django + Redis + Spring + Angular)
docker compose -f docker-compose.app.yml up -d --build
```

Requiere `back_generador_bd/.env` (plantilla en `back_generador_bd/.env.example`; los valores reales nunca se suben a git). Angular queda en http://localhost:4200. Detalle de puertos y de variables en `AGENTS.md` y `DESPLIEGUE.md`. MongoDB es opcional y no arranca con estos comandos; se levanta con su perfil (`DESPLIEGUE.md` §8).

## 8. Qué quedó fuera (a propósito)

Cuentas y autenticación; separar permisos de lectura y de edición; ejecutar el modelo local en el servidor de AWS; infraestructura como código y CI/CD; reescribir el historial de git (la contraseña antigua ya no sirve, pero sigue visible en commits viejos).
