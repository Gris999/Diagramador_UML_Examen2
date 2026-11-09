# 3. Manual de usuario

Este manual enseña a usar la herramienta completa, la del primer parcial y lo nuevo de este parcial. Es un tutorial paso a paso, formato elegido como recurso de aprendizaje porque cada paso se puede seguir mirando la pantalla. Además, la herramienta tiene su propio **asistente de ayuda** (sección 3.9): una persona que no sabe cómo hacer algo se lo puede preguntar sin salir de la aplicación. Las capturas son de la aplicación funcionando con una sala de prueba. Las de entrar con el correo, «Mis diagramas», Compartir con roles y «sin invitación» (figuras 3.1 a 3.1d) se tomaron en una copia local con datos de ejemplo y personas ficticias, porque el sitio publicado pide un código que llega por correo; las demás se tomaron en el sitio publicado el 8 de noviembre, antes de agregar el acceso por correo.

## 3.1 Empezar: entrar con tu correo, «Mis diagramas» y compartir

![Entrar con el correo](capturas/14-entrar.png)
*Figura 3.1. La página «Entrar»: se escribe el correo y la herramienta manda un código. No hay contraseñas.*

1. Escribe tu correo y pulsa **Enviar código**. Te llega un mensaje de «Diagramador UML» con un código de 6 dígitos que vale 10 minutos (si tarda, mira la carpeta de correo no deseado; los buzones de algunas universidades demoran unos minutos).
2. Escribe el código y pulsa **Entrar**. La sesión se queda guardada en ese navegador y se renueva cada vez que vuelves a usar la herramienta (vale 30 días desde la última vez), así que no vuelve a pedirte el código mientras la uses; en otro navegador u otro aparato hay que entrar una vez. **Cerrar sesión** (arriba a la derecha) borra la de la cuenta actual. Si no llega o te equivocas cinco veces, pide otro código con **Pedir otro código**.
3. Si usas más de un correo (por ejemplo uno personal y otro de la universidad), el navegador los recuerda (hasta cinco). **Cambiar de cuenta** (arriba a la derecha de «Mis diagramas») abre **Elige tu cuenta**: pulsas un correo y entras sin código; **Usar otro correo** agrega uno nuevo y la cruz quita un correo de ese navegador. Si la sesión de un correo ya venció, la herramienta pide un código nuevo de ese correo.

![Escribir el código](capturas/14b-entrar-codigo.png)
*Figura 3.1a. Segundo paso: el código de 6 dígitos que llegó al correo.*

Al entrar ves **Mis diagramas**: la lista de todo lo tuyo, como en Google Docs. Cada tarjeta muestra el nombre del diagrama, tu rol (**Propietario**, **Editor** o **Lector**), cuándo lo abriste por última vez, de quién es (si no es tuyo) y «Con enlace» si cualquiera con el enlace puede abrirlo. Aparecen los diagramas que creaste, a los que te invitaron y los que abriste con un enlace público.

![Mis diagramas](capturas/15-mis-diagramas.png)
*Figura 3.1b. «Mis diagramas»: Ana es propietaria de dos, editora de uno y lectora de otro. Los tres puntos de cada tarjeta abren **Abrir**, **Cambiar nombre** y **Eliminar** (solo la persona propietaria) o **Quitar de mi lista** (las demás).*

4. Pulsa **Nuevo diagrama** para empezar uno: quien lo abre primero queda como **Propietario**. El nombre («Sin título» al principio) se cambia en la barra superior del editor, junto a tu rol, o desde el menú de la tarjeta.
5. No se te pregunta el nombre: la herramienta usa el que sale de tu correo («pedro.alaca@…» aparece como «Pedro Alaca»). Los demás lo verán en la lista de participantes y en la actividad.
6. Para dar acceso a otras personas, dentro del diagrama pulsa **Compartir** (arriba a la derecha):
   - En **Agregar personas** escribe uno o varios correos, elige con qué rol entran (**Editor**: puede cambiar el diagrama; **Lector**: solo mira), escribe un mensaje si quieres y pulsa **Enviar invitación**. A cada persona le llega un correo con el enlace; entra con ese mismo correo.
   - **Personas con acceso** lista quién tiene el diagrama. La persona propietaria cambia el rol de cada una o la quita con la cruz.
   - **Acceso general** decide quién más puede abrirlo: **Restringido** (solo las personas de la lista, con su correo) o **Cualquiera con el enlace** (como Lector o como Editor). El enlace para copiar solo aparece cuando el acceso es público.

![Compartir](capturas/16-compartir-roles.png)
*Figura 3.1c. La ventana «Compartir» de un diagrama: personas con su rol, acceso general y enlace.*

7. Si abres un diagrama privado con un correo que no está en su lista, ves «No tienes invitación a esta sala» y puedes entrar con otro correo; no se abre nada. Quien solo tiene rol de **Lector**, o abre el diagrama desde un celular, entra a la vista de solo lectura (sección 3.7).

![Sin invitación](capturas/17-sin-acceso.png)
*Figura 3.1d. Una persona que no está en la lista de un diagrama privado no entra, aunque tenga el enlace.*

**Instalación local sin acceso por correo.** En una copia de la herramienta donde el servidor no pide entrar con el correo (como una instalación para desarrollo), no hay «Mis diagramas» ni invitaciones: la página principal ofrece **Crear Nuevo Lienzo** y **Unirse al Lienzo**, y el código de la sala hace de llave.

![Página principal](capturas/01-inicio.png)
*Figura 3.1e. Página principal de una instalación sin acceso por correo: crear una sala nueva o unirse a una con su código. El botón «Ayuda» está siempre arriba a la derecha.*

![Código no válido](capturas/11-codigo-invalido.png)
*Figura 3.2. En ese modo, si lo que se escribe no es un código de sala, la herramienta no entra y explica por qué.*

El código es el que genera «Crear Nuevo Lienzo» (una serie de letras y números con guiones). Si escribes otra cosa, aparece «El código no es válido» y te quedas en la página principal. Para salir de una sala pulsa **Salir**, arriba del panel izquierdo; si vuelves a entrar al mismo diagrama, el diagrama, la actividad y la conversación con la IA siguen donde los dejaste.

## 3.2 Dibujar el diagrama

![El editor](capturas/03-editor.png)
*Figura 3.3. El editor: la paleta a la izquierda, el lienzo al centro, y arriba las herramientas y los botones Actividad, Participantes y Compartir.*

- **Agregar una clase.** En **Paleta de elementos** haz clic en **Clase UML** (queda marcada y un aviso sobre el lienzo dice qué hacer) y luego haz clic en el lugar del lienzo donde la quieras: la clase aparece ahí, centrada en el clic. No hace falta mantener presionado; arrastrar la herramienta al lienzo también funciona, y **Esc** cancela.
- **Cambiar un nombre, un atributo o un método.** Haz doble clic sobre el texto, selecciona todo (Cmd+A o Ctrl+A), escribe el nuevo y pulsa Enter.
- **Unir dos clases.** En la paleta haz clic en la relación que quieres (**Asociación**, **Herencia**, **Agregación**, **Composición** o **Dependencia**), luego haz clic en la clase de origen (queda resaltada) y después en la de destino; **Esc** cancela. También puedes hacer clic en una clase y arrastrar desde uno de los círculos de su borde hasta la otra clase; si sueltas sobre el lienzo vacío no queda ninguna relación. La línea sale por el lado que mira a la otra clase, solo con líneas horizontales y verticales, y se acomoda sola cada vez que mueves una clase; la multiplicidad queda a un lado de la línea, fuera de las clases. La paleta tiene además **Clase Asociativa**.
- **Multiplicidad.** Haz doble clic sobre ella y escribe el valor, por ejemplo `*` o `0..1`. Cuando una asociación queda con «muchos» en los dos extremos, el editor la deja directa entre sus dos clases, con sus multiplicidades, y crea sola la clase asociativa (por ejemplo `Curso_Estudiante`) unida al medio de la línea con un conector punteado, sin multiplicidad. Si prefieres dibujarla tú, haz clic en **Clase Asociativa**, luego en tu clase y después en la línea de la asociación (en ese orden o al revés). Si borras la clase asociativa que el editor generó, la asociación queda sin ella y no se vuelve a crear.
- **Mover y ajustar.** Arrastra las clases; **Acercar**, **Alejar** y **Restablecer zoom** están arriba del lienzo. El primer botón de la barra superior oculta o muestra el panel de herramientas para dar más lugar al lienzo.
- **Tema oscuro o claro.** La herramienta se ve en tema oscuro; el botón con un sol o una luna de la barra superior (y de la página principal) cambia al tema claro y se recuerda en tu navegador.
- **Validar el modelo.** **Sugerencias del modelo** abre un panel; con **Analizar modelo** la herramienta muestra las relaciones válidas y los errores con una sugerencia.

## 3.3 Crear o cambiar el diagrama con texto, voz o una imagen

![Generar modelo](capturas/02-generar-modelo.png)
*Figura 3.4. «Generar modelo»: se escribe lo que se quiere con palabras.*

- **Texto.** En **Generar modelo** escribe lo que quieres («Agrega una clase Factura con total y fecha») y pulsa **Generar**. La IA agrega lo pedido sin duplicar ni mover lo que ya existe, y todos lo ven. Mientras trabaja, las demás personas leen «Pensando (a pedido de…)».
- **Voz.** Pulsa el micrófono, di la instrucción y vuelve a pulsarlo para terminar: la voz se convierte en texto y se aplica igual que si la hubieras escrito. Funciona solo en Chrome con conexión segura (HTTPS).
- **Imagen.** En **Importaciones** → **Importar Imagen** elige la foto o captura de un diagrama de clases. Si el diagrama ya tiene elementos, la herramienta pregunta si quieres **Reemplazar diagrama**, **Combinar con actual** o **Cancelar**.
- Si lo que pides **elimina** elementos, la herramienta te pide confirmación antes de aplicarlo.

## 3.4 Trabajar en equipo

![Dos personas en la sala](capturas/04-colaboracion.png)
*Figura 3.5. Una sala con dos personas: cada acción aparece en la actividad con el nombre de quien la hizo.*

![Lista de participantes](capturas/13-participantes.png)
*Figura 3.5b. Los círculos de la barra superior abren la lista de participantes: quién es el Host, quién eres tú y si la IA está disponible.*

- **Participantes.** Las personas conectadas se ven como círculos con su inicial en la barra superior; al tocarlos se abre la lista. Tú apareces con «(Tú)» y la IA como un integrante más, «Disponible» o «Pensando».
- **Host.** La primera persona que entra a una sala es el **Host**; las demás son **Participante**. Todos editan por igual. Solo el Host ve el botón **Expulsar** junto a cada participante: la persona expulsada ve «El host te expulsó de la sala» y vuelve al inicio, y puede volver a entrar si sigue en la lista del diagrama. Si el Host sale, pasa a serlo quien lleva más tiempo en la sala.
- **Actividad.** El botón **Actividad** de la barra superior abre la lista de quién hizo qué («Bruno añadió la clase Autor»); si llegó algo nuevo mientras estaba cerrada, el botón muestra un número. Mover o cambiar el tamaño de una clase no se registra, para no saturar la lista.
- **Reconexión.** Si se corta tu conexión o cierras la pestaña, al volver recuperas el diagrama sin perder lo que ya estaba guardado.

## 3.5 La IA como integrante de la sala

![Chat con la IA](capturas/05-chat-ia-abierto.png)
*Figura 3.6. El chat de la sala con la IA: lo ven todas las personas y dice qué IA responde.*

Pulsa **Chat con la IA** (abajo a la derecha). **La conversación es de toda la sala**: la ven y la alimentan todas las personas, y cada mensaje muestra quién lo escribió. La IA atiende **un pedido a la vez**; si está ocupada con otra persona, te lo dice y esperas a que termine. Arriba se lee qué IA responde y se puede elegir entre **Nube (Gemini)** y **Local**: el modelo es **uno solo para toda la sala**, el cambio queda en la actividad y «Local» aparece apagado si el servidor no tiene el modelo local. Es **un solo chat**: no hay que elegir un modo, la herramienta entiende lo que escribes.

| Lo que escribes | Qué hace la IA |
|---|---|
| Una pregunta («¿qué clases hay?», «explícame el diagrama») | Solo responde; no toca el diagrama |
| Un pedido de cambio («agrega una clase Factura con total y fecha») | **Propone lo que haría y te pide permiso.** El diagrama no cambia hasta que pulses **Aplicar** (o escribas «sí»); **Descartar** (o «no») la cancela. Si escribes «directamente» lo aplica sin preguntar. Al aplicarse, la actividad dice «IA añadió la clase Factura (a pedido de Ana)» |
| «Revisa el diagrama» | Revisa clases, atributos, métodos y relaciones y deja sus ideas en la **actividad** de toda la sala, cada una con un botón **Aplicar** |
| «¿Qué hizo Bruno?» o «historial de Ana» | Responde con el registro de actividad de esa persona, incluido lo que hizo con la IA; sin nombre cuenta lo último que pasó en la sala |

![Respuesta de la IA](capturas/06-chat-ia-respuesta.png)
*Figura 3.7. Respuesta a una pregunta: la IA usa el diagrama y la actividad de todos.*

![Propuesta de cambio con permiso](capturas/06b-propuesta-permiso.png)
*Figura 3.7b. Un pedido de cambio: la IA cuenta lo que haría y espera. El diagrama no cambia hasta que se pulsa **Aplicar**; **Descartar** lo cancela.*

![Revisión con ideas aplicables](capturas/07-revision-ideas.png)
*Figura 3.8. Revisión: las ideas aparecen en la actividad de todos, cada una con un botón **Aplicar**.*

**Aplicar una idea.** Cualquier persona puede pulsar **Aplicar** en una idea: el cambio queda a nombre de quien la aplicó, mientras tanto los demás leen «Aplicando (…)» y la idea se marca como **Aplicada** para todos; nadie más puede aplicarla dos veces. La IA nunca cambia el diagrama por su cuenta: solo cuando alguien se lo pide o pulsa **Aplicar**. Hay un tope de preguntas por minuto; si te pasas, espera un momento.

## 3.6 Importar y exportar

![Exportaciones](capturas/08-exportaciones.png)
*Figura 3.9. Las exportaciones del diagrama.*

- **XMI.** **Exportar XMI** e **Importar XMI** (arriba del lienzo) intercambian el diagrama con Enterprise Architect y otras herramientas.
- **Exportaciones.** **Exportar a Backend** genera un proyecto Spring Boot con PostgreSQL y una colección de Postman en un .zip; **Exportar como SQL** da el script de las tablas; **Exportar como Imagen** descarga el diagrama como imagen; **Exportar Flutter** genera un proyecto móvil con base de datos local, que funciona sin conexión; **Descargar proyecto completo** entrega en un solo .zip el backend, la aplicación móvil, el script SQL y un archivo LEEME con los pasos. Los dos preguntan antes el nombre de la aplicación, que se ve bajo el icono y en la cabecera de la app (puede quedar vacío). La aplicación móvil tiene un asistente que entiende lo que se le escribe o dice; para usarlo sin internet, el botón **Descargar IA local** baja el modelo una sola vez (unos 1,1 GB, con confirmación y progreso; quien tiene el modelo pequeño anterior ve **Descargar IA mejorada**). Con el modelo listo el asistente **conversa** sobre sistemas de gestión usando los datos reales de la app y ejecuta órdenes («crea un departamento llamado Ventas», «borra el empleado número 3»); cada respuesta lleva la etiqueta **IA local** (la escribió el modelo) o **Respuesta de la app** (texto fijo o reglas). Es un modelo pequeño y puede equivocarse al explicar conceptos. Si el generador no responde, la herramienta lo avisa y no descarga nada.

## 3.7 Seguir la sala desde el celular

![Vista móvil](capturas/09-vista-movil.png)
*Figura 3.10. Vista móvil de seguimiento, con el botón para activar los avisos.*

1. En el editor pulsa **Compartir**, luego **Copiar enlace para seguir desde el celular**, y ábrelo en el teléfono con tu correo (un celular nunca abre el editor: siempre entra a esta vista de solo lectura, aunque seas editora). Si alguien solo tiene rol de **Lector**, también entra aquí.
2. Verás el diagrama actualizándose en vivo y, debajo, la actividad. Es de solo lectura: no tiene controles de edición y no cuenta como participante.
3. Pulsa **Activar avisos** y permítelos en el navegador: cada vez que alguien cambie el diagrama o la IA publique una idea, el celular te avisa. Los avisos llegan solo mientras la página sigue abierta (no hay servidor de avisos). En un iPhone, ábrela en Safari y agrégala a la pantalla de inicio (Compartir → «Agregar a Inicio»): los avisos solo existen en esa app, no en una pestaña de Safari. Si el navegador los bloqueó, hay que permitirlos en sus ajustes.

## 3.8 IA local y sin internet (opcional)

La plataforma puede usar un modelo de IA que corre en el propio computador, sin enviar nada a internet, en lugar de Gemini. Se activa con la configuración del servidor (`AI_PROVIDER=ollama`) y, para los cambios al diagrama, puede usar el modelo reentrenado por el equipo (`OLLAMA_CHANGE_MODEL`). El chat muestra «IA local» cuando está activa. Los pasos de instalación están en el Anexo A.

## 3.9 Aprender con el asistente de ayuda

![Asistente de ayuda](capturas/10-ayuda.png)
*Figura 3.11. El asistente de ayuda responde con los pasos, usando el manual de la herramienta.*

El botón **Ayuda** está en la página principal y dentro de la sala (en la barra de arriba del lienzo). Ábrelo y pregunta cómo hacer algo («¿Cómo exporto a Flutter?», «¿Cómo pido una revisión?»). El asistente responde paso a paso con lo que dice el manual de la herramienta; si lo que preguntas no trata de la herramienta, lo dice y no responde. Tu conversación con la ayuda es personal: no la ve nadie más y no necesita una sala. También tiene un tope de preguntas por minuto.

## 3.10 Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| «No tienes invitación a esta sala» | Entraste con un correo que no está en la lista del diagrama. Pide a quien lo creó que te invite a ese correo, o entra con el correo al que te llegó la invitación (**Entrar con otro correo**). |
| No llega el código ni la invitación | Mira el correo no deseado y espera unos minutos (algunos buzones de universidad demoran); pide otro código con **Pedir otro código** (hay un tiempo de espera entre pedidos). |
| «El código no es válido» (instalación sin acceso por correo) | Pide el código a quien creó la sala: se copia en **Compartir** → **Copiar código de sala**. |
| «Demasiadas preguntas seguidas» | La IA y la ayuda tienen un tope de uso por persona, sala y servicio; espera un minuto. |
| «La IA está atendiendo a…» | La IA atiende a una persona a la vez; espera a que termine y vuelve a enviar. |
| «La IA no pudo responder ahora» | El diagrama no se modificó ni se guardó nada a medias; reintenta o sigue editando a mano. |
| «No se pudo generar el backend» o «…la aplicación móvil» | El generador no respondió; reintenta en unos momentos o revisa que el diagrama tenga clases. |
| Me expulsaron | Vuelve a entrar desde **Mis diagramas** (o con el enlace): entrarás como participante nuevo. |
| El micrófono no responde | Usa Chrome con conexión segura (HTTPS), o escribe el texto. |
| Una sala se comporta raro | Crea un diagrama nuevo con **Nuevo diagrama**; lo que se hizo queda respaldado en el servidor. |
