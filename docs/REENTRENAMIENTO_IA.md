# Reentrenamiento del modelo de IA

| | |
|---|---|
| **Qué se hizo** | Se reentrenó (*fine-tuning* con LoRA) un modelo abierto de la familia Qwen para convertir un pedido en el JSON de cambios que entiende el editor, se midió contra el modelo sin entrenar y se desplegó en Ollama |
| **Dónde** | En un Mac con chip Apple M5 y 16 GB de memoria, con MLX |
| **Código y evidencia** | Carpeta `ml/` del repositorio (rama `feat/ia-reentrenada`): generador de datos, entrenamiento, evaluación, scripts de despliegue y la carpeta de cada corrida con sus registros |
| **Estado** | Primera corrida completa (2026-10-22); segunda corrida con más datos de lo que falló (sección 7) |

## 1. Objetivo y alcance

El docente planteó la IA local como un extra **no obligatorio y valorable** (apuntes de clase). La interpretación del equipo, coincidente con la de otros grupos, es que se espera un modelo abierto **reentrenado por el propio equipo, desplegado y con la explicación de cómo se entrenó**. Este anexo documenta eso con evidencia reproducible. La plataforma sigue funcionando con Gemini por defecto; el modelo reentrenado es opcional y se activa por configuración.

## 2. Cómo funciona el reentrenamiento

- El **modelo base** (Qwen3-4B-Instruct, 4 mil millones de parámetros, cuantizado a 4 bits) ya sabe español, programar y escribir JSON.
- El ***fine-tuning*** le da cientos de ejemplos resueltos de *esta* tarea (diagrama actual + pedido → JSON exacto) para que practique y corrija sus errores.
- **LoRA** (Hu et al., 2021) congela el modelo y entrena solo unas matrices pequeñas de bajo rango añadidas a sus capas: aquí **22 millones de parámetros, el 0,55 % del total**. El resultado es un **adaptador** de 88 MB. **QLoRA** (Dettmers et al., 2023) hace lo mismo sobre el modelo cuantizado, lo que permite entrenar en 16 GB.
- La **pérdida** mide cuánto se equivoca el modelo al predecir cada palabra del JSON correcto; debe bajar. Solo se mide sobre la respuesta, no sobre el pedido.

## 3. Diseño del experimento

### 3.1 Datos

- **Generador determinista** (`ml/data/generar_dataset.py`, semilla fija): 16 tipos de operación (crear clase, agregar atributo, método o varios atributos, cambiar tipo, renombrar atributo o clase, eliminar atributo, método, clase o relación, crear relaciones, herencia, crear varias clases...), con redacciones variadas (sinónimos, tuteo, errores leves de ortografía, «por favor»).
- **Respuestas correctas por construcción:** el JSON esperado lo calcula el programa con reglas, no otro modelo. Al modificar una clase existente se pide la clase completa (mismo id, todos sus atributos y métodos); al eliminar se pide solo la marca `eliminar`.
- **Prompt corto:** el modelo aprende las reglas del editor, así que el pedido solo lleva el diagrama compacto (ids cortos, sin posiciones) y la frase. El proveedor de la plataforma (`modelo_reentrenado.py`) traduce los ids largos del editor a cortos y vuelve a los reales en la respuesta; una prueba automática garantiza que el texto del prompt sea idéntico al del entrenamiento.
- **Conjuntos:** 1500 ejemplos de entrenamiento, 150 de validación y 200 de prueba. La prueba usa **entidades que el modelo nunca vio** (Paciente, Doctor, Vehículo, Canción, Mascota, Película, Gimnasio, Receta) y **redacciones reservadas**; un script comprueba que no haya ejemplos repetidos entre entrenamiento y prueba.

### 3.2 Entrenamiento

LoRA de rango 16 sobre las últimas 24 capas, lote de 2, tasa de aprendizaje 1·10⁻⁴, 1000 iteraciones (≈ 1,3 épocas), secuencias de hasta 1024 *tokens*, validación cada 100 iteraciones y un punto de control cada 100. Duración: **1 h 23 min** en el Mac del equipo.

### 3.3 Evaluación

Se genera con decodificación determinista (temperatura 0) y se compara el JSON con el correcto en forma canónica: mismas clases, atributos con su tipo, métodos y relaciones con sus extremos, sin importar el orden ni los ids. Una respuesta cuenta como correcta **solo si es exactamente igual**; si el modelo pierde un atributo, inventa otro o devuelve un JSON roto, es incorrecta. Se mide el mismo conjunto de 200 ejemplos con tres modelos: el base sin entrenar, el reentrenado (MLX) y el reentrenado ya desplegado en Ollama.

## 4. Resultados de la primera corrida

![Comparación de aciertos del modelo base, el reentrenado y el desplegado en Ollama](../ml/runs/dia2/comparacion.png)
*Figura B.1. Aciertos sobre 200 ejemplos que el modelo nunca vio.*

| Modelo | JSON válido | Respuestas exactamente correctas | Tiempo promedio |
|---|---|---|---|
| Qwen3-4B base, sin entrenar | 192/200 | **70/200** (35 %) | 4.7 s |
| Reentrenado con LoRA (MLX) | 197/200 | **154/200** (77 %) | 3.79 s |
| Reentrenado y desplegado en Ollama (int4) | 196/200 | **153/200** (76 %) | 4.46 s |

| Operación | Base | Reentrenado | Ollama |
|---|---|---|---|
| agregar atributo | 9/13 | 12/13 | 12/13 |
| agregar metodo | 7/13 | 1/13 | 2/13 |
| agregar varios atributos | 6/13 | 13/13 | 13/13 |
| crear clase | 11/13 | 10/13 | 8/13 |
| crear clase con metodos | 4/13 | 10/13 | 10/13 |
| crear dos con relacion | 0/13 | 1/13 | 1/13 |
| crear varias clases | 13/13 | 12/13 | 10/13 |
| editar tipo | 11/13 | 10/13 | 10/13 |
| eliminar atributo | 0/12 | 10/12 | 10/12 |
| eliminar clase | 0/12 | 12/12 | 12/12 |
| eliminar metodo | 0/12 | 11/12 | 11/12 |
| eliminar relacion | 3/12 | 12/12 | 12/12 |
| herencia | 0/12 | 12/12 | 12/12 |
| relacion | 0/12 | 12/12 | 12/12 |
| renombrar atributo | 3/12 | 7/12 | 8/12 |
| renombrar clase | 3/12 | 9/12 | 10/12 |

La pérdida de validación bajó de 2,23 al inicio a 0,04 al final (mínimo de 0,024 en la iteración 600):

![Curva de pérdida del entrenamiento](../ml/runs/dia2/curva-perdida.png)
*Figura B.2. Curva de pérdida del entrenamiento y de la validación.*

## 5. Análisis

**Lo que mejoró con claridad.** El modelo pasó de acertar el 35 % al **77 %**. Las operaciones que el modelo sin entrenar casi nunca hacía bien pasaron a hacerse bien: relaciones, herencia y eliminar clase, atributo, método o relación (de entre 0 y 3 aciertos sobre 12 a entre 10 y 12 sobre 12). El modelo base tendía a devolver el diagrama completo en vez de solo el cambio, y al pedirle eliminar no marcaba nada; el reentrenado aprendió el formato exacto de la plataforma.

**Lo que no mejoró, y por qué.** Dos operaciones fallan, y una incluso empeora frente al modelo base:

- **Agregar un método** (de 7/13 a 1/13): el modelo devuelve la clase tal cual estaba, **sin agregar el método pedido**. Se verificó que no es un problema de redacción nueva: con frases iguales a las del entrenamiento solo acierta 7 de 24.
- **Crear dos clases con una relación** (1/13): el modelo mezcla atributos de otras clases del diagrama.

La hipótesis es que son operaciones con pocos ejemplos (unos 90 de 1500 cada una) y que, como casi toda la respuesta es una copia del diagrama, el aprendizaje de la parte que cambia queda diluido en 1000 iteraciones. Además, el **renombrar** mejoró pero sigue débil (7/12 y 9/12).

**Efecto de la cuantización.** Al importar el modelo a Ollama con cuantización a 4 bits se pierde un acierto (154 → 153), con diferencias pequeñas por operación (clase y varias clases bajan; renombrar sube). Se mide, no se oculta.

**Posible sobreajuste.** La pérdida de validación tuvo su mínimo en la iteración 600 (0,024) y después osciló entre 0,05 y 0,06: más iteraciones no mejoraron la validación. Un punto de control intermedio podría rendir igual o mejor.

## 6. Despliegue y uso en la plataforma

1. El adaptador se **fusiona** con el modelo (`mlx_lm fuse`) y se **importa a Ollama** como `uml-qwen-dia2` con cuantización a 4 bits (3,4 GB). La importación es determinista: repetirla produce la misma imagen.
2. En la configuración del servidor se define `AI_PROVIDER=ollama` y `OLLAMA_CHANGE_MODEL=uml-qwen-dia2`. Las preguntas y la revisión siguen con el modelo general (por ejemplo, Qwen 3.5 de 9 B); los **cambios al diagrama** los atiende el modelo reentrenado. El chat muestra «IA local (…; cambios: uml-qwen-dia2 reentrenado)».
3. La plataforma **no confía ciegamente en el modelo**: el guardia de cambios valida el tamaño, cuenta lo que se eliminaría y, si la respuesta deja fuera atributos o métodos de una clase existente, el navegador pide confirmación antes de aplicarla. Así, un fallo como el de «agregar método» (que no agrega nada) no destruye datos.

## 7. Segunda corrida

*(en curso: se vuelve a entrenar con más ejemplos de lo que falló; los resultados se agregan aquí al terminar)*

## 8. Evidencia de que se entrenó de verdad

| Evidencia | Dónde |
|---|---|
| Registro crudo del entrenamiento, con pérdida por iteración, fechas y datos del equipo | `ml/runs/dia2/train.log`, `loss.csv`, `equipo.txt` |
| Adaptador entrenado (88 117 092 bytes) con su hash SHA-256 `2a26ffd8…49477` | `ml/runs/dia2/adaptador.sha256` (el archivo pesa demasiado para el repositorio y no se versiona) |
| Datos y manifiesto (semilla, conteos, hashes, sin fugas entre entrenamiento y prueba) | `ml/runs/dia2/MANIFEST.json`, `ml/data/muestra_*.jsonl` |
| Resultados de cada modelo, con **cada respuesta cruda** | `ml/runs/dia2/eval-base.json`, `eval-reentrenado.json`, `eval-ollama.json` |
| Modelo desplegado en Ollama | `ml/runs/dia2/ollama-list.txt`, `ollama-modelfile.txt` |
| Todo repetible con un comando (semilla fija) | `ml/pipeline.sh <nombre> [iteraciones]` y `ml/README.md` |
| Pruebas automáticas del adaptador del proveedor (ids, parámetros de los métodos, errores) | `back_generador_bd/uml_api/tests/test_modelo_reentrenado.py` (17 pruebas) |

Se puede **mostrar un mini-entrenamiento en vivo** (100 iteraciones, unos 9 minutos) con `ml/train/entrenar.sh`.

## 9. Limitaciones

- Es un modelo pequeño entrenado con datos generados por plantillas: acierta mucho en lo que vio, y menos en operaciones poco frecuentes o con redacciones muy distintas.
- No supera a Gemini ni a un modelo grande en comprensión general; su ventaja es que corre sin internet, es ajustable y es barato.
- Solo se probó en un conjunto de 200 ejemplos generados; los 10 pedidos fijos de `scripts/evaluar_ia.py` se miden aparte (Anexo A).
- El servidor de AWS (2 GB de memoria) no puede ejecutarlo: se usa en el computador de quien presenta o en un servidor de IA con más memoria.
