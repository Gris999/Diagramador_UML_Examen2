# Manual de la herramienta «Lienzo Colaborativo»

Herramienta web para modelar diagramas de clases UML en equipo (de 2 a 3 personas), con una IA que ayuda a quien se lo pide. No hay cuentas de usuario ni contraseñas: la sala se identifica con un código y cada persona con un nombre.

## 1. Empezar: crear o entrar a una sala

- En la página principal, «Crear Nuevo Lienzo» crea una sala nueva y te lleva a ella. Cada sala tiene un código.
- Para entrar a una sala que ya existe, escribe su código en «Ingresa el código del lienzo» y pulsa «Unirse al Lienzo».
- La primera vez, el navegador te pregunta «¿Cómo deseas que te vean en la sala?». Ese nombre es el que verán los demás y el que aparece en la actividad. Se guarda en tu navegador.
- Para invitar a alguien, dentro de la sala pulsa «Compartir» (el botón azul de arriba a la derecha). Ahí copias el enlace de invitación: quien lo abre entra a la sala y solo escribe su nombre. También puedes pulsar «Copiar código de sala» y mandar el código: la otra persona lo escribe en «Ingresa el código del lienzo» de la página principal.
- Para invitar por correo, en «Compartir» escribe en «Invitar por correo» uno o varios correos separados por comas (hasta 10), un mensaje opcional (sin enlaces) y pulsa «Enviar invitación»: a cada persona le llega un correo de «Diagramador UML» con el enlace de la sala, y si responde, la respuesta te llega a ti. Si el servidor no puede mandar correos, el botón cambia a «Abrir mi correo», que abre tu programa de correo con el mensaje ya escrito.
- Cuando la herramienta pide iniciar sesión, la página principal es «Mis diagramas»: la lista de los diagramas que creaste, a los que te invitaron y los que abriste con un enlace, cada uno con su nombre, tu rol (Propietario, Editor o Lector) y cuándo lo abriste. Con «Nuevo diagrama» creas uno. En el menú de cada tarjeta (los tres puntos) puedes «Abrir», «Cambiar nombre» y «Eliminar» (solo el propietario; elimina el diagrama para todas las personas) o «Quitar de mi lista» (si el diagrama no es tuyo).
- Dentro de un diagrama, arriba se ve su nombre y tu rol. El propietario le cambia el nombre con un clic en el nombre.
- En «Compartir» (con inicio de sesión) hay tres partes, como en Google Docs: «Agregar personas» (escribes los correos, eliges con qué rol entran, «Editor» o «Lector», y pulsas «Enviar invitación»), «Personas con acceso» (el propietario puede cambiar el rol de cada una o quitarla) y «Acceso general». El acceso general puede ser «Restringido» (solo entran las personas agregadas, con el correo al que les llegó la invitación) o «Cualquiera con el enlace» (entra quien tenga el enlace e inicie sesión, como Lector o como Editor, a elección del propietario). El botón «Copiar enlace» solo aparece cuando el acceso general es «Cualquiera con el enlace»: si es «Restringido», el enlace por sí solo no abre el diagrama y quien no está invitado ve «No tienes invitación a esta sala» (con el botón «Entrar con otro correo»).
- Un «Lector» ve el diagrama en tiempo real pero no puede cambiarlo ni invitar a nadie: se abre en la vista de solo lectura. Un «Editor» puede cambiar el diagrama e invitar. En un celular el diagrama siempre se abre en solo lectura (la edición es desde un computador o una tableta).
- Cuando la herramienta pide iniciar sesión, la primera pantalla es «Entrar»: escribes tu correo, pulsas «Enviar código», te llega un código de 6 dígitos (vale 10 minutos y sirve una sola vez) y lo escribes para entrar. No hay contraseñas. Si el código no llega, revisa la carpeta de correo no deseado y pulsa «Pedir otro código» (hay que esperar unos segundos). El navegador recuerda tu cuenta: mientras sigas usando la herramienta no vuelve a pedirte el código (la sesión vale 30 días desde la última vez que entraste). Si usas más de un correo (por ejemplo uno personal y uno de la universidad), el navegador recuerda hasta cinco: pulsa «Cambiar de cuenta» en la página principal, elige el correo en «Elige tu cuenta» y entras sin código; con «Usar otro correo» agregas uno nuevo y con la cruz quitas uno de este navegador. Si la sesión de una cuenta ya venció, te pide un código nuevo de ese correo. Para salir de tu cuenta pulsa «Cerrar sesión» en la página principal (las otras cuentas recordadas siguen ahí). En un navegador o un dispositivo distinto hay que entrar de nuevo, porque la sesión se guarda en cada navegador. Quien recibe una invitación por correo debe entrar con ese mismo correo.
- Para salir pulsa «Salir» (arriba del panel de herramientas, a la izquierda). Si vuelves a entrar con el mismo código, el diagrama y la actividad siguen ahí.
- La herramienta se ve en tema oscuro por defecto. El botón con un sol o una luna de la barra superior cambia entre el tema oscuro y el claro (se recuerda en tu navegador). El botón de la izquierda de la barra superior oculta o muestra el panel de herramientas para dar más lugar al lienzo.

## 2. Participantes y roles

- Los círculos con la inicial de cada persona, arriba a la derecha, abren la lista «Participantes»: quién está conectado. Tú apareces con «(Tú)». La IA aparece como «IA» (con un ícono de destellos) y dice si está disponible o pensando.
- La primera persona que entra a la sala es el «Host»; las demás son «Participante». Todos pueden editar el diagrama por igual.
- Solo el Host ve el botón «Expulsar» junto a los demás. La persona expulsada ve un aviso y vuelve al inicio.
- Si el Host sale, el rol pasa a la persona que lleva más tiempo conectada. Al volver a entrar, entras como participante.

## 3. Dibujar el diagrama a mano

- En «Herramientas UML» → «Paleta de elementos» están «Clase UML», «Asociación», «Herencia», «Agregación», «Composición», «Dependencia» y «Clase Asociativa».
- Para agregar una clase, haz clic en «Clase UML» (queda marcada) y luego haz clic en el lugar del lienzo donde la quieras: aparece ahí. No hace falta mantener presionado ni arrastrar, aunque arrastrarla también funciona. Con Esc se cancela.
- Para renombrar una clase, un atributo o un método, haz doble clic sobre el texto, selecciona todo (Cmd+A o Ctrl+A), escribe el nombre nuevo y pulsa Enter.
- Para unir dos clases, haz clic en la relación que quieres en la paleta («Asociación», «Herencia», «Agregación», «Composición» o «Dependencia»), luego haz clic en la clase de origen y después en la de destino; un aviso sobre el lienzo dice qué falta y con Esc se cancela. También se puede hacer clic en una clase y arrastrar desde un circulito de su borde hasta la otra clase. La línea sale sola por el lado que mira a la otra clase y se acomoda cada vez que mueves una clase; las multiplicidades quedan a un lado de la línea, sin quedar tapadas.
- Para cambiar la multiplicidad, haz doble clic sobre ella y escribe el valor (por ejemplo «*»).
- Cuando una relación es de muchos a muchos, el editor crea sola la clase intermedia.
- Arriba del lienzo están «Acercar», «Alejar» y «Restablecer zoom».
- Todo lo que haces lo ven los demás al instante.

## 4. Crear o cambiar el diagrama con texto, voz o imagen

- «Generar modelo»: escribe en «Describe tu modelo aquí...» lo que quieres (por ejemplo «Agrega una clase Factura con total y fecha») y pulsa «Generar». La IA agrega lo pedido sin duplicar ni mover lo que ya existe, y todos lo ven.
- Voz: pulsa el micrófono, di la instrucción y vuelve a pulsarlo (⏹️) para terminar. La voz se convierte en texto y esa instrucción se aplica igual que si la hubieras escrito en «Generar modelo». El micrófono funciona solo en Chrome con conexión segura (HTTPS).
- Imagen: en «Importaciones» → «Importar Imagen» elige la foto o captura de un diagrama de clases. Si el diagrama de la sala ya tiene elementos, la herramienta pregunta qué hacer con el resultado: «Reemplazar diagrama», «Combinar con actual» o «Cancelar».
- Si un cambio de la IA va a eliminar elementos, la herramienta te pide confirmación antes de aplicarlo.

## 5. Chat con la IA (la conversación es de toda la sala)

- Pulsa «Chat con la IA» (abajo a la derecha). La conversación la ven y la alimentan todas las personas de la sala; cada mensaje muestra quién lo escribió.
- La IA atiende un pedido a la vez. Si está ocupada con otra persona, te avisa y esperas a que termine.
- Es un solo chat: escribes lo que quieras y la IA entiende qué es. No hay que elegir un modo.
  - Una pregunta, por ejemplo «¿Cuántas clases hay?» o «Explícame este diagrama»: la IA solo responde. No toca el diagrama.
  - Un pedido de cambio, por ejemplo «Agrega una clase Cliente con nombre y correo»: la IA propone lo que haría y te pide permiso. El diagrama no cambia hasta que pulses «Aplicar» (o escribas «sí»). «Descartar» (o «no») cancela la propuesta. Si escribes «directamente» (por ejemplo «agrega la clase Venta directamente») lo aplica sin preguntar. En la actividad figura como «IA, a pedido de» quien lo pidió.
  - «Revisa el diagrama»: la IA revisa y deja sus ideas en «Actividad», cada una con un botón «Aplicar».
  - «¿Qué hizo Beto?» o «historial de Ana»: responde con el registro de actividad de esa persona, incluido lo que hizo con la IA. Sin nombre («muéstrame el historial») cuenta lo último que pasó en la sala.
- Las ideas de una revisión tienen un botón «Aplicar». Quien lo pulsa aplica la idea a su nombre y queda marcada como aplicada para todos; nadie más puede aplicarla dos veces.
- La IA nunca cambia el diagrama por su cuenta: solo cuando alguien se lo pide, y antes te pide permiso.
- Arriba del chat se elige el modelo de la sala: «Nube (Gemini)» o «Local». Es uno solo para todos y el cambio queda en Actividad. «Local» solo se puede elegir si el servidor tiene el modelo local; si no, aparece apagado.
- Hay un tope de preguntas por minuto. Si te pasas, espera un momento.
- El chat indica si la IA es la de la nube (Gemini) o una local.

## 6. Actividad de la sala

- El botón «Actividad» de la barra superior abre la lista de quién hizo qué (si llegó algo nuevo mientras estaba cerrada, el botón muestra un número): clases añadidas, elementos eliminados, relaciones, textos editados y las revisiones de la IA.
- Mover o cambiar el tamaño de una clase no se registra.

## 7. Validar el modelo

- «Sugerencias del modelo» abre el panel de validación. Pulsa «Analizar modelo» y verás las relaciones válidas (con una marca verde) y los errores (con una marca roja) con sugerencias.

## 8. Importar y exportar

- «Exportar XMI» e «Importar XMI» (arriba del lienzo) intercambian el diagrama con Enterprise Architect y otras herramientas.
- En «Exportaciones»:
  - «Exportar a Backend»: genera un proyecto Spring Boot con PostgreSQL y una colección de Postman, en un archivo .zip.
  - «Exportar como SQL»: descarga el script SQL de las tablas.
  - «Exportar como Imagen»: descarga el diagrama como imagen.
  - «Exportar Flutter»: genera un proyecto Flutter con base de datos local, que funciona sin conexión. Antes te pregunta el nombre de la aplicación (puedes dejarlo vacío).
  - «Descargar proyecto completo»: un solo .zip con el backend, la aplicación móvil, el script SQL y un archivo LEEME con los pasos para ponerlo a funcionar. También te pregunta el nombre de la aplicación.
  - La aplicación móvil generada trae un asistente con IA local. Para usarlo sin internet, dentro de la app toca «Descargar IA local» (unos 1,1 GB, una sola vez, con confirmación). Con el modelo listo puedes conversar con él sobre sistemas de gestión y pedirle órdenes sobre tus datos («crea un departamento llamado Ventas», «borra el empleado número 3»). Cada respuesta dice si la escribió la «IA local» o es una «Respuesta de la app». Es un modelo pequeño: puede equivocarse al explicar conceptos.

## 9. Seguir la sala desde el celular

- Pulsa «Compartir», luego «Copiar enlace para seguir desde el celular», y abre ese enlace en el celular (tiene la forma /sala/CÓDIGO/seguir). En un iPhone, ábrelo en Safari y agrégalo a la pantalla de inicio (Compartir → «Agregar a Inicio») para poder recibir avisos.
- Es una vista de solo lectura: muestra el diagrama actualizándose en vivo y la actividad debajo. No tiene controles de edición y no cuenta como participante.
- Pulsa «🔔 Activar avisos» para recibir una notificación del navegador cuando alguien cambie el diagrama o la IA publique una idea. Los avisos solo llegan mientras la página siga abierta. Si el navegador los bloqueó, hay que permitirlos en sus ajustes.

## 10. Ayuda

- El botón «Ayuda» (con un signo de interrogación, en la página principal y dentro de la sala) abre este asistente. Pregúntale cómo hacer algo en la herramienta; solo responde sobre el uso de la herramienta.
- Tu conversación con la ayuda es personal: no la ve nadie más y se queda en tu navegador.

## 11. Problemas frecuentes

- «La IA no pudo responder ahora»: reintenta en unos segundos; el diagrama no se pierde ni cambia.
- «La IA está atendiendo a otra persona»: espera a que termine y vuelve a enviar.
- «Todavía no te identificaste en la sala»: recarga la página.
- El micrófono no responde: usa Chrome y una conexión segura (HTTPS), o escribe el texto.
- Una sala que se comporta raro: crea una sala nueva con «Crear Nuevo Lienzo»; lo que se hizo queda respaldado en el servidor.
