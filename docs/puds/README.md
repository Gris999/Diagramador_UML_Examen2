# Documentación PUDS — Diagramador UML

Este directorio reúne los **artefactos del Proceso Unificado de Desarrollo de Software (PUDS)** del proyecto. La organización sigue el material de la cátedra (*El Proceso Unificado de Desarrollo de Software*, A.U.S. Gustavo Torossi): cuatro fases, cinco disciplinas y, por cada disciplina, los artefactos de la tabla "Resumen de Trabajadores, Actividades y Artefactos" (páginas 23–25 del PDF).

> **Convención.** ✅ implementado y verificado · 🔄 en construcción · 📋 planificado. Lo marcado *(verificado)* se comprobó leyendo el código o ejecutando pruebas; *(propuesta)* es diseño que todavía no existe.
> **Estado al 2026-10-21.** Fecha de entrega estimada: 2026-11-04 *(por confirmar con el docente)*.

## 1. Cómo se aplica PUDS aquí

- **Dirigido por casos de uso.** Los requisitos funcionales se expresan como casos de uso (`01-requisitos.md`) y cada iteración se elige por los casos de uso que completa y por los riesgos que reduce.
- **Centrado en la arquitectura.** La arquitectura base ya existe y está desplegada (`03-diseno.md`); las iteraciones nuevas la extienden sin reescribirla (`AGENTS.md`: no reescribir desde cero).
- **Iterativo e incremental.** Cada iteración termina en un incremento probado e integrado en la rama `develop`.
- **Ciclo de vida.** Cuatro fases, cada una cerrada por un hito:

| Fase | Hito PUDS | Qué significa en este proyecto | Estado |
|---|---|---|---|
| **Inicio** | Objetivos del ciclo de vida | Alcance acordado (RF-01…RF-33), plan, riesgos, línea base de `develop` limpia | ✅ cerrada (I0) |
| **Elaboración** | Arquitectura del ciclo de vida | Arquitectura validada con un caso de uso de punta a punta (nombre → acción → registro de actividad visible para todos) | ✅ cerrada (I1), verificada en dos navegadores y en el sitio desplegado |
| **Construcción** | Capacidad operativa inicial | RF-23…RF-32 implementados y probados; sistema estable para usar | ✅ I2 a I5 listas; falta el cierre (I7) y, si da el tiempo, la IA local (I6) |
| **Transición** | Lanzamiento del producto | Sistema desplegado, documentación final, demostración ensayada | 📋 I7 (congelamiento ≈ 2026-11-02) |

## 2. Mapa de artefactos (tabla del PDF → este proyecto)

| Disciplina | Artefactos PUDS | Documento | Estado |
|---|---|---|---|
| Requisitos | Modelo de casos de uso, glosario, requisitos adicionales, casos de uso detallados | [`01-requisitos.md`](01-requisitos.md) y [`../REQUIREMENTS.md`](../REQUIREMENTS.md) | ✅ |
| Análisis | Clases de análisis, realización de casos de uso (análisis), paquetes | [`02-analisis.md`](02-analisis.md) | ✅ base · 🔄 IA participante |
| Diseño | Descripción de la arquitectura, clases de diseño, subsistemas, interfaces, realización de casos de uso (diseño), **modelo de despliegue** | [`03-diseno.md`](03-diseno.md), [`../DESPLIEGUE.md`](../DESPLIEGUE.md) | ✅ base · 🔄 IA participante |
| Implementación | Componentes, modelo de implementación, plan de integración de construcciones | [`04-implementacion.md`](04-implementacion.md) | ✅ |
| Prueba | Plan de prueba, casos de prueba, procedimientos, defectos, evaluación de prueba | [`05-pruebas.md`](05-pruebas.md) | ✅ plan · 🔄 evidencia |
| Gestión (apoyo) | Plan de desarrollo, lista de riesgos, plan de despliegue | [`../PLAN_PUDS_IA_PARTICIPANTE.md`](../PLAN_PUDS_IA_PARTICIPANTE.md), [`../DESPLIEGUE.md`](../DESPLIEGUE.md), [`../GAP_MATRIX.md`](../GAP_MATRIX.md) | ✅ |

## 3. Iteraciones realizadas y previstas

| Iteración | Fase | Resultado | Estado |
|---|---|---|---|
| I0 — Cierre de la línea base | Inicio | Todo lo del primer parcial funcionando (editor, IA por texto/imagen/voz, colaboración, XMI con Enterprise Architect, Spring/Postman, Flutter); entidad intermedia visual para M:N; despliegue en AWS con dominio y HTTPS; documentación de despliegue | ✅ |
| I1 — Identidad y registro de actividad | Elaboración | Nombre visible por participante, registro de actividad compartido, panel de actividad | ✅ |
| I2 — Chat individual con contexto | Construcción | Chat privado con la IA que conoce la actividad de todos | ✅ |
| I3 — Acciones, sugerencias y revisión | Construcción | La IA cambia el diagrama solo a pedido; ideas visibles; revisión; la IA como integrante de la sala | ✅ |
| I4 — Sesiones continuas | Construcción | Recuperar diagrama, actividad y chat propio al volver | ✅ validado de punta a punta en local (2026-10-21); falta repetirlo en el sitio desplegado |
| I5 — Vista móvil de seguimiento | Construcción | Vista de solo lectura en vivo | ✅ |
| I6 — IA local (opcional) | Construcción | Proveedor configurable Gemini / local (Ollama, Qwen) | 📋 opcional |
| I7 — Endurecimiento y entrega | Transición | Despliegue final, prueba de humo, documentación y demo | 📋 |

El detalle de cada iteración (objetivo, esfuerzo, rama, criterios de aceptación) está en la sección 8 del [plan de trabajo](../PLAN_PUDS_IA_PARTICIPANTE.md).

## 4. Trazabilidad

La matriz requisito → caso de uso → iteración → verificación está en la sección 14 del plan. El estado de cada requisito se lleva en [`../GAP_MATRIX.md`](../GAP_MATRIX.md); si un requisito cambia de estado, se actualiza allí.
