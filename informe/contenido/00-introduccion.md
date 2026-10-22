# 0. Justificación del stack tecnológico

La plataforma es una aplicación web con tres servicios y un conjunto de apoyos. Cada tecnología se eligió por una razón concreta del problema (edición visual de diagramas, colaboración en tiempo real, generación de código e inteligencia artificial).

## Frontend

- **TypeScript.** El tipado estático evita errores al manipular estructuras como clases, atributos, relaciones y operaciones de colaboración (cada operación que viaja por la red tiene un tipo propio). Es la base de Angular.
- **Angular 20 con renderizado en servidor (SSR).** Su arquitectura de componentes, la inyección de dependencias y las señales reactivas permiten reflejar de inmediato en pantalla lo que envían los demás participantes. El SSR entrega la primera pantalla desde el servidor.
- **JointJS.** Biblioteca de diagramación sobre SVG que resuelve lo difícil del editor: arrastrar elementos, conectar enlaces, vértices y etiquetas de multiplicidad. Se extendió con las clases UML del proyecto en lugar de escribir un motor de dibujo.
- **Tailwind CSS.** Estilos por utilidades que mantienen la interfaz consistente y adaptable, incluida la vista móvil de seguimiento.

## Backend principal

- **Python 3.12 y Django 5.** Marco maduro, con ORM, migraciones y pruebas integradas. Concentra la API, la colaboración y la integración con modelos de IA.
- **Django REST Framework.** Serialización y vistas de la API (actividad, chat con la IA, respaldo del diagrama, importación y exportación).
- **Django Channels y Daphne.** Añaden WebSockets a Django: el servidor retransmite a cada sala las operaciones de edición, la presencia y la actividad.
- **Redis.** Capa de canales de Channels y almacén del orden de conexión de cada sala, del que se deriva quién es el *host*. Son datos temporales y de acceso muy rápido.
- **PostgreSQL 17.** Guarda lo que debe sobrevivir: respaldo del diagrama de cada sala, participantes, registro de actividad y chats con la IA.

## Generadores

- **Spring Boot 3.5 con Java 21 y Maven Wrapper.** Genera un proyecto backend completo a partir del diagrama, con la estructura en capas exigida (entidad, DTO, repositorio, servicio y controlador). El Maven Wrapper evita exigir Maven instalado.
- **Flutter y SQLite.** Proyecto móvil generado con persistencia local, de modo que la aplicación funciona sin conexión.
- **Colección de Postman.** Se genera junto con el backend para probar los endpoints.

## Inteligencia artificial

- **Gemini (nube).** Proveedor por defecto: convierte texto, voz e imágenes en diagramas y atiende el chat de la sala.
- **Ollama con Qwen (local).** Alternativa que corre en el computador, sin internet. Para esta entrega se reentrenó un modelo Qwen de 4 mil millones de parámetros con la técnica LoRA usando **MLX**, el marco de Apple para su silicio (capítulo 7 y Parte 2, implementación).

## Modelado

- **PlantUML y Graphviz.** Los diagramas de la Parte 2 se escriben como texto y se dibujan con la notación de UML 2.5.1 (casos de uso, comunicación, clases, paquetes, despliegue, secuencia, componentes). Se generan desde los mismos datos que las tablas del informe, de modo que el modelo y los diagramas no se desincronizan, y se pueden regenerar cuando el modelo cambia. Para el contexto, los contenedores y los componentes se usa la notación del modelo C4.
- **XMI y Enterprise Architect.** Además, la propia plataforma exporta el modelo de clases a XMI para abrirlo en Enterprise Architect (y lo importa desde allí), flujo que se probó con esa herramienta.

## Despliegue y calidad

- **Docker Compose, nginx y Let's Encrypt en AWS EC2.** Todo se despliega de forma repetible con HTTPS en un dominio propio (https://diagramador.dev).
- **Jasmine y Karma (frontend), pruebas de Django y JUnit (Spring).** Las pruebas son automáticas y cubren sincronización, permisos, reconexión, generadores e IA.
- **Git y GitHub.** Ramas por tarea, commits pequeños y un control previo a cada commit.

# 1. Introducción

## 1.1 Descripción del problema

Modelar un sistema con UML suele hacerse en herramientas de escritorio, de forma individual, y pasar del modelo al código es un trabajo manual y repetitivo. Cuando varias personas diseñan a la vez, se pierde la visión de quién cambió qué. Además, las herramientas de inteligencia artificial suelen vivir fuera del equipo: se usan en un chat aparte, sin conocer el diagrama ni lo que hizo cada integrante.

## 1.2 Objetivo general

Construir una plataforma CASE (*Computer-Aided Software Engineering*) web para modelar diagramas de clases UML 2.5 de forma colaborativa, en la que la **inteligencia artificial participe como un integrante más de la sala**, y que genere a partir del modelo un backend Spring Boot con PostgreSQL, una colección de Postman y un proyecto Flutter.

## 1.3 Objetivos específicos

1. Permitir crear y editar diagramas de clases manualmente, con todas las relaciones UML, multiplicidades, importación y exportación XMI para Enterprise Architect.
2. Crear o modificar el diagrama a partir de texto, de imágenes y de voz.
3. Soportar sesiones colaborativas de 2 a 3 personas con *host* y participantes, expulsión, reconexión y recuperación del estado.
4. Incorporar la IA como integrante de la sala: que no actúe hasta que alguien se lo pida, que sus ideas sean visibles, que conozca lo que hizo cada persona, que cada persona tenga su propio chat y que las sesiones puedan retomarse.
5. Ofrecer una vista móvil de solo lectura para seguir los cambios en vivo.
6. Generar el backend Spring Boot + PostgreSQL, la colección de Postman y el proyecto Flutter con persistencia local.
7. Ofrecer, de forma opcional, una IA local: un modelo abierto reentrenado para la tarea de modificar diagramas, que funcione sin internet.
8. Desplegar la plataforma en AWS con dominio propio y HTTPS, y documentar el proceso con PUDS.

## 1.4 Alcance

**Incluye:** editor UML de clases; texto, voz e imagen a UML; colaboración en tiempo real; identidad anónima por participante; registro de actividad compartido; chat privado con la IA en tres modos (preguntar, pedir cambio y revisar); ideas aplicables; sesiones continuas; vista móvil; XMI; generadores; IA local reentrenada; despliegue en AWS.

**No incluye (decisiones explícitas):** cuentas de usuario con inicio de sesión (el código de la sala es la llave de acceso y los roles existen solo mientras dura la sala); edición desde la vista móvil; infraestructura como código e integración continua; ejecutar el modelo local en el servidor pequeño de AWS.

## 1.5 Qué se construyó sobre la línea base

La plataforma partió de una base funcional del primer parcial (editor, colaboración, generadores). Esta entrega la cierra y la extiende: IA como participante (iteraciones I1 a I5), IA local (I6), endurecimiento, despliegue y revisión independiente del código (I7) y reentrenamiento del modelo. Cada iteración dejó un incremento probado e integrado, como se detalla en la Parte 2.
