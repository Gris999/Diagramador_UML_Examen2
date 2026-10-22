# 0. Justificación del stack tecnológico utilizado

Cada tecnología del proyecto se eligió por una razón concreta del problema: edición visual de diagramas, colaboración en tiempo real, generación de código e inteligencia artificial.

## Frontend

### TypeScript

TypeScript se eligió porque añade tipado estático sobre JavaScript, lo que mejora la robustez y el mantenimiento del código del cliente. El editor maneja estructuras complejas (clases, atributos, relaciones) y cada operación de colaboración que viaja por la red tiene un tipo propio; el tipado evita errores al manipularlas. Además es la base de Angular.

### Angular 20 con renderizado en servidor (SSR)

Angular es un marco estructurado y modular para interfaces complejas y reactivas. Su arquitectura de componentes, la inyección de dependencias y las señales reactivas permiten reflejar de inmediato en pantalla lo que envían las demás personas de la sala. Ofrece integración nativa con RxJS para eventos en tiempo real, soporte para formularios y estados complejos, y compatibilidad con TypeScript y Tailwind CSS. El SSR entrega la primera pantalla desde el servidor.

### JointJS

Biblioteca de diagramación sobre SVG que resuelve lo más difícil del editor: arrastrar elementos, conectar enlaces, vértices y etiquetas de multiplicidad. Se extendió con las clases UML del proyecto en lugar de escribir un motor de dibujo propio.

### Tailwind CSS

Estilos por utilidades que mantienen la interfaz consistente y adaptable a distintos tamaños de pantalla, incluida la vista móvil de seguimiento.

## Backend

### Python 3.12

Lenguaje expresivo, apropiado para integrar servicios inteligentes, manejar concurrencia y comunicación en red. Su sintaxis clara favorece la legibilidad en un entorno colaborativo.

### Django 5 y Django REST Framework

Django es un marco maduro con ORM, migraciones y pruebas integradas. Concentra la API, la colaboración y la integración con los modelos de IA. Django REST Framework aporta la serialización y las vistas de la API (actividad, chat con la IA, respaldo del diagrama, importación y exportación) y se integra de forma natural con Django Channels.

### Django Channels y Daphne

Añaden WebSockets a Django. El servidor actúa como relé: retransmite a cada sala las operaciones de edición, la presencia y la actividad, y aplica los permisos (solo el *host* puede expulsar).

### Redis

Capa de canales de Channels y almacén del orden de conexión de cada sala, del que se deriva quién es el *host*. Son datos temporales de acceso muy rápido que no necesitan sobrevivir a un reinicio.

### PostgreSQL 17

Guarda lo que debe sobrevivir: el respaldo del diagrama de cada sala, los participantes, el registro de actividad y los chats con la IA.

### Spring Boot 3.5 (Java 21) y Maven Wrapper

Es el generador de backend: produce un proyecto completo con la estructura en capas que exige la materia (entidad, DTO, repositorio, servicio y controlador) y una colección de Postman. El Maven Wrapper evita exigir Maven instalado.

### Flutter y SQLite

Proyecto móvil generado con persistencia local, de modo que la aplicación generada funciona sin conexión.

### Gemini (nube) y Ollama con Qwen (local)

Gemini es el proveedor de IA por defecto: convierte texto, voz e imágenes en diagramas y atiende el chat de la sala. Como alternativa que corre en el computador y sin internet se usa Ollama con el modelo abierto Qwen, que además se reentrenó con la técnica LoRA usando MLX, el marco de Apple para su silicio (capítulo 7 y Anexo B).

## Herramientas

### Postman

Se genera una colección junto con el backend para probar los endpoints sin escribir las peticiones a mano.

### Visual Studio Code y asistentes de IA para programar

Editor del proyecto, con control previo de cada *commit*. Los asistentes de IA se usaron como apoyo de desarrollo y revisión de código, y todo cambio pasó por pruebas automáticas.

### Git y GitHub

Ramas por tarea, *commits* pequeños y una etiqueta de versión (v1.0) de lo que se entrega.

### Docker Compose, nginx, Let's Encrypt y AWS EC2

Despliegue repetible de todos los servicios, con HTTPS en un dominio propio (https://diagramador.dev).

### Jasmine y Karma, pruebas de Django y JUnit

Pruebas automáticas del frontend, del backend y del generador Spring (que compila de verdad el proyecto generado).

### PlantUML, Graphviz y el modelo C4

Los diagramas de la Parte 2 se escriben como texto y se dibujan con la notación de UML 2.5.1 (casos de uso, comunicación, clases, paquetes, despliegue, secuencia, componentes). Se generan desde los mismos datos que las tablas del informe, de modo que el modelo y los diagramas no se desincronizan. Para el contexto, los contenedores y los componentes se usa la notación del modelo C4.

### Enterprise Architect (XMI)

La plataforma exporta el modelo de clases a XMI para abrirlo en Enterprise Architect y lo importa desde allí; ese intercambio se probó con la herramienta.
