# 0. Justificación del stack tecnológico utilizado

Cada tecnología del proyecto se eligió por una razón concreta del problema: edición visual de diagramas, colaboración en tiempo real, generación de código, inteligencia artificial y datos de distinta naturaleza. Cuando hubo una alternativa razonable, aquí se dice por qué no se eligió.

## Frontend

### TypeScript

TypeScript añade tipado estático sobre JavaScript, lo que mejora la robustez y el mantenimiento del código del cliente. El editor maneja estructuras complejas (clases, atributos, relaciones) y cada operación de colaboración que viaja por la red tiene un tipo propio; el tipado evita errores al manipularlas. Además es la base de Angular.

### Angular 20 con renderizado en servidor (SSR)

Angular es un marco estructurado y modular para interfaces complejas y reactivas. Su arquitectura de componentes, la inyección de dependencias y las señales reactivas permiten reflejar de inmediato en pantalla lo que envían las demás personas de la sala y organizar el cliente en componentes y servicios con responsabilidades separadas. Ofrece integración nativa con RxJS para eventos en tiempo real y compatibilidad con TypeScript y Tailwind CSS. El SSR entrega la primera pantalla desde el servidor.

### JointJS

Biblioteca de diagramación sobre SVG que resuelve lo más difícil del editor: arrastrar elementos, conectar enlaces, vértices y etiquetas de multiplicidad. Se extendió con las clases UML del proyecto en lugar de escribir un motor de dibujo propio.

### Tailwind CSS

Estilos por utilidades que mantienen la interfaz consistente y adaptable a distintos tamaños de pantalla, incluida la vista móvil de seguimiento.

### API de notificaciones del navegador y service worker

Los avisos de la vista del celular usan la API de notificaciones del navegador, sin servidor de avisos ni suscripciones: son locales y solo funcionan con la página abierta, lo que alcanza para «informarse desde el celular» sin cuentas. Como Android no deja crear una notificación directamente desde la página, un service worker mínimo (`notification-sw.js`) la muestra en su lugar.

## Backend

### Python 3.12

Lenguaje expresivo, apropiado para integrar servicios inteligentes, manejar concurrencia y comunicación en red. Su sintaxis clara favorece la legibilidad en un entorno colaborativo.

### Django 5 y Django REST Framework

Django es un marco maduro con ORM, migraciones y pruebas integradas. Concentra la API, la colaboración y la integración con los modelos de IA. Django REST Framework aporta la serialización y las vistas de la API (actividad, chat con la IA, ayuda, respaldo del diagrama, importación y exportación).

### Django Channels y Daphne

Añaden WebSockets a Django. El servidor actúa como relé: retransmite a cada sala las operaciones de edición, la presencia y la actividad, y aplica los permisos (solo el *host* puede expulsar).

### Arquitectura hexagonal: puertos y adaptadores

Lo que el servidor guarda o consulta (la actividad, la conversación con la IA, el turno de la IA, los topes de uso y el proveedor de IA) se declara como un **puerto**, una interfaz de Python en `collab/ports.py` y `ai_provider.py`, y se implementa en **adaptadores** intercambiables. El adaptador se elige con una variable de entorno (`ACTIVITY_STORE`, `CONVERSATION_STORE`, `AI_PROVIDER`), de modo que cambiar PostgreSQL por MongoDB, o Gemini por un modelo local, no toca las vistas. Las mismas pruebas de contrato se ejecutan contra cada adaptador.

### Redis

Capa de canales de Channels y almacén de lo efímero: el orden de conexión de cada sala (de donde se deriva quién es el *host*), el turno de la IA por sala (un cerrojo con vencimiento) y los contadores del tope de uso de la ayuda. Son datos de acceso muy rápido que no necesitan sobrevivir a un reinicio.

### PostgreSQL 17

Guarda lo relacional: los participantes, los intentos de uso de la IA (para sus topes) y el respaldo del diagrama de cada sala. Es el adaptador por defecto de la actividad y de la conversación.

### MongoDB 7

Guarda la actividad de la sala y la conversación con la IA cuando se activa. Son documentos que solo se agregan, con un campo `data` que cambia según el tipo de evento, y que se consultan siempre por sala y por orden: el encaje clásico de una base documental, sin las uniones ni la integridad relacional que PostgreSQL ofrece y aquí no hacen falta. La alternativa de Amazon, DynamoDB, ata el sistema a un proveedor y no se puede levantar en el computador del equipo; MongoDB corre igual en Docker en el equipo y en el servidor. Se configura con una caché acotada (0,25 GB) para que quepa junto a los demás servicios en la máquina de 2 GB.

### Spring Boot 3.5 (Java 21) y Maven Wrapper

Es el generador de backend: produce un proyecto completo con la estructura en capas que exige la materia (entidad, DTO, repositorio, servicio y controlador) y una colección de Postman. El Maven Wrapper evita exigir Maven instalado.

### Flutter y SQLite

Proyecto móvil generado con persistencia local, de modo que la aplicación generada funciona sin conexión.

### Gemini (nube) y Ollama con Qwen (local)

Gemini es el proveedor de IA por defecto: convierte texto, voz e imágenes en diagramas y atiende el chat de la sala y la ayuda. Como alternativa que corre en el computador y sin internet se usa Ollama con el modelo abierto Qwen, que además se reentrenó con la técnica LoRA usando MLX, el marco de Apple para su silicio (Anexo B). Los dos están detrás del mismo puerto, `AIProvider`.

## Herramientas

### Postman

Se genera una colección junto con el backend para probar los endpoints sin escribir las peticiones a mano.

### Visual Studio Code y asistentes de IA para programar

Editor del proyecto, con control previo de cada *commit*. Los asistentes de IA se usaron como apoyo de desarrollo y revisión de código, siguiendo las reglas escritas en `AGENTS.md` (sección 1.6), y todo cambio pasó por pruebas automáticas.

### Git y GitHub

Ramas por tarea, *commits* pequeños con el propósito en el mensaje y etiquetas de versión de lo que se entrega.

### Docker Compose, nginx, Let's Encrypt y AWS EC2

Despliegue repetible de todos los servicios, con HTTPS en un dominio propio (https://diagramador.dev).

### Jasmine y Karma, pruebas de Django y JUnit

Pruebas automáticas del frontend, del backend y del generador Spring (que compila de verdad el proyecto generado). Los adaptadores de MongoDB se prueban además contra un servidor MongoDB real en Docker.

### Enterprise Architect (XMI y diagramas del informe)

Todos los diagramas del informe se hicieron en Enterprise Architect con la notación de UML 2.5.1 (casos de uso, comunicación, clases, paquetes, despliegue, secuencia, componentes); los de la arquitectura siguen el modelo C4. Un programa los genera desde los mismos datos que las tablas del informe, de modo que el modelo y los diagramas no se desincronizan. Además la plataforma exporta el modelo de clases a XMI para abrirlo en Enterprise Architect y lo importa desde allí; ese intercambio se probó con la herramienta.
