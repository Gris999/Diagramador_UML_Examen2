# 1. Introducción

## 1.1 Continuación del primer parcial

Este documento es el **segundo parcial** y continúa el primero. El primer parcial dejó la base de la herramienta CASE colaborativa, organizada en tres ciclos de vida:

- **Ciclo 1:** gestionar salas de trabajo, modelar el diagrama de clases y guardar y recuperar su estado (CU-01, CU-02 y CU-05).
- **Ciclo 2:** colaborar en tiempo real, gestionar participantes, crear o modificar el modelo con lenguaje natural, imagen y voz, y validarlo con IA (CU-03, CU-04 y CU-06 a CU-09).
- **Ciclo 3:** exportar e importar en XMI, generar el script SQL, el proyecto Spring Boot con PostgreSQL y el proyecto móvil Flutter (CU-10 a CU-13).

Aquí no se repite nada de eso: el registro del proceso (PUDS) **sigue desde el ciclo de vida 4** y la numeración de los casos de uso continúa en CU-14. Lo ya hecho aparece solo como referencia (en gris en los diagramas) cuando un caso de uso nuevo lo reutiliza.

## 1.2 Qué se agrega en este parcial

Después del primer parcial el docente pidió que la inteligencia artificial deje de ser una herramienta aparte y pase a ser **un integrante más de la sala**. De ahí salen los tres ciclos nuevos:

- **Ciclo 4: identidad, actividad y chat con la IA.** Cada persona tiene un nombre visible y un identificador anónimo; la sala tiene un registro de actividad que todos ven; y cada persona conversa con la IA en un chat privado (CU-14 a CU-16).
- **Ciclo 5: la IA actúa a pedido y la sesión continúa.** La IA modifica el diagrama solo cuando se lo piden, revisa el modelo y publica ideas que cualquiera puede aplicar; y la persona puede retomar su sesión con el diagrama, la actividad y su chat (CU-17 a CU-20).
- **Ciclo 6: vista móvil, IA local y reentrenamiento.** Una vista de solo lectura para seguir la sala desde el celular, un proveedor de IA configurable y un modelo local, reentrenado con LoRA, que funciona sin internet (CU-21 a CU-23).

Además, este parcial agrega la justificación de las tecnologías (capítulo 0), el modelo C4 en el diseño y el despliegue en AWS con dominio y HTTPS (Anexo C).

## 1.3 Capítulo 10: Lenguaje de modelado de software (modelo C4)

El **modelo C4** es una técnica para describir y visualizar la arquitectura de un sistema en cuatro niveles de detalle, de lo general a lo particular (Brown, s. f.):

1. **Contexto:** el sistema como una caja negra, sus usuarios y los sistemas externos con los que se relaciona.
2. **Contenedores:** las aplicaciones y almacenes de datos que se ejecutan por separado (una aplicación web, una API, una base de datos) y cómo se comunican.
3. **Componentes:** las piezas internas de un contenedor y sus responsabilidades.
4. **Código:** las clases o módulos principales de un componente.

C4 no reemplaza a UML: lo complementa, porque cada nivel puede detallarse con diagramas UML cuando hace falta. Su ventaja es que cada diagrama tiene un público claro (quien decide, quien construye, quien programa) y se mantiene legible.

**Aplicación en el proyecto.** En la sección 2.3.1 se presentan los cuatro niveles: el contexto (participantes, observadores, Gemini, Ollama y Enterprise Architect), los contenedores (aplicación web, API y tiempo real, generador Spring, PostgreSQL y Redis), los componentes de la API de Django (relé de WebSocket, actividad e identidad, chat con la IA, guardia de cambios, proveedores de IA, XMI y generador Flutter) y el código de los proveedores de IA.

## 1.4 Capítulo 11: La IA como integrante del equipo y los modelos reentrenados

El capítulo 7 del primer parcial presentó cómo se aplica la IA a la ingeniería de software. Este capítulo agrega dos ideas que se usan en los ciclos nuevos.

**La IA como integrante de la sala.** Un solo modelo de lenguaje atiende a varias personas a la vez, por lo que hace falta separar el contexto de cada una. Se resolvió con un **chat privado por participante** y con el **registro de actividad** de la sala como contexto compartido, de modo que la IA puede responder "¿qué hizo Bruno?". Tiene tres modos: *preguntar* (solo responde), *pedir cambio* (propone un cambio que se aplica en el navegador de quien lo pidió y queda registrado como "IA, a pedido de X") y *revisar* (publica observaciones para toda la sala, cada una con un botón para aplicarla). Para que sea un integrante confiable y no un riesgo, la IA no hace nada hasta que alguien se lo pide, los cambios que eliminan elementos piden confirmación, hay topes de uso por persona y por sala para controlar el costo, y si el proveedor falla el diagrama no cambia.

**IA local y reentrenada.** Como alternativa sin internet y sin enviar datos a un tercero, se reentrenó un modelo abierto. Se usó **LoRA** (*Low-Rank Adaptation*), que congela el modelo y entrena solo matrices de bajo rango añadidas a sus capas, con menos del 1 % de los parámetros (Hu et al., 2021), sobre un modelo cuantizado a 4 bits en la variante **QLoRA** (Dettmers et al., 2023), de la familia Qwen (Qwen Team, 2025), con el marco MLX de Apple. El resultado, un adaptador de unas decenas de megabytes, se fusiona con el modelo base y se sirve con Ollama. Los datos de entrenamiento se generan de forma determinista y se reservan ejemplos de prueba que el modelo nunca ve, para medir con honestidad si mejoró. El detalle, con la evidencia de cómo se entrenó, está en el Anexo B.

