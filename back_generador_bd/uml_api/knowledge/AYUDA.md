# Manual de la herramienta «Lienzo Colaborativo»

Herramienta web para modelar diagramas de clases UML en equipo (de 2 a 3 personas), con una IA que ayuda a quien se lo pide. No hay cuentas de usuario ni contraseñas: la sala se identifica con un código y cada persona con un nombre.

## 1. Empezar: crear o entrar a una sala

- En la página principal, «Crear Nuevo Lienzo» crea una sala nueva y te lleva a ella. Cada sala tiene un código.
- Para entrar a una sala que ya existe, escribe su código en «Ingresa el código del lienzo» y pulsa «Unirse al Lienzo».
- La primera vez, el navegador te pregunta «¿Cómo deseas que te vean en la sala?». Ese nombre es el que verán los demás y el que aparece en la actividad. Se guarda en tu navegador.
- Para invitar a alguien, dentro de la sala pulsa «Copiar código de sala» y mándale el código.
- Para salir pulsa «Salir» (arriba del panel izquierdo). Si vuelves a entrar con el mismo código, el diagrama y la actividad siguen ahí.

## 2. Participantes y roles

- El panel «Participantes» muestra quién está conectado. Tú apareces con «(Tú)». La IA aparece como «🤖 IA» y dice si está disponible o pensando.
- La primera persona que entra a la sala es el «Host»; las demás son «Participante». Todos pueden editar el diagrama por igual.
- Solo el Host ve el botón «Expulsar» junto a los demás. La persona expulsada ve un aviso y vuelve al inicio.
- Si el Host sale, el rol pasa a la persona que lleva más tiempo conectada. Al volver a entrar, entras como participante.

## 3. Dibujar el diagrama a mano

- En «Herramientas UML» → «Paleta de elementos» están «Clase UML», «Asociación», «Herencia», «Agregación», «Composición», «Dependencia» y «Clase Asociativa».
- Para agregar una clase, arrastra «Clase UML» al lienzo.
- Para renombrar una clase, un atributo o un método, haz doble clic sobre el texto, selecciona todo (Cmd+A o Ctrl+A), escribe el nombre nuevo y pulsa Enter.
- Para unir dos clases, haz clic en una (aparecen circulitos en sus bordes) y arrastra desde un circulito hasta la otra clase. La relación nace como asociación con multiplicidades 0..1 y 1.
- Para cambiar la multiplicidad, haz doble clic sobre ella y escribe el valor (por ejemplo «*»).
- Cuando una relación es de muchos a muchos, el editor crea sola la clase intermedia.
- Arriba del lienzo están «Acercar», «Alejar» y «Restablecer zoom».
- Todo lo que haces lo ven los demás al instante.

## 4. Crear o cambiar el diagrama con texto, voz o imagen

- «🤖 Generar modelo»: escribe en «Describe tu modelo aquí...» lo que quieres (por ejemplo «Agrega una clase Factura con total y fecha») y pulsa «Generar». La IA agrega lo pedido sin duplicar ni mover lo que ya existe, y todos lo ven.
- Voz: pulsa el micrófono, di la instrucción y vuelve a pulsarlo (⏹️) para terminar. La voz se convierte en texto y esa instrucción se aplica igual que si la hubieras escrito en «Generar modelo». El micrófono funciona solo en Chrome con conexión segura (HTTPS).
- Imagen: en «Importaciones» → «Importar Imagen» elige la foto o captura de un diagrama de clases. Si el diagrama de la sala ya tiene elementos, la herramienta pregunta qué hacer con el resultado: «Reemplazar diagrama», «Combinar con actual» o «Cancelar».
- Si un cambio de la IA va a eliminar elementos, la herramienta te pide confirmación antes de aplicarlo.

## 5. Chat con la IA (la conversación es de toda la sala)

- Pulsa «🤖 Chat con la IA» (abajo a la derecha). La conversación la ven y la alimentan todas las personas de la sala; cada mensaje muestra quién lo escribió.
- La IA atiende un pedido a la vez. Si está ocupada con otra persona, te avisa y esperas a que termine.
- Hay tres modos:
  - «Preguntar»: la IA solo responde, por ejemplo «¿Qué hizo Beto?» o «Explícame este diagrama». No toca el diagrama.
  - «Pedir cambio»: la IA modifica el diagrama y todos lo ven. En la actividad figura como «IA, a pedido de» quien lo pidió.
  - «Revisar»: la IA revisa el diagrama y publica sus ideas para todos en el panel «Actividad».
- Las ideas de una revisión tienen un botón «Aplicar». Quien lo pulsa aplica la idea a su nombre y queda marcada como aplicada para todos; nadie más puede aplicarla dos veces.
- La IA nunca cambia el diagrama por su cuenta: solo cuando alguien se lo pide.
- Hay un tope de preguntas por minuto. Si te pasas, espera un momento.
- El chat indica si la IA es la de la nube (Gemini) o una local.

## 6. Actividad de la sala

- El panel «Actividad» lista quién hizo qué: clases añadidas, elementos eliminados, relaciones, textos editados y las revisiones de la IA.
- Mover o cambiar el tamaño de una clase no se registra.

## 7. Validar el modelo

- «🔍 Sugerencias del modelo» abre el panel de validación. Pulsa «Analizar modelo» y verás las relaciones válidas (✅) y los errores (❌) con sugerencias.

## 8. Importar y exportar

- «Exportar XMI» e «Importar XMI» (arriba del lienzo) intercambian el diagrama con Enterprise Architect y otras herramientas.
- En «Exportaciones»:
  - «Exportar a Backend»: genera un proyecto Spring Boot con PostgreSQL y una colección de Postman, en un archivo .zip.
  - «Exportar como SQL»: descarga el script SQL de las tablas.
  - «Exportar como Imagen»: descarga el diagrama como imagen.
  - «Exportar Flutter»: genera un proyecto Flutter con base de datos local, que funciona sin conexión.

## 9. Seguir la sala desde el celular

- Pulsa «📱 Copiar enlace para seguir desde el celular» y abre ese enlace en el celular (tiene la forma /sala/CÓDIGO/seguir).
- Es una vista de solo lectura: muestra el diagrama actualizándose en vivo y la actividad debajo. No tiene controles de edición y no cuenta como participante.
- Pulsa «🔔 Activar avisos» para recibir una notificación del navegador cuando alguien cambie el diagrama o la IA publique una idea. Los avisos solo llegan mientras la página está abierta. Si el navegador los bloqueó, hay que permitirlos en sus ajustes.

## 10. Ayuda

- El botón «❓ Ayuda» (en la página principal y dentro de la sala) abre este asistente. Pregúntale cómo hacer algo en la herramienta; solo responde sobre el uso de la herramienta.
- Tu conversación con la ayuda es personal: no la ve nadie más y se queda en tu navegador.

## 11. Problemas frecuentes

- «La IA no pudo responder ahora»: reintenta en unos segundos; el diagrama no se pierde ni cambia.
- «La IA está atendiendo a otra persona»: espera a que termine y vuelve a enviar.
- «Todavía no te identificaste en la sala»: recarga la página.
- El micrófono no responde: usa Chrome y una conexión segura (HTTPS), o escribe el texto.
- Una sala que se comporta raro: crea una sala nueva con «Crear Nuevo Lienzo»; lo que se hizo queda respaldado en el servidor.
