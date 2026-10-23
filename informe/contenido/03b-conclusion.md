# 4. Conclusión

Este segundo parcial continuó la herramienta CASE colaborativa del primero sin rehacerla: los casos de uso CU-01 a CU-13 se mantienen y se reutilizan, y se agregaron seis casos de uso nuevos (CU-14 a CU-19) en tres ciclos de vida. Su valor está en el intento que pidió el docente: **reducir el tiempo de desarrollo y mejorar la productividad** del equipo que diseña.

- **La IA como integrante de la sala** cambió la forma de trabajar: ya no es un chat aparte que solo entiende una instrucción de edición, sino un integrante que conoce el diagrama y la actividad de todos, responde cuando se le pregunta, cambia el diagrama solo cuando se le pide y deja sus ideas a la vista para que cualquiera las aplique.
- **La identidad y la actividad** hicieron visible quién hizo qué, y **las sesiones que continúan** permiten dejar el trabajo hoy y retomarlo mañana con el diagrama, la actividad y la conversación propia.
- **La vista del celular** sirve para informarse, sin editar, cuando la persona está en movimiento.
- **La IA local reentrenada** demostró, con evidencia medible (Anexo B), que un modelo abierto de 4 mil millones de parámetros reentrenado con LoRA acierta más que el mismo modelo sin entrenar al modificar diagramas, y funciona sin internet.

El modelado siguió el Proceso Unificado de Desarrollo de Software con UML 2.5: los actores son los roles reales de las personas (Diseñador y Colaborador), cada caso de uso es un objetivo completo y no una operación suelta, y lo que no lo inicia un actor se registró como requisito adicional. Los diagramas se hicieron en Enterprise Architect.

**Limitaciones conocidas.** Los diagramas exportados llevan la marca de agua de la versión de prueba de Enterprise Architect. La conversación con la IA es privada para cada persona, aunque la IA conoce la actividad de todos; si se prefiere una conversación compartida por toda la sala, sería un cambio acotado en el chat. El modelo local depende de un computador con memoria suficiente y no se mide con la misma exactitud que Gemini en pedidos largos.
