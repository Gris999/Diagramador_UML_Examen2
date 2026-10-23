# 3. Manual de usuario

Este manual cubre **solo lo nuevo de este parcial**; el uso básico (crear una sala o unirse a una, dibujar el diagrama, generarlo con texto, voz o imagen y exportarlo) está en el manual del primer parcial. Es un tutorial paso a paso, formato elegido como recurso de aprendizaje (entre tutorial, video o asistente inteligente) porque cada paso se puede seguir mirando la pantalla. Todas las capturas son del sitio desplegado, https://diagramador.dev, con una sala de prueba.

## 3.1 Qué mecánicas nuevas usa la plataforma

- **Nombre visible.** Al entrar, la plataforma pregunta cómo quieres que te vean y lo recuerda en tu navegador. Con ese nombre aparecen tus acciones en el registro de actividad. No hay cuentas ni contraseñas.
- **Host por orden de llegada.** Quien lleva más tiempo conectado en la sala es el *host* (el Diseñador); las demás personas son participantes (Colaboradores).
- **La IA como integrante.** La IA aparece en la lista de participantes y no hace nada hasta que alguien se lo pide. Cada persona tiene su propio chat con ella, que nadie más puede leer.

## 3.2 Paso 1: entrar con tu nombre y ver la actividad del equipo

![Editor con un diagrama](capturas/03-editor.png)
*Figura 3.1. Editor con un diagrama de clases, la actividad de la sala y la lista de participantes.*

1. Entra a una sala con su código. Si es la primera vez en ese navegador, escribe cómo quieres que te vean.
2. Arriba a la derecha, **Participantes** muestra quién está en la sala y **Actividad** muestra quién hizo qué ("Bruno añadió la clase Autor").
3. Mover o cambiar el tamaño de una clase no se registra, para no saturar la lista.

![Dos personas en la sala](capturas/04-colaboracion.png)
*Figura 3.2. Sala con varias personas: cada acción aparece en la actividad con el nombre de quien la hizo.*

4. El **host** puede pulsar **Expulsar** junto a un participante, que verá el aviso "El host te expulsó de la sala". Si el host sale, el participante más antiguo pasa a ser host.

## 3.3 Paso 2: usar la IA como integrante de la sala

![Abrir el chat con la IA](capturas/05-chat-ia-abierto.png)
*Figura 3.3. Chat con la IA: privado, con tres modos y el proveedor que responde.*

Pulsa **Chat con la IA**. Arriba se lee "Privado: solo tú ves esta conversación" y qué IA responde ("IA en la nube (Gemini)" o "IA local"). Hay tres modos:

| Modo | Para qué sirve | Qué puede hacer la IA |
|---|---|---|
| **Preguntar** | Consultar sobre el diagrama o sobre lo que hizo cada persona ("¿qué hizo Bruno?") | Solo responde; no toca el diagrama |
| **Pedir cambio** | Pedir una modificación ("agrega una clase Factura con total y fecha") | Propone el cambio y se aplica en tu navegador; todos lo ven y la actividad dice "IA añadió la clase Factura (a pedido de Ana)" |
| **Revisar** | Pedir una revisión de clases, atributos, métodos y relaciones | Publica sus observaciones para **toda la sala** |

![Respuesta de la IA](capturas/06-chat-ia-respuesta.png)
*Figura 3.4. Respuesta en modo Preguntar.*

![Revisión con ideas aplicables](capturas/07-revision-ideas.png)
*Figura 3.5. Revisión: las ideas aparecen en la actividad de todos, cada una con un botón **Aplicar**.*

**Aplicar una idea.** Cualquier persona puede pulsar **Aplicar** en una idea: el cambio queda a nombre de quien la aplicó y la idea se marca como **Aplicada** para todos (nadie más puede aplicarla dos veces). Si la idea propone **eliminar** algo, la plataforma pide confirmación antes de hacerlo.

**Qué hacer si la IA falla.** El chat muestra un mensaje claro y el diagrama no cambia. Puedes reintentar o seguir editando a mano.

**Sesiones continuas.** Si cierras la pestaña y vuelves a la sala, recuperas el diagrama, la actividad y tu propio chat.

## 3.4 Paso 3: seguir la sala desde el celular

![Vista móvil](capturas/09-vista-movil.png)
*Figura 3.6. Vista móvil de seguimiento.*

1. En el editor pulsa **Copiar enlace para seguir desde el celular** y ábrelo en el teléfono.
2. Verás el diagrama actualizándose en vivo y, debajo, la actividad. Es de solo lectura: no tiene controles de edición y no cuenta como participante.

## 3.5 Paso 4: IA local y sin internet (opcional)

La plataforma puede usar un modelo de IA que corre en el propio computador, sin enviar nada a internet, en lugar de Gemini. Se activa con la configuración del servidor (`AI_PROVIDER=ollama`) y, para los cambios al diagrama, puede usar el modelo reentrenado por el equipo (`OLLAMA_CHANGE_MODEL`). El chat muestra "IA local" cuando está activa. Los pasos de instalación están en el Anexo A.

## 3.6 Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| "Demasiadas preguntas seguidas" | La IA tiene un tope de uso por persona, sala y servicio; espera un minuto. |
| Me expulsaron | Vuelve a entrar con el código: entrarás como participante. |
| La IA responde un error | El diagrama no se modificó; reintenta o edita a mano. |
