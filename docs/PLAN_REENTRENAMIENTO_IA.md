# Plan: modelo de IA reentrenado y desplegado

| | |
|---|---|
| **Rama** | `feat/ia-reentrenada` (no toca lo desplegado hasta aprobarse) |
| **Fecha del plan** | 2026-10-22 |
| **Estado** | Prueba de viabilidad (día 1) **superada**: se entrenó un adaptador real, mejoró frente al base y se desplegó en Ollama. Ver la bitácora al final |
| **Entrega estimada del proyecto** | 2026-11-04 *(por confirmar con el docente)* |

## 1. Objetivo y supuesto a confirmar

**Objetivo:** tomar un modelo de lenguaje abierto (familia Qwen), **reentrenarlo** (*fine-tuning*) para que convierta un pedido en el JSON de cambios que espera el diagramador, **desplegarlo** y poder **demostrar cómo se entrenó**.

**Supuesto (por confirmar):** los apuntes del audio del docente dicen *"IA local (no es obligatorio) (valorarle) (funcionar con IA's convencionales) IA studio"* y no mencionan reentrenar. Varios compañeros del grupo entendieron que se pedía un modelo reentrenado y desplegado, y que cada grupo debe mostrar cómo lo entrenó; por eso se asume. Es **opcional y valorable**, y debe convivir con Gemini. Hasta la fecha no se ha entrenado nada: `docs/IA_LOCAL.md` describe un Qwen ejecutado tal cual, sin entrenamiento.

## 2. Cómo funciona (explicación para el informe)

- El **modelo base** ya sabe español, programar y escribir JSON.
- El **fine-tuning** le da cientos de ejemplos resueltos de *esta* tarea (diagrama actual + pedido → JSON exacto) para que practique y corrija sus errores.
- **LoRA** congela el modelo y entrena solo unas matrices pequeñas añadidas (≈ 1 % de los parámetros). El resultado es un **adaptador** de unas decenas de MB; modelo base + adaptador = modelo reentrenado. **QLoRA** hace lo mismo sobre un modelo comprimido a 4 bits, para que quepa en 16 GB.
- La **pérdida (*loss*)** mide cuánto se equivoca el modelo al predecir cada palabra del JSON correcto. Debe bajar durante el entrenamiento; su curva es evidencia.

## 3. Evidencia de que se entrenó de verdad

Todo se **genera por el proceso**, no se escribe a mano:

| Evidencia | Qué demuestra |
|---|---|
| Log crudo del entrenamiento (pérdida por iteración, fechas, equipo) | Que corrió en el Mac del grupo |
| Adaptador entrenado (`.safetensors`) con su SHA-256 | Que existe un resultado distinto del modelo base |
| Datos de entrenamiento y `MANIFEST.json` (semilla, conteos, hashes, comprobación de que no hay ejemplos de prueba en entrenamiento) | Con qué se entrenó y que se puede repetir |
| Resultados de evaluación en JSON: base contra reentrenado, sobre ejemplos no vistos | Si mejoró, y cuánto |
| `ollama show` del modelo desplegado | Que el modelo desplegado es el entrenado |
| `comparar.py`: el mismo pedido al base y al reentrenado, lado a lado | La diferencia visible |
| Mini-entrenamiento en vivo ante el docente (pocos minutos) | Ver bajar la pérdida en directo |
| Todo en el repositorio con un comando de repetición (semilla fija) | Reproducibilidad |

## 4. Estructura

```
ml/
  README.md              cómo repetir todo, comandos exactos
  requirements.txt       versiones fijas
  data/
    generar_dataset.py   generador determinista (semilla fija)
    MANIFEST.json        conteos, semilla, hashes
    muestra_*.jsonl      ejemplos legibles
  train/
    config.yaml          hiperparámetros
    entrenar.sh          entrena y guarda el log
  eval/
    evaluar.py           base vs reentrenado, resultados en JSON
    comparar.py          lado a lado
  export/
    importar_ollama.sh   fusiona y crea el modelo en Ollama
  runs/<fecha>/          log, loss.csv, gráfico, hash del adaptador, métricas
  tests/                 pruebas del generador y de los verificadores
```

Los pesos grandes (modelo base y fusionado) no se versionan; el adaptador (decenas de MB) sí, o se publica como *release*, con su hash.

## 5. Datos

- **Un generador, no escritura a mano**: unos 1500 ejemplos "diagrama de entrada + pedido → JSON de cambios".
- **Correctos por construcción**: el JSON esperado lo calcula el programa con reglas (no un modelo) en los tres formatos que ya usa la app (crear, editar con `original`/`editado` y eliminar con `eliminar`).
- **Variedad**: 14 tipos de operación (crear clase, agregar atributo o método, cambiar tipo, renombrar, borrar atributo, método, clase o relación, herencia, composición, muchos a muchos, dominio completo), con muchas redacciones (sinónimos, tuteo, errores leves). Opcionalmente Gemini parafrasea los **pedidos**, nunca el resultado esperado.
- **Prueba sin trampa**: conjunto de prueba con **entidades y redacciones no vistas** más los 10 pedidos fijos de `scripts/evaluar_ia.py`; un script comprueba que no se repita ningún ejemplo entre entrenamiento y prueba.
- **Decisión de diseño**: el modelo reentrenado puede usar un **prompt corto** (las reglas quedan aprendidas). Acelera el entrenamiento y reduce errores; el proveedor necesita un constructor de prompt propio para este modelo.

## 6. Entrenamiento

- **Base**: un Qwen de 3 a 4 mil millones de parámetros (el de 9B no cabe cómodamente para entrenar en 16 GB). Se decide en la prueba de viabilidad.
- **Herramienta**: MLX (Apple Silicon). Plan B: Google Colab gratuito.
- **Configuración inicial**: QLoRA, rango 16, unas 1000 iteraciones, validación periódica para detectar sobreajuste, secuencias cortas. Se ajusta con las mediciones.

## 7. Evaluación

- Mismo conjunto de prueba para: base chico sin entrenar, reentrenado, Qwen 3.5 9B (el actual) y Gemini.
- Métricas: JSON válido, exactitud estricta (verificadores de `scripts/evaluar_ia.py`), eliminaciones inesperadas, tiempo por respuesta, con el tamaño de la muestra.
- **Criterio de éxito**: el reentrenado supera con claridad a su base sin entrenar. **No** se promete superar a Gemini ni al 9B; los números se publican como salgan.

## 8. Despliegue

1. Fusionar el adaptador con el modelo e importarlo a Ollama como `uml-qwen`.
2. La app lo usa con el interruptor existente (`AI_PROVIDER=ollama`, `OLLAMA_MODEL=uml-qwen`).
3. Para que lo use cualquiera que entre a diagramador.dev, el servidor de AWS se conecta al Ollama del Mac con un túnel seguro (Tailscale o Cloudflare). Se decide al final; sin túnel, solo lo usa quien corre la app en el Mac.

## 9. Calendario

| Día | Qué |
|---|---|
| 1 | Prueba de viabilidad: instalar MLX, bajar el modelo, mini-entrenamiento y llegar hasta Ollama. *Si falla, se cambia de modelo o herramienta antes de invertir más* |
| 2 | Generador de datos con pruebas |
| 3 | Medición del base y entrenamiento completo |
| 4 | Evaluación y ajustes |
| 5 | Despliegue, integración y evidencia lista para mostrar |
| 6 a 12 | Margen, informe en Word/PDF y ensayo de la demostración |

## 10. Riesgos

| Riesgo | Respuesta |
|---|---|
| No mejora | Reportarlo, ajustar datos; el proceso sigue siendo una demostración válida |
| Memoriza plantillas | La prueba usa entidades y redacciones nuevas |
| 16 GB insuficientes | Modelo o secuencias más chicos; o Colab |
| Falla el paso a Ollama | Convertir con llama.cpp |
| "Reentrenar" significa otra cosa | Confirmar con el docente; lo construido sirve igual |

## 11. Bitácora

### 2026-10-22 — Día 1: prueba de viabilidad (superada)

Corrida completa en `ml/runs/spike/` (equipo: Apple M5, 16 GB, macOS 26.5.2; MLX 0.32.4, mlx-lm 0.32.2):

| Paso | Resultado |
|---|---|
| Datos | 240 de entrenamiento, 36 de validación y 60 de prueba, generados con semilla 42 (`ml/data/generar_dataset.py`); 12 tipos de operación; la prueba incluye 5 entidades que el entrenamiento nunca ve y redacciones reservadas; sin fugas comprobado (`MANIFEST.json`) |
| Modelo base | Qwen3-4B-Instruct-2507, 4 bits (MLX), ya presente en el equipo; 4,02 mil millones de parámetros |
| Entrenamiento | LoRA, rango 16, 16 capas, 100 iteraciones (≈ 9 min). Se entrenó el **0,365 %** de los parámetros (14,68 M). Pérdida de entrenamiento 1,370 → 0,093; de validación 2,662 → 0,108 (`loss.csv`, `train.log`) |
| Adaptador | `adapters.safetensors`, 58.744.712 bytes, SHA-256 `6e0a27f5…0726a9` (`adaptador.sha256`) |
| Despliegue | Fusionado (`mlx_lm fuse --dequantize`) e importado a Ollama como `uml-qwen-spike` (3,4 GB, `--quantize int4`); responde por la API de Ollama |

**Evaluación en las mismas 60 pruebas** (respuesta idéntica al JSON correcto, comparación canónica; `eval-*.json` guarda cada respuesta cruda):

| Modelo | JSON válido | Correctas | Promedio |
|---|---|---|---|
| Qwen3-4B base, sin entrenar | 60/60 | **14/60** | 4,6 s |
| + LoRA (MLX) | 55/60 | **35/60** | 4,0 s |
| Desplegado en Ollama (int4) | 54/60 | **33/60** | 4,1 s |

Por operación, con 100 iteraciones y 240 ejemplos: relación, herencia y eliminar relación pasaron de 0/5 a 5/5; eliminar clase de 0/5 a 4/5. Siguen mal: agregar método (2/5), eliminar método (0/5), renombrar atributo (0/5) y crear dos clases con relación (0/5). Es una prueba de viabilidad: el entrenamiento completo usará más datos e iteraciones.

**Lo que enseñó la prueba (defectos reales encontrados):**

1. **Primera evaluación del reentrenado: 0/60 válidas.** La plantilla de chat de Qwen3 renderiza el turno del asistente con un bloque `<think></think>` vacío; el modelo aprendió a emitirlo y aparecía antes del JSON. El JSON de debajo era correcto. Se quita el bloque al interpretar la respuesta (`quitar_razonamiento`), y el proveedor de la app deberá hacer lo mismo. Las respuestas crudas se conservaron y se volvieron a puntuar (`reevaluar.py`, con el motivo anotado en el archivo).
2. **El modelo base falla de verdad, no por una comparación estricta**: devuelve el diagrama completo en vez de los cambios y, al pedirle eliminar, no marca nada.
3. **La cuantización a 4 bits de Ollama cuesta 2 aciertos** frente a MLX (35 → 33). Se mide, no se esconde.
4. **Algunas respuestas se cortan o se repiten** (5 inválidas en MLX, 6 en Ollama): efecto de pocas iteraciones; se reevalúa con el entrenamiento completo.

**Siguiente (día 2):** ampliar el generador (composición/agregación, muchos a muchos, dominios completos, más redacciones), 1500 ejemplos de entrenamiento, y reentrenar con más iteraciones; fijar el punto de parada con la pérdida de validación.

| Fecha | Hecho | Resultado |
|---|---|---|
| 2026-10-22 | Plan escrito; rama `feat/ia-reentrenada` creada | — |
| 2026-10-22 | Prueba de viabilidad completa (datos → entrenamiento → evaluación → Ollama) | 14/60 → 35/60 (MLX) → 33/60 (Ollama) |
