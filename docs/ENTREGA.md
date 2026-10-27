# Lista final de entrega — versión 1.0

| | |
|---|---|
| **Proyecto** | Diagramador UML colaborativo con IA como integrante de la sala (Ingeniería de Software I) |
| **Versión** | `v1.0` (etiqueta en la rama `develop`) |
| **Repositorio** | https://github.com/Gris999/Diagramador_UML_Examen2 |
| **Sitio desplegado** | https://diagramador.dev (AWS EC2, HTTPS) |
| **Fecha estimada de entrega** | 2026-11-04 *(por confirmar con el docente)* |
| **Estado al congelar** | 2026-10-22: pruebas en verde, sitio comprobado con `scripts/smoke-test.sh`, sin secretos en el repositorio |

## 1. Qué se entrega

| Entrega | Dónde está |
|---|---|
| Código fuente (frontend, backend, generador Spring) | Repositorio, etiqueta `v1.0` |
| Aplicación funcionando | https://diagramador.dev |
| Documentación PUDS por disciplina (requisitos, análisis, diseño, implementación, prueba) | [`puds/`](puds/README.md) |
| Plan de trabajo PUDS (fases, iteraciones, riesgos, trazabilidad) | [`PLAN_PUDS_IA_PARTICIPANTE.md`](PLAN_PUDS_IA_PARTICIPANTE.md) |
| Estado de cada requisito | [`GAP_MATRIX.md`](GAP_MATRIX.md) y [`REQUIREMENTS.md`](REQUIREMENTS.md) |
| Despliegue (AWS, dominio, HTTPS, seguridad, pruebas de humo) | [`DESPLIEGUE.md`](DESPLIEGUE.md) y `scripts/smoke-test.sh` |
| IA local (instalación, evaluación 10/10) | [`IA_LOCAL.md`](IA_LOCAL.md) y `scripts/evaluar_ia.py` |
| Guion de la demostración | [`DEMO.md`](DEMO.md) |
| Evidencia de pruebas y defectos | [`puds/05-pruebas.md`](puds/05-pruebas.md) |

## 2. Requisitos: resumen

Todos los requisitos de `REQUIREMENTS.md` figuran como **hechos** salvo los que se indican (ver [`GAP_MATRIX.md`](GAP_MATRIX.md) para el detalle y la evidencia):

| Grupo | Estado |
|---|---|
| Editor UML manual, texto → UML, imagen → UML, voz → UML | Hecho |
| Colaboración de 2–3 personas, host/participantes, expulsar, reconexión y recuperación de estado | Hecho |
| XMI con Enterprise Architect (en ambos sentidos, con pruebas de seguridad) | Hecho |
| Generación Spring Boot + PostgreSQL, colección Postman, proyecto Flutter con SQLite sin conexión | Hecho |
| IA como integrante de la sala: identidad, actividad, chat (compartido por la sala desde el segundo parcial), cambios a pedido, revisión con ideas aplicables, sesiones continuas, vista móvil | Hecho (RF-23 a RF-32) |
| IA local (Ollama + Qwen 3.5 9B) | Hecho: evaluado con verificaciones estrictas, 10/10 pedidos correctos (RF-33) |
| Despliegue en AWS con dominio y HTTPS | Parcial: manual y repetible; sin infraestructura como código ni CI/CD |
| IA local **dentro de la app móvil generada** | Parcial: el asistente de la app Flutter es un intérprete de comandos determinista, no un modelo |
| Cobertura de pruebas / formalidad UML 2.5 / documentación PUDS | Parcial: ver §4 |

## 3. Estado de las pruebas (2026-10-22)

| Suite | Resultado |
|---|---|
| Frontend (Karma) | 201 correctas, 0 fallos; `ng build` sin errores |
| Django sin base de datos | 101 correctas |
| Django con base de datos (`settings_test`) | 126 correctas |
| Spring (incluye compilar de verdad el proyecto generado) | 9 correctas |
| Pruebas manuales en producción | Tres identidades + vista móvil: sincronización, IA, revisión, expulsión, relevo de host, reconexión |
| Revisión de código independiente | Dos rondas (I1–I5 y la revisión final del 2026-10-22); hallazgos corregidos con pruebas o documentados como límites de diseño (`puds/05-pruebas.md` D-08) |
| Escaneo de secretos (árbol actual y 131 commits) | Sin hallazgos; la contraseña antigua de PostgreSQL se rotó y la antigua es rechazada |

Comandos exactos: [`puds/05-pruebas.md`](puds/05-pruebas.md) §3.

## 4. Limitaciones conocidas (decirlas con honestidad)

1. **Sin cuentas:** el código de la sala es la capacidad de acceso; la vista móvil es de solo lectura pero **no** es un permiso separado (`DESPLIEGUE.md` §7).
2. **Atribución a la IA** (`via_ia`) la declara el navegador: es transparencia, no auditoría a prueba de manipulación.
3. **Servidor pequeño** (2 vCPU, ~2 GB): la IA local no corre allí; la nube (Gemini) sí. Si el servidor se reinicia, las personas conectadas pierden la conexión y deben volver a entrar (el estado de las salas se limpia al arrancar, D-04); el diagrama se recupera desde el respaldo.
4. **Dominio** `diagramador.dev` vence el 2027-10-21 (renovación automática apagada a propósito).
5. **Pruebas en dispositivos reales:** la vista móvil se probó en una ventana del tamaño de un celular, no en un teléfono físico.
6. **Calidad de la IA:** depende de Gemini o del modelo local; las respuestas pueden fallar o equivocarse; en ese caso el chat muestra el error y el diagrama no cambia, y los cambios que eliminan elementos piden confirmación.

## 5. Lo que tiene que hacer una persona antes de entregar

- [ ] **Confirmar con el docente** la fecha de entrega y si exige un formato de informe concreto (se asumió la tabla de artefactos del material de la cátedra).
- [ ] **Ensayar la demostración** con las personas reales (`DEMO.md`), cada una en su propio navegador o perfil.
- [ ] **Probar la vista móvil en un celular real** (abrir el enlace del botón "📱 Copiar enlace…").
- [ ] **Repetir el intercambio XMI con Enterprise Architect** y la generación de Flutter/Spring el mismo día de la demostración.
- [ ] **Reservar una IP fija en AWS (IP elástica)** si el servidor se llegara a apagar: sin ella la IP cambia y hay que actualizar el DNS (`DESPLIEGUE.md` §5).
- [ ] **Restringir el puerto 22 a la IP de quien administra** (opcional; riesgo: quedarse sin acceso si la IP cambia).
- [ ] **Decidir si se baja la IA local o se muestra solo Gemini** en la demostración (`DEMO.md` §4).
- [ ] **Imprimir o exportar a PDF** la documentación que pida el docente (`docs/puds/` está en Markdown con diagramas Mermaid).

## 6. Antes de empezar la demostración (30 minutos antes)

1. `scripts/smoke-test.sh` → debe decir "Todo en orden."
2. Abrir https://diagramador.dev en Chrome, crear una sala de prueba, agregar una clase, abrir el chat y hacer una pregunta (comprueba la IA y la base de datos).
3. Tener a mano: Enterprise Architect abierto, una imagen de un diagrama de clases, el celular con el enlace de seguimiento.
4. Si algo falla: crear una sala nueva; el plan B está en `DEMO.md`.

## 7. Cómo correr todo en un computador (si piden ver el código funcionando)

```bash
# red y base de datos
docker network create backend            # solo la primera vez
docker compose -f docker-compose.db.yml up -d
# aplicación (Django + Redis + Spring + Angular)
docker compose -f docker-compose.app.yml up -d --build
```

Requiere `back_generador_bd/.env` (plantilla en `back_generador_bd/.env.example`; los valores reales nunca se suben a git). Angular queda en http://localhost:4200. Detalle de puertos y de variables en `AGENTS.md` y `DESPLIEGUE.md`.

## 8. Qué quedó fuera (a propósito)

Cuentas y autenticación; separar permisos de lectura y de edición; ejecutar el modelo local en el servidor de AWS; infraestructura como código y CI/CD; reescribir el historial de git (la contraseña antigua ya no sirve, pero sigue visible en commits viejos).
