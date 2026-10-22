# 3. Manual de usuario

Este manual es un tutorial paso a paso. Se eligió el formato de tutorial como recurso de aprendizaje (entre tutorial, video o asistente inteligente) porque cada paso se puede seguir mirando la pantalla. Todas las capturas son del sitio desplegado, https://diagramador.dev, con una sala de prueba.

## 3.1 Qué mecánicas usa la plataforma

- **Sala (lienzo colaborativo).** Todo ocurre dentro de una sala con un código. Quien conoce el código entra. La primera persona en entrar es el *host*; las demás son participantes. No hay cuentas ni contraseñas.
- **Nombre visible.** Al entrar, la plataforma pregunta cómo quieres que te vean y lo recuerda en tu navegador. Con ese nombre aparecen tus acciones en el registro de actividad.
- **La IA como integrante.** La IA aparece en la lista de participantes y no hace nada hasta que alguien se lo pide. Cada persona tiene su propio chat con ella, que nadie más puede leer.

## 3.2 Paso 1: crear una sala o unirse a una

![Pantalla de inicio](capturas/01-inicio.png)
*Figura 3.1. Pantalla de inicio.*

1. Abre https://diagramador.dev.
2. Para empezar de cero pulsa **Crear Nuevo Lienzo**. Se abre el editor con un código de sala nuevo.
3. Para entrar a una sala existente escribe su código en **Unirme al Lienzo** y pulsa **Unirse al Lienzo**.
4. Para invitar a alguien, pulsa **Copiar código de sala** y envíaselo.

## 3.3 Paso 2: conocer el editor

![Editor con un diagrama](capturas/03-editor.png)
*Figura 3.2. Editor con un diagrama de clases, la actividad de la sala y la lista de participantes.*

- **Paleta de elementos (izquierda):** **Clase UML**, **Asociación**, **Herencia**, **Agregación**, **Composición**, **Dependencia** y **Clase Asociativa**.
- **Lienzo (centro):** donde se dibuja. Los botones **+**, **−** y el de restablecer controlan el zoom; también se puede acercar con Ctrl y la rueda del ratón.
- **Actividad y Participantes (arriba a la derecha):** quién hizo qué y quién está en la sala.
- **Importar XMI / Exportar XMI (arriba):** intercambio con Enterprise Architect.
- **Importaciones y Exportaciones (izquierda):** menús con las demás entradas y salidas.
- **Chat con la IA (abajo a la derecha).**

## 3.4 Paso 3: dibujar un diagrama a mano

- **Agregar una clase:** arrastra **Clase UML** de la paleta al lienzo.
- **Cambiar el nombre, los atributos o los métodos:** haz doble clic sobre la zona que quieras editar. Selecciona el texto antes de escribir para reemplazarlo en lugar de añadirlo. Enter confirma.
- **Relacionar dos clases:** haz clic en una clase (aparecen cuatro círculos en sus bordes) y arrastra desde un círculo hasta la otra clase. La relación nace como asociación con multiplicidades `0..1` y `1`.
- **Cambiar la multiplicidad:** doble clic sobre el número y escribe el nuevo valor (por ejemplo `*`).
- **Otros tipos de relación:** usa **Herencia**, **Agregación**, **Composición** o **Dependencia** de la paleta.
- **Relación muchos a muchos:** al dibujarla, el editor crea solo la **entidad intermedia** con sus dos claves.
- **Atajos de teclado:** Suprimir o Retroceso elimina el elemento seleccionado; Ctrl+C, Ctrl+X, Ctrl+V y Ctrl+D copian, cortan, pegan y duplican; Escape quita la selección.

## 3.5 Paso 4: crear el diagrama con texto, voz o imagen

![Generar modelo](capturas/02-generar-modelo.png)
*Figura 3.3. Cuadro "Generar modelo" con una descripción escrita.*

- **Texto:** en **Generar modelo** describe lo que quieres (por ejemplo, "Crea un sistema de biblioteca con las clases Libro, Autor y Prestamo") y pulsa el botón. La IA agrega o modifica clases sin mover ni duplicar lo que ya existe.
- **Voz:** pulsa el micrófono y di la instrucción. Funciona en Google Chrome con HTTPS.
- **Imagen:** en **Importaciones** elige **Importar Imagen** y sube una foto de un diagrama; después decide si **Reemplazar** el diagrama actual o **Combinar** con él.

## 3.6 Paso 5: trabajar en equipo

![Dos personas en la sala](capturas/04-colaboracion.png)
*Figura 3.4. Sala con varias personas: cada acción aparece en la actividad con el nombre de quien la hizo.*

1. Quienes entran con el código aparecen en **Participantes**. Quien lleva más tiempo conectado figura como **Host**.
2. Todos editan a la vez y los cambios se ven al instante en las demás pantallas.
3. En **Actividad** se lee quién hizo qué ("Bruno añadió la clase Autor"). Mover o cambiar el tamaño de una clase no se registra, para no saturar la lista.
4. El **host** puede pulsar **Expulsar** junto a un participante, que verá el aviso "El host te expulsó de la sala". Los participantes no tienen ese botón.
5. Si el host sale, el participante más antiguo pasa a ser host. Quien vuelve a entrar lo hace como participante, con el diagrama y la actividad intactos.

## 3.7 Paso 6: usar la IA como integrante de la sala

![Abrir el chat con la IA](capturas/05-chat-ia-abierto.png)
*Figura 3.5. Chat con la IA: privado, con tres modos y el proveedor que responde.*

Pulsa **Chat con la IA**. Arriba se lee "Privado: solo tú ves esta conversación" y qué IA responde ("IA en la nube (Gemini)" o "IA local"). Hay tres modos:

| Modo | Para qué sirve | Qué puede hacer la IA |
|---|---|---|
| **Preguntar** | Consultar sobre el diagrama o sobre lo que hizo cada persona ("¿qué hizo Bruno?") | Solo responde; no toca el diagrama |
| **Pedir cambio** | Pedir una modificación ("agrega una clase Factura con total y fecha") | Propone el cambio y se aplica en tu navegador; todos lo ven y la actividad dice "IA añadió la clase Factura (a pedido de Ana)" |
| **Revisar** | Pedir una revisión de clases, atributos, métodos y relaciones | Publica sus observaciones para **toda la sala** |

![Respuesta de la IA](capturas/06-chat-ia-respuesta.png)
*Figura 3.6. Respuesta en modo Preguntar.*

![Revisión con ideas aplicables](capturas/07-revision-ideas.png)
*Figura 3.7. Revisión: las ideas aparecen en la actividad de todos, cada una con un botón **Aplicar**.*

**Aplicar una idea.** Cualquier persona puede pulsar **Aplicar** en una idea: el cambio queda a nombre de quien la aplicó y la idea se marca como **Aplicada** para todos (nadie más puede aplicarla dos veces). Si la idea propone **eliminar** algo, la plataforma pide confirmación antes de hacerlo.

**Qué hacer si la IA falla.** El chat muestra un mensaje claro y el diagrama no cambia. Puedes reintentar o seguir editando a mano.

**Sesiones continuas.** Si cierras la pestaña y vuelves a la sala, recuperas el diagrama, la actividad y tu propio chat.

## 3.8 Paso 7: seguir la sala desde el celular

![Vista móvil](capturas/09-vista-movil.png)
*Figura 3.8. Vista móvil de seguimiento.*

1. En el editor pulsa **Copiar enlace para seguir desde el celular** y ábrelo en el teléfono.
2. Verás el diagrama actualizándose en vivo y, debajo, la actividad. Es de solo lectura: no tiene controles de edición y no cuenta como participante.

## 3.9 Paso 8: exportar e importar

![Menú de exportaciones](capturas/08-exportaciones.png)
*Figura 3.9. Menú de exportaciones.*

| Opción | Resultado |
|---|---|
| **Exportar a Backend** | Proyecto Spring Boot + PostgreSQL en `.zip` (capas, DTO, endpoints JSON) y colección de Postman |
| **Exportar Flutter** | Proyecto móvil Flutter con SQLite local (funciona sin conexión) |
| **Exportar como SQL** | Guion SQL de las tablas |
| **Exportar como Imagen** | Imagen PNG del diagrama |
| **Exportar XMI / Importar XMI** | Intercambio con Enterprise Architect en ambos sentidos |
| **Importar Imagen** | Diagrama a partir de una foto |

## 3.10 IA local y sin internet (opcional)

La plataforma puede usar un modelo de IA que corre en el propio computador, sin enviar nada a internet, en lugar de Gemini. Se activa con la configuración del servidor (`AI_PROVIDER=ollama`) y, para los cambios al diagrama, puede usar el modelo reentrenado por el equipo (`OLLAMA_CHANGE_MODEL`). El chat muestra "IA local" cuando está activa. Los pasos de instalación están en el Anexo A.

## 3.11 Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| "Demasiadas preguntas seguidas" | La IA tiene un tope de uso por persona, sala y servicio; espera un minuto. |
| El micrófono no funciona | Usa Google Chrome y entra por HTTPS. |
| Una sala se ve rara | Crea una sala nueva con **Crear Nuevo Lienzo**; el diagrama se respalda en el servidor. |
| Me expulsaron | Vuelve a entrar con el código: entrarás como participante. |
| La IA responde un error | El diagrama no se modificó; reintenta o edita a mano. |
