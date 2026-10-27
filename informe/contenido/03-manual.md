# 3. Manual de usuario

Este manual enseña a usar la herramienta completa, la del primer parcial y lo nuevo de este parcial. Es un tutorial paso a paso, formato elegido como recurso de aprendizaje porque cada paso se puede seguir mirando la pantalla. Además, la herramienta tiene su propio **asistente de ayuda** (sección 3.9): una persona que no sabe cómo hacer algo se lo puede preguntar sin salir de la aplicación. Las capturas son de la aplicación funcionando con una sala de prueba.

## 3.1 Empezar: crear o entrar a una sala

![Página principal](capturas/01-inicio.png)
*Figura 3.1. Página principal: crear una sala nueva o unirse a una con su código. El botón «Ayuda» está siempre arriba a la derecha.*

1. Pulsa **Crear Nuevo Lienzo** para empezar una sala nueva: cada una tiene un código propio.
2. La primera vez, el navegador te pregunta «¿Cómo deseas que te vean en la sala?». Escribe tu nombre: los demás lo verán en la lista de participantes y en la actividad, y se guarda en tu navegador. No hay cuentas ni contraseñas.
3. Para invitar a alguien, dentro de la sala pulsa **Copiar código de sala** y envíale el código. Esa persona lo escribe en **Ingresa el código del lienzo** y pulsa **Unirse al Lienzo**.

![Código no válido](capturas/11-codigo-invalido.png)
*Figura 3.2. Si lo que se escribe no es un código de sala, la herramienta no entra y explica por qué.*

El código es el que genera «Crear Nuevo Lienzo» (una serie de letras y números con guiones). Si escribes otra cosa, aparece «El código no es válido» y te quedas en la página principal. Para salir de una sala pulsa **Salir**, arriba del panel izquierdo; si vuelves a entrar con el mismo código, el diagrama, la actividad y la conversación con la IA siguen donde los dejaste.

## 3.2 Dibujar el diagrama

![El editor](capturas/03-editor.png)
*Figura 3.3. El editor: la paleta a la izquierda, el lienzo al centro, y arriba la actividad y los participantes.*

- **Agregar una clase.** En **Paleta de elementos** arrastra **Clase UML** al lienzo.
- **Cambiar un nombre, un atributo o un método.** Haz doble clic sobre el texto, selecciona todo (Cmd+A o Ctrl+A), escribe el nuevo y pulsa Enter.
- **Unir dos clases.** Haz clic en una clase (aparecen círculos en sus bordes) y arrastra desde un círculo hasta la otra clase. Si sueltas sobre el lienzo vacío no queda ninguna relación. La paleta tiene **Asociación**, **Herencia**, **Agregación**, **Composición**, **Dependencia** y **Clase Asociativa**.
- **Multiplicidad.** Haz doble clic sobre ella y escribe el valor, por ejemplo `*` o `0..1`. Cuando una asociación queda con «muchos» en los dos extremos, el editor crea sola la clase intermedia con sus dos relaciones uno a muchos.
- **Mover y ajustar.** Arrastra las clases; **Acercar**, **Alejar** y **Restablecer zoom** están arriba del lienzo.
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

- **Participantes.** Muestra quién está conectado. Tú apareces con «(Tú)» y la IA como un integrante más, «Disponible» o «Pensando».
- **Host.** La primera persona que entra a una sala es el **Host**; las demás son **Participante**. Todos editan por igual. Solo el Host ve el botón **Expulsar** junto a cada participante: la persona expulsada ve «El host te expulsó de la sala» y vuelve al inicio, y puede volver a entrar con el código. Si el Host sale, pasa a serlo quien lleva más tiempo en la sala.
- **Actividad.** Lista quién hizo qué («Bruno añadió la clase Autor»). Mover o cambiar el tamaño de una clase no se registra, para no saturar la lista.
- **Reconexión.** Si se corta tu conexión o cierras la pestaña, al volver recuperas el diagrama sin perder lo que ya estaba guardado.

## 3.5 La IA como integrante de la sala

![Chat con la IA](capturas/05-chat-ia-abierto.png)
*Figura 3.6. El chat de la sala con la IA: lo ven todas las personas y dice qué IA responde.*

Pulsa **Chat con la IA** (abajo a la derecha). **La conversación es de toda la sala**: la ven y la alimentan todas las personas, y cada mensaje muestra quién lo escribió. La IA atiende **un pedido a la vez**; si está ocupada con otra persona, te lo dice y esperas a que termine. Arriba se lee qué IA responde («IA en la nube (Gemini)» o una IA local). Hay tres modos:

| Modo | Para qué sirve | Qué puede hacer la IA |
|---|---|---|
| **Preguntar** | Consultar sobre el diagrama o sobre lo que hizo cada persona («¿qué hizo Bruno?») | Solo responde; no toca el diagrama |
| **Pedir cambio** | Pedir una modificación («agrega una clase Factura con total y fecha») | Cambia el diagrama, todos lo ven y la actividad dice «IA añadió la clase Factura (a pedido de Ana)» |
| **Revisar** | Pedir una revisión de clases, atributos, métodos y relaciones | Publica sus observaciones para **toda la sala** |

![Respuesta de la IA](capturas/06-chat-ia-respuesta.png)
*Figura 3.7. Respuesta en modo Preguntar: la IA usa el diagrama y la actividad de todos.*

![Revisión con ideas aplicables](capturas/07-revision-ideas.png)
*Figura 3.8. Revisión: las ideas aparecen en la actividad de todos, cada una con un botón **Aplicar**.*

**Aplicar una idea.** Cualquier persona puede pulsar **Aplicar** en una idea: el cambio queda a nombre de quien la aplicó, mientras tanto los demás leen «Aplicando (…)» y la idea se marca como **Aplicada** para todos; nadie más puede aplicarla dos veces. La IA nunca cambia el diagrama por su cuenta: solo cuando alguien se lo pide o pulsa **Aplicar**. Hay un tope de preguntas por minuto; si te pasas, espera un momento.

## 3.6 Importar y exportar

![Exportaciones](capturas/08-exportaciones.png)
*Figura 3.9. Las exportaciones del diagrama.*

- **XMI.** **Exportar XMI** e **Importar XMI** (arriba del lienzo) intercambian el diagrama con Enterprise Architect y otras herramientas.
- **Exportaciones.** **Exportar a Backend** genera un proyecto Spring Boot con PostgreSQL y una colección de Postman en un .zip; **Exportar como SQL** da el script de las tablas; **Exportar como Imagen** descarga el diagrama como imagen; **Exportar Flutter** genera un proyecto móvil con base de datos local, que funciona sin conexión. Si el generador no responde, la herramienta lo avisa y no descarga nada.

## 3.7 Seguir la sala desde el celular

![Vista móvil](capturas/09-vista-movil.png)
*Figura 3.10. Vista móvil de seguimiento, con el botón para activar los avisos.*

1. En el editor pulsa **Copiar enlace para seguir desde el celular** y ábrelo en el teléfono.
2. Verás el diagrama actualizándose en vivo y, debajo, la actividad. Es de solo lectura: no tiene controles de edición y no cuenta como participante.
3. Pulsa **Activar avisos** y permítelos en el navegador: cada vez que alguien cambie el diagrama o la IA publique una idea, el celular te avisa. Los avisos llegan solo mientras la página está abierta. Si el navegador los bloqueó, hay que permitirlos en sus ajustes.

## 3.8 IA local y sin internet (opcional)

La plataforma puede usar un modelo de IA que corre en el propio computador, sin enviar nada a internet, en lugar de Gemini. Se activa con la configuración del servidor (`AI_PROVIDER=ollama`) y, para los cambios al diagrama, puede usar el modelo reentrenado por el equipo (`OLLAMA_CHANGE_MODEL`). El chat muestra «IA local» cuando está activa. Los pasos de instalación están en el Anexo A.

## 3.9 Aprender con el asistente de ayuda

![Asistente de ayuda](capturas/10-ayuda.png)
*Figura 3.11. El asistente de ayuda responde con los pasos, usando el manual de la herramienta.*

El botón **Ayuda** está en la página principal y dentro de la sala (en la barra de arriba del lienzo). Ábrelo y pregunta cómo hacer algo («¿Cómo exporto a Flutter?», «¿Qué hace el modo Revisar?»). El asistente responde paso a paso con lo que dice el manual de la herramienta; si lo que preguntas no trata de la herramienta, lo dice y no responde. Tu conversación con la ayuda es personal: no la ve nadie más y no necesita una sala. También tiene un tope de preguntas por minuto.

## 3.10 Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| «El código no es válido» | Pide el código a quien creó la sala: se copia con **Copiar código de sala**. |
| «Demasiadas preguntas seguidas» | La IA y la ayuda tienen un tope de uso por persona, sala y servicio; espera un minuto. |
| «La IA está atendiendo a…» | La IA atiende a una persona a la vez; espera a que termine y vuelve a enviar. |
| «La IA no pudo responder ahora» | El diagrama no se modificó ni se guardó nada a medias; reintenta o sigue editando a mano. |
| «No se pudo generar el backend» o «…la aplicación móvil» | El generador no respondió; reintenta en unos momentos o revisa que el diagrama tenga clases. |
| Me expulsaron | Vuelve a entrar con el código: entrarás como participante nuevo. |
| El micrófono no responde | Usa Chrome con conexión segura (HTTPS), o escribe el texto. |
| Una sala se comporta raro | Crea una sala nueva con **Crear Nuevo Lienzo**; lo que se hizo queda respaldado en el servidor. |
