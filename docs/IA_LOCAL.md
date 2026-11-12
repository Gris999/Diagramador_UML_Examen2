# IA local con Ollama (Qwen)

El chat de la sala habla con la IA a través de la interfaz `AIProvider` (`back_generador_bd/uml_api/services/ai_provider.py`). Hoy hay dos proveedores:

| Proveedor | Variable `AI_PROVIDER` | Dónde corre | Internet |
|---|---|---|---|
| Gemini (por defecto) | `gemini` | Nube de Google | Sí |
| Ollama (modelo local, p. ej. Qwen) | `ollama` | Tu computador | No |

El chat muestra arriba cuál responde ("IA en la nube (Gemini)" o "IA local (modelo)") y **permite elegirlo desde el propio chat**: dos botones, **Nube (Gemini)** y **Local (modelo)**, cambian el modelo de **toda la sala** (uno solo para todos) y el cambio queda en la actividad. «Local» solo se puede elegir si el servidor alcanza a Ollama (`OLLAMA_BASE_URL`); en el servidor de AWS no hay modelo local y el botón aparece apagado. Sin elegir nada, la sala usa el proveedor del servidor (`AI_PROVIDER`). El chat único (preguntar, pedir un cambio con permiso, revisar, historial) funciona con cualquiera de los dos: el proveedor local recibe **las mismas instrucciones** que Gemini (el prompt de cambios se extrajo a `build_change_prompt`, verificado idéntico al original).

> **Estado:** implementado, probado con pruebas automáticas y **evaluado con un modelo real (Qwen 3.5 de 9 B) el 2026-10-22**: 10 de 10 pedidos correctos, ver "Evaluación". También se probó el chat completo contra el modelo local a través de la API y, el 2026-11-08, el chat único en el navegador con Qwen 3.5 de 9 B: «agrega una clase Cliente con nombre y correo» produjo la propuesta con permiso y, al pulsar Aplicar, la clase apareció en el diagrama.

## Instalar (macOS)

```bash
brew install ollama
ollama serve            # déjalo corriendo en otra terminal
ollama pull qwen3.5:9b  # ≈ 7.6 GB en disco; en un Mac de 16 GB va bien
```

Alternativas más ligeras si hay poca memoria: `qwen3.5:4b` o `qwen3.5:2b` (no evaluados). Los modelos pequeños fallan más al devolver el JSON de cambios; cuando fallan, el chat muestra el error de siempre y **el diagrama no se toca**.

## Activarlo

En `back_generador_bd/.env` (archivo local, no versionado):

```
AI_PROVIDER=ollama
OLLAMA_MODEL=qwen3.5:9b
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

`host.docker.internal` es la dirección con la que el contenedor de Django alcanza el Ollama que corre en el Mac (Docker Desktop). Si Django corre fuera de Docker, usa `http://localhost:11434`. Reinicia Django (`docker restart django_backend_UML`).

Para volver a Gemini basta con `AI_PROVIDER=gemini` (o quitar la línea).

## Modelo reentrenado (opcional)

Para los **cambios al diagrama** se puede usar un modelo que el equipo reentrenó (Qwen3-4B con LoRA; ver el Anexo B y `docs/REENTRENAMIENTO_IA.md`). En `back_generador_bd/.env`:

```
AI_PROVIDER=ollama
OLLAMA_MODEL=qwen3.5:9b
OLLAMA_CHANGE_MODEL=uml-qwen-dia3
```

Las preguntas y la revisión siguen con el modelo general (`OLLAMA_MODEL`); los cambios los atiende el reentrenado, que usa un prompt corto con ids cortos y es más rápido (≈ 2 s por cambio). En los 10 pedidos fijos acierta 8 de 10 (los otros proveedores, 10 de 10) y en 200 ejemplos reservados acierta el 82 %, contra el 35 % del modelo sin entrenar. Si falla, el chat muestra el error de siempre y el diagrama no cambia; la plataforma además pide confirmación cuando una respuesta dejaría fuera atributos o métodos existentes.

## Varios pedidos a la vez (motor `mlx`)

**Problema medido (2026-11-11, Mac M5 de 16 GB, Ollama 0.40.8):** con el motor MLX de Ollama, cuatro pedidos a la vez salen uno tras otro (2,1 / 4,1 / 6,1 / 8,1 s) **aunque se suba `OLLAMA_NUM_PARALLEL=4`**: ese motor no mezcla pedidos (es un problema conocido de Ollama con MLX). Por eso el modelo local tiene un segundo motor, `LOCAL_ENGINE=mlx`, que usa `mlx_lm.server` con `--decode-concurrency`: mezcla los pedidos en una sola pasada del modelo. Tres cambios al diagrama a la vez, desde el servidor completo (Django + Redis), contestan todos a los 5,6 s (en fila serían unos 9 s); cuatro pedidos mezclados (cambios y preguntas), entre 6 y 8,7 s.

Qué hay en `ml/serve/`:

| Archivo | Para qué |
|---|---|
| `iniciar.sh` | `start` levanta todo (dos servidores `mlx_lm` y la puerta) y los calienta; `tunel` abre un túnel `ngrok`; `status`; `stop` |
| `gateway.py` | La **puerta**: una sola dirección (puerto 8090) y una clave (`Authorization: Bearer …`) delante de los dos servidores. Deja pasar solo `POST /v1/chat/completions` y `GET /v1/models` (nada de bajar o borrar modelos), limita el tamaño del pedido y de la respuesta y no acepta respuestas en flujo. Solo usa la biblioteca estándar |
| `test_gateway.py` | Pruebas de la puerta: `python3 -m unittest discover -s ml/serve -v` |

Los dos servidores cargan el mismo Qwen3-4B (4 bits): `cambios` **con el adaptador que reentrenó el equipo** (los cambios al diagrama) y `chat` sin adaptador (preguntas y revisiones). Los dos juntos ocupan unos 5 GB. Sin ayuda, la calidad de los cambios era la del modelo reentrenado en Ollama (7 de 9 pedidos de cambios de `scripts/evaluar_ia.py`). Probándolo en pantalla con tres navegadores (2026-11-12) aparecieron cuatro fallos del modelo pequeño que el servidor ahora corrige al restaurar el cambio (`modelo_reentrenado.restaurar` con la instrucción a la vista): una clase nueva que llega con el id de otra («agrega una clase Pedido» renombraba y vaciaba a Cliente), dos clases nuevas con el mismo id, «agrega el atributo telefono» escrito como método, y una herencia con la flecha al revés («Empleado hereda de Persona»); y la pantalla cambió los ids nuevos que parecen los internos de JointJS (`c2`), que impedían dibujar la clase. Con eso, `scripts/evaluar_ia.py mlx` acierta **10 de 10**. Las preguntas y la revisión las contesta el 4B general, que es más pequeño que el 9B del motor Ollama.

Activarlo en el computador de quien presenta (`back_generador_bd/.env`):

```
AI_PROVIDER=ollama          # o elegir «Local» en el chat de la sala
LOCAL_ENGINE=mlx
LOCAL_AI_URL=http://127.0.0.1:8090
LOCAL_AI_TOKEN=<el contenido de ml/serve/.run/clave>
```

```bash
ml/serve/iniciar.sh start
```

**Cuántas personas atiende a la vez la IA de una sala (RF-48):** los cupos dependen del modelo elegido: nube (Gemini) 4, local con `mlx` 4, local con Ollama 1 (porque su motor contesta de uno en uno). Se ajustan con `AI_CONCURRENCY_GEMINI` y `AI_CONCURRENCY_LOCAL`. Cada persona atiende de a un pedido; si todos los cupos están ocupados, los demás pedidos esperan en fila y se atienden en orden de llegada.

## En el servidor (AWS)

La instancia (2 vCPU, ~2 GB de RAM) **no** puede correr el modelo local: ni con Ollama (7 B) ni con el 4B de `mlx` junto a Postgres, Mongo, Redis y Django. Mantiene `AI_PROVIDER=gemini` y el botón «Local» del chat aparece apagado. Para que el **sitio desplegado** use el modelo del computador de quien presenta, sin pagar nada, se abre un túnel hacia la puerta:

1. En el computador: `ml/serve/iniciar.sh start` y después `ml/serve/iniciar.sh tunel` (usa `ngrok`, que ya tiene cuenta gratis); muestra una dirección `https://….ngrok-free.app`.
2. En el servidor, en `back_generador_bd/.env`: `LOCAL_ENGINE=mlx`, `LOCAL_AI_URL=<la dirección>` y `LOCAL_AI_TOKEN=<la clave de ml/serve/.run/clave>`; se recrea el contenedor de Django (`docker-compose -f docker-compose.app.yml up -d --force-recreate django`, un `restart` no vuelve a leer el `.env`).
3. En la sala, el botón **Local** se enciende y el modelo de toda la sala pasa a ser el del computador. La IA sigue con Gemini por defecto.

La clave es lo que protege el túnel (la dirección es pública; con el dominio estático gratis de la cuenta de ngrok, `….ngrok-free.dev`, es la **misma** cada vez que se reinicia el túnel —verificado el 2026-11-11—, así que el servidor no hay que tocarlo; si algún día cambiara, se actualiza `LOCAL_AI_URL` en el `.env` del servidor y se recrea `django`): sin la clave la puerta responde 401, y aun con ella solo deja generar texto. **Se cierra al terminar** (`ml/serve/iniciar.sh stop`). Si el túnel o el computador se apagan, «Local» vuelve a verse apagado en unos 10 segundos y la sala puede volver a **Nube (Gemini)**.

## Evaluación (2026-10-22)

`scripts/evaluar_ia.py` ejecuta **10 pedidos fijos** contra un proveedor, tal como los usa el chat, y comprueba de forma automática que la respuesta sea un JSON utilizable **y** que haga exactamente lo pedido: la clase, el atributo, el tipo o los extremos de la relación correctos, que no se pierda lo que ya existía y que la cantidad de eliminaciones sea la esperada (la misma cuenta que usa el chat para pedir confirmación). Se corre así (desde la raíz del repositorio):

```bash
DJANGO_SECRET_KEY=x POSTGRES_PASSWORD=x back_generador_bd/.venv/bin/python scripts/evaluar_ia.py gemini
DJANGO_SECRET_KEY=x POSTGRES_PASSWORD=x back_generador_bd/.venv/bin/python scripts/evaluar_ia.py ollama qwen3.5:9b http://localhost:11434
DJANGO_SECRET_KEY=x POSTGRES_PASSWORD=x back_generador_bd/.venv/bin/python scripts/evaluar_ia.py --verificadores   # sin proveedor
```

La opción `--verificadores` (y una prueba automática de Django) comprueba que las verificaciones aceptan una respuesta buena y **rechazan** respuestas casi buenas: clase o atributo equivocado, tipo equivocado, relación con la dirección invertida o con otros extremos, atributos que se perderían al reemplazar la clase, eliminar de más o de menos. Una primera versión del script solo buscaba palabras en el JSON; la revisión independiente señaló que eso podía dar por buena una respuesta equivocada, por eso se endureció y se volvió a medir.

Los 10 pedidos: crear una clase con atributos, crear dos clases con una relación, agregar un atributo, agregar un método, cambiar el tipo de un atributo, eliminar un atributo, eliminar una clase, herencia, un dominio completo desde texto (biblioteca) y la revisión de un diagrama con defectos (debe señalar la clase aislada y sin atributos y proponer cómo arreglarla).

| # | Pedido | Gemini (nube) | | Qwen 3.5 9B (local) | |
|---|---|---|---|---|---|
| | | correcto | segundos | correcto | segundos |
| 1 | crear clase con atributos | sí | 5.4 | sí | 11.6 |
| 2 | crear dos clases y una relación | sí | 9.2 | sí | 15.2 |
| 3 | agregar atributo | sí | 9.6 | sí | 7.4 |
| 4 | agregar método | sí | 9.2 | sí | 5.0 |
| 5 | editar tipo de atributo | sí | 10.0 | sí | 13.5 |
| 6 | eliminar atributo | sí | 9.1 | sí | 6.1 |
| 7 | eliminar clase | sí | 16.8 | sí | 4.9 |
| 8 | herencia | sí | 44.6 | sí | 5.9 |
| 9 | dominio desde texto | sí | 36.6 | sí | 24.7 |
| 10 | revisión con defectos | sí | 41.6 | sí | 21.9 |
| | **Resultado** | **10/10** | **19,2 s de promedio** | **10/10** | **11,6 s de promedio** |

**Conclusión:** con las verificaciones estrictas, el modelo local y Gemini aciertan los mismos 10 pedidos (JSON válido y resultado correcto). Los tiempos **varían mucho entre corridas**: en una primera medición, con verificaciones más laxas, Gemini promedió 9,2 s y el modelo local 21,9 s; en esta, 19,2 s y 11,6 s (Gemini tuvo varias respuestas lentas y las dos evaluaciones corrieron a la vez). No hay base para afirmar que uno sea más rápido que el otro; el modelo local ocupa unos 8 GB de memoria mientras responde. Son 10 pedidos, no un estudio estadístico: sirven para demostrar que la alternativa local funciona, no para afirmar que iguala a Gemini en todo. Medido en un Mac de 16 GB con Ollama 0.40.

**Detalles que se aprendieron al probarlo:**

- Qwen 3.5 es un modelo con razonamiento: el proveedor envía `think: false` para que responda directo (si no, el tiempo se multiplica).
- Ollama responde "structured output is unavailable" con Qwen 3.5 si se pide `format: "json"`. Por eso no se pide: el prompt exige JSON y el servidor tolera el cerco de Markdown (` ```json `).
- La primera respuesta tras arrancar Ollama es más lenta porque carga el modelo en memoria.

## Seguridad

- Las excepciones del proveedor nunca incluyen la URL con la clave de Gemini; el proveedor local no usa claves.
- `GET /api/ia/provider/` solo devuelve el nombre del proveedor y el modelo, sin ningún dato sensible.
- Con el modelo local, los pedidos y el diagrama **no salen del computador** (no van a internet).

## Arranque local verificado para el parcial (2026-11-10)

La IA local se usa desde **http://localhost:4200**, no desde el sitio de AWS.
El 2026-11-10 se comprobó en el navegador: el selector mostraba
«Local (qwen3.5:9b)» y «Uma, agrega una clase Producto con nombre y precio»
produjo una propuesta real y su holograma, antes de pulsar Aplicar. No se
instaló ni descargó otro modelo.

Después de reiniciar la Mac, los procesos deben volver a iniciarse. Si los
puertos están libres, usar las dependencias ya instaladas:

```bash
# Terminal 1: infraestructura existente (sin borrar volúmenes)
docker desktop start
docker start postgres_db redis_server
ollama serve

# Terminal 2: desde la raíz del repositorio, API nativa contra Docker local
cd back_generador_bd
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5433 \
REDIS_HOST=127.0.0.1 REDIS_PORT=6379 \
AI_PROVIDER=ollama OLLAMA_BASE_URL=http://127.0.0.1:11434 \
OLLAMA_MODEL=qwen3.5:9b \
.venv/bin/daphne -b 127.0.0.1 -p 8000 diagramador_uml.asgi:application

# Terminal 3: desde la raíz del repositorio, interfaz local
cd front_generador_bd
npx ng serve --host 127.0.0.1 --port 4200
```

El servidor Ollama debe usar el modelo instalado; no ejecutar `ollama pull`
antes de la exposición. La primera petición puede tardar más al cargarlo.
En esta preparación se aplicaron únicamente las migraciones locales
`collab.0006` y `collab.0007`, después de respaldar la base existente; no se
modificó la configuración de producción ni el archivo `.env` local.
Esta preparación arranca el editor y su IA; el generador Spring no se inició
como parte de ella. Para demostrar las exportaciones completas se puede usar
el sitio publicado, donde la comprobación de salud del generador pasó.
