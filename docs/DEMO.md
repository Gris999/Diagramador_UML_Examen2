# Guion de la demostración

Sitio: **https://diagramador.dev** · Duración prevista: **12–15 minutos** (se puede acortar a 8 quitando los bloques marcados *opcional*).

Este guion sigue el orden en que el docente pidió ver el sistema: primero que **todo lo del primer parcial funcione completo**, y después que **la IA sea un integrante más de la sala**. Cada bloque dice qué hacer, qué decir y qué debe verse; si algo no se ve, está el plan B.

## 0. Antes de empezar (10 minutos antes)

| Qué | Cómo comprobarlo |
|---|---|
| El sitio está sano | `scripts/smoke-test.sh` → debe terminar con "Todo en orden." |
| Tres navegadores o perfiles distintos | Un perfil por persona (Ana, Bruno, Carla): **cada perfil guarda su propia identidad**; con pestañas del mismo perfil comparten nombre. Usar ventanas de incógnito distintas sirve. |
| Un celular (o la ventana del navegador en tamaño móvil) | Se abre el enlace del botón "📱 Copiar enlace para seguir desde el celular" |
| Chrome (no Safari) para el micrófono | El micrófono solo funciona en Chrome con HTTPS |
| Enterprise Architect abierto con un proyecto vacío | Para el bloque XMI |
| Una imagen de un diagrama de clases lista | Para "UML desde imagen" |
| La IA local (opcional) | `ollama serve` en el computador de quien presenta; ver [`IA_LOCAL.md`](IA_LOCAL.md) |
| Conexión a internet estable | La IA en la nube (Gemini) la necesita |
| Un celular real con Chrome y HTTPS (para los avisos) | Los avisos solo se pueden permitir en HTTPS y con la página abierta; en un navegador de escritorio también sirven |
| El código de una sala de ensayo y uno mal escrito (por ejemplo `mi-sala`) | Para mostrar que la portada no entra con un código inválido |

**Si algo falla durante la demo:** la sala se puede rehacer en 10 segundos ("Crear Nuevo Lienzo"); todo lo que se ve ya está respaldado en el servidor.

## 1. Primer parcial: el editor completo (4–5 min)

1. **Crear la sala** (Ana). *"Cada sala tiene un código; quien lo conoce entra."* Mostrar el botón **Copiar código de sala**. Escribir `mi-sala` en «Unirse al Lienzo»: aparece *«El código no es válido»* y no entra.
2. **Edición manual.** Se hace así (ensayado el 2026-10-22):
   - **Agregar clases:** arrastrar **Clase UML** de la paleta al lienzo (dos veces).
   - **Renombrar:** doble clic sobre el **nombre** de la clase; aparece una cajita de texto con el nombre actual. **Seleccionar todo antes de escribir** (triple clic o Cmd+A); si no, el texto nuevo se agrega al final ("EntidadCliente"). Enter confirma. Lo mismo para atributos y métodos (doble clic en su zona).
   - **Unir con una Asociación:** hacer clic en una clase (aparecen cuatro circulitos en sus bordes) y **arrastrar desde un circulito hasta la otra clase**. La paleta no es una herramienta de clic, es para arrastrar clases. La relación nace con multiplicidades `0..1` y `1`.
   - **Multiplicidad:** doble clic sobre el `0..1` y sobre el `1`, reemplazar por `*` en ambos extremos.
   - *"Cuando una relación es muchos-a-muchos, el editor crea sola la entidad intermedia con su clave."* (Se ve la clase `Cliente_Pedido`.)
   - **Consejo:** hacer toda la edición manual **antes** de que entren los demás: el panel de Actividad crece con cada acción y empuja el lienzo hacia abajo (llega a un máximo y luego se desplaza solo).
3. **UML desde texto.** En "Generar modelo": *"Agrega una clase Factura con total y fecha"*. Mostrar que no duplica ni mueve lo existente.
4. **UML desde voz** *(opcional)*. Pulsar el micrófono y decir una instrucción corta.
5. **UML desde imagen** *(opcional)*. Importaciones → imagen del diagrama → Reemplazar/Combinar.
6. **Exportaciones.** *"El mismo diagrama sale en varios formatos"*:
   - **XMI → Enterprise Architect:** Exportar XMI, abrirlo en EA (clases, atributos, relaciones y multiplicidades intactos) y, al revés, importar un XMI.
   - **Backend Spring Boot + PostgreSQL + Postman:** Exportaciones → generar; mostrar el `.zip` y que compila con el Maven Wrapper incluido.
   - **Flutter:** proyecto con SQLite local (funciona sin red).
   - **SQL e imagen PNG.**

## 2. Colaboración en tiempo real con tres personas (3 min)

1. Bruno y Carla entran con el código. En **Participantes** se ve: Ana = **Host**, los otros = Participante, cada uno con su nombre.
2. Los tres editan a la vez: lo que hace uno aparece en las otras pantallas. En **Actividad** aparece *quién hizo qué* ("Carla añadió la clase …"). *Mover o redimensionar no se registra a propósito, para no estorbar la edición.*
3. **Permisos:** Ana (host) pulsa **Expulsar** en Carla → Carla ve el aviso *"El host te expulsó de la sala"* y vuelve al inicio; a Bruno no le aparece el botón.
4. **Relevo de host:** Ana sale de la sala → Bruno pasa a ser **Host**.
5. **Reconexión:** Carla vuelve a entrar → entra como participante (el rol no se hereda), con el diagrama y la actividad intactos.

## 3. La IA como integrante de la sala (4–5 min)

Frase de apertura: *"La IA es un integrante más: no hace nada hasta que alguien se lo pide, todos ven lo que hace, conoce lo que hizo cada uno y se puede dejar la sesión para retomarla después."*

1. **La IA aparece en Participantes** (🤖 IA, "Disponible").
2. **Chat compartido** (botón 🤖 *Chat con la IA*). Mostrar el aviso *"Lo ven todas las personas de la sala"*: es una sola IA y una sola conversación para el equipo, como pidió el docente. Cada mensaje muestra su autor.
   - **Preguntar:** *"¿Qué hizo Bruno hasta ahora?"* → responde con el registro de actividad. *"Solo responde; en este modo no puede tocar el diagrama."*
3. **Pedir cambio** (Ana): *"Agrega una clase Factura con total y fecha, relacionada con Pedido"*. Mientras trabaja, en la pantalla de los demás se lee **"Pensando (a pedido de Ana)…"**. Al terminar, la clase aparece en las tres pantallas y en Actividad: **"🤖 IA añadió la clase Factura (a pedido de Ana)"**.
   - *Si el cambio elimina algo, la IA pide confirmación antes de aplicarlo.*
4. **Revisar** (Carla): la IA publica sus observaciones para **todos**, con un botón **Aplicar** en cada idea. Bruno pulsa **Aplicar** en una: el cambio queda a nombre de Bruno ("IA … a pedido de Bruno") y la idea se marca **Aplicada** para todos (nadie más puede aplicarla dos veces).
5. **Conversación compartida:** Bruno abre su chat → **ve** las preguntas de Ana y de Carla, cada una con su autor, y las respuestas de la IA. *La IA atiende un pedido a la vez:* si Ana y Bruno preguntan al mismo tiempo, el segundo lee *«La IA está atendiendo a Ana. Espera a que termine.»*
6. **Sesión continua:** cerrar todas las pestañas y volver a abrir la sala → siguen el diagrama, la actividad y la conversación con la IA.
7. **Vista móvil de seguimiento** (celular): abrir el enlace → se ve el diagrama actualizándose en vivo y la actividad debajo; **no tiene ningún control de edición** y no cuenta como participante (no se vuelve host). Pulsar **Activar avisos** y permitirlos: cuando alguien cambia el diagrama o la IA publica una idea, el celular avisa (solo con la página abierta). *Si en el ensayo el navegador tiene los avisos bloqueados, la barra lo dice y se explica que se permiten en sus ajustes.*
8. **Asistente de ayuda** (también desde la portada, sin sala): pulsar **Ayuda** y preguntar *«¿Cómo invito a un compañero y cómo la sigo desde el celular?»* → responde con los pasos del manual. Preguntar algo ajeno (*«¿Quién ganó el mundial de 2018?»*) → responde *«Solo puedo ayudarte con el uso de esta herramienta.»* Es el mecanismo para que cualquiera aprenda a usar la herramienta.

## Lo que se comprobó en los ensayos del 2026-10-22 y del 2026-10-26 (para no sorprenderse)

- **Tres personas a la vez** (Ana, Bruno y Carla) y un celular: las cuatro pantallas convergen; el celular no cuenta como participante ni tiene controles.
- **Salir de la sala** (botón *Salir*): en 3 segundos otra persona pasa a ser host (la que lleva más tiempo conectada). **Volver a entrar** es una conexión nueva: entra como participante.
- **Expulsar:** la persona expulsada ve el aviso *"El host te expulsó de la sala"* y vuelve al inicio.
- **"Pensando (a pedido de X)…"** se ve en las pantallas de los demás mientras la IA trabaja.
- **Ideas de la revisión:** si una idea propone **eliminar** algo, el navegador pide confirmación (en la demo conviene mostrarlo y aceptar); si no elimina nada (por ejemplo, renombrar), se aplica directo.
- **Conversación compartida (2026-10-26):** el chat de Bruno muestra las preguntas de Ana con su autor; cuando Bruno aplica una idea de la revisión de Carla, el pedido queda en la conversación a nombre de Bruno. Mientras alguien aplica una idea, las demás pantallas leen *«Aplicando (Bruno)…»* y la idea no se puede aplicar dos veces.
- **Volver tras una expulsión (2026-10-26):** la persona expulsada puede volver a entrar con el código sin recargar la página (antes la expulsaba de nuevo).
- **Código de sala:** un texto que no es un código (`mi-sala`) no entra; un código en mayúsculas y con espacios sí (se normaliza).
- **Relaciones sueltas:** soltar una relación sobre el lienzo vacío no deja nada colgado ni escribe un evento en la actividad.
- **Si falla un generador:** con el generador Spring apagado, *Exportar a Backend* avisa y no descarga nada.
- **Ayuda con Gemini real:** responde en 10 a 40 segundos; tener paciencia o adelantar la pregunta.
- **Un detalle de la preparación:** si se prueba con varias pestañas **del mismo navegador**, comparten nombre e identidad; para ensayar con tres personas usar perfiles o ventanas de incógnito distintas.

## 3b. Base de datos NoSQL (1 min)

*"Pidió el docente una base NoSQL: la actividad y la conversación con la IA pueden guardarse en MongoDB en lugar de PostgreSQL, con una variable de entorno y sin tocar el resto, porque el servidor habla con una interfaz (puerto) y no con la base."* Mostrar `collab/ports.py` y `collab/mongo_stores.py`, y las pruebas de contrato que se ejecutan contra PostgreSQL y contra un MongoDB real. **Decir con honestidad:** el adaptador de MongoDB está listo y probado; en el servidor de AWS (2 GB) se activa solo después de medir la memoria libre (`DESPLIEGUE.md`, sección 8).

## 4. IA local, sin internet (2 min, *opcional pero recomendable*)

*"El docente planteó como opcional y valorable una IA local; la probamos con Qwen 3.5 de 9 mil millones de parámetros."* (Es opcional: no es obligatorio, solo suma.)

1. En el computador de quien presenta: `AI_PROVIDER=ollama` (ver [`IA_LOCAL.md`](IA_LOCAL.md)) y reiniciar Django. En el chat se lee **"IA local (qwen3.5:9b)"**.
2. Hacer una pregunta y un cambio: funciona igual, sin enviar nada a internet.
3. Mostrar la tabla de evaluación: **10 de 10 pedidos correctos** con el modelo local y **10 de 10** con Gemini, con verificaciones estrictas (clase, atributo, tipo y extremos correctos; nada perdido). Los tiempos varían entre corridas (de ≈ 10 s a ≈ 20 s en promedio para ambos): no prometer que uno sea más rápido.
4. Decir con honestidad: *el servidor de AWS (2 GB de memoria) no puede correr el modelo; la IA local se demuestra en un portátil.*

## 5. Arquitectura, proceso y despliegue (2 min)

- **Arquitectura:** Angular + JointJS (editor), Django + Channels + Redis (colaboración y API), Spring Boot (generador), PostgreSQL. Detalle y diagramas: [`puds/03-diseno.md`](puds/03-diseno.md).
- **Despliegue:** AWS EC2 con Docker Compose, nginx y HTTPS (Let's Encrypt) en un dominio propio; solo los puertos 22, 80 y 443 están abiertos. Un solo comando comprueba todo: `scripts/smoke-test.sh`. Runbook: [`DESPLIEGUE.md`](DESPLIEGUE.md).
- **Proceso PUDS:** fases, iteraciones, artefactos por disciplina y trazabilidad en [`puds/`](puds/README.md); estado de cada requisito en [`GAP_MATRIX.md`](GAP_MATRIX.md).
- **Pruebas:** 288 del frontend y 350 del backend (más 19 contra un MongoDB real), compilación real del proyecto Spring generado, 66 casos de prueba (uno por cada camino de los 14 casos de uso) y 21 procedimientos ejecutados a mano con la IA real (sección 2.5 del informe); y una revisión de código independiente cuyos hallazgos se corrigieron ([`puds/05-pruebas.md`](puds/05-pruebas.md)).

## Preguntas probables y respuestas cortas

| Pregunta | Respuesta |
|---|---|
| ¿Por qué no hay cuentas de usuario? | Es una decisión de diseño (RF-17): el rol de host vive solo en la sala viva; la identidad es un nombre más un identificador anónimo del navegador. El código de sala es la "llave". |
| ¿Qué pasa si la IA falla? | Se muestra un mensaje claro, el diagrama no cambia y nada queda guardado a medias. |
| ¿Puede la IA cambiar el diagrama sin que se lo pidan? | No. Solo el modo *Pedir cambio* lo modifica, y lo aplica el navegador de quien lo pidió; *Preguntar* y *Revisar* nunca devuelven cambios (hay una prueba automática con un proveedor falso que devuelve un diagrama). |
| ¿Por qué una sola conversación con la IA para toda la sala? | Porque el docente lo pidió: es un integrante más del equipo, una sola instancia que conoce lo que hizo cada persona. Atiende un pedido a la vez (un cerrojo por sala en Redis) y cada mensaje muestra su autor. |
| ¿Cómo se evita que alguien gaste la cuota de la IA? | Topes por persona (12/min), por sala (30/min) y en total (60/min) en el chat, y 6/min por persona y 30/min en total en la ayuda. Las rutas de imagen y de audio todavía no tienen tope propio (limitación conocida). |
| ¿Cómo sé que lo que dice el documento está en el software? | La sección 2.6 lo comprueba en las dos direcciones cada vez que se genera el informe: cada clase, operación y mensaje de secuencia del diseño existe en el código, y cada clase del código que el diseño no modela tiene escrita su razón. |
| ¿La vista móvil es segura? | Es solo lectura y no puede enviar nada, pero el enlace lleva el código de la sala; no es un permiso separado (se documenta en `DESPLIEGUE.md` §7). |
| ¿Qué falta? | Evaluación con más pedidos de la IA local, pruebas en un celular físico y, si se quisiera separar permisos de lectura y edición, códigos distintos. |

## Plan B

| Si falla… | Hacer |
|---|---|
| Gemini (nube) | Cambiar a la IA local (`AI_PROVIDER=ollama`) o mostrar el modo que no la necesita; el chat muestra el error claro. |
| Internet | IA local + los generadores (no necesitan red). |
| El micrófono | Usar texto; el micrófono funciona solo en Chrome con HTTPS. |
| Una sala "rara" | Crear una sala nueva (10 segundos). Al reiniciar el servidor ya se limpian los participantes de las salas anteriores. |
