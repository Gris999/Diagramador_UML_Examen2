# IA local con Ollama (Qwen)

El chat de la sala habla con la IA a través de la interfaz `AIProvider` (`back_generador_bd/uml_api/services/ai_provider.py`). Hoy hay dos proveedores:

| Proveedor | Variable `AI_PROVIDER` | Dónde corre | Internet |
|---|---|---|---|
| Gemini (por defecto) | `gemini` | Nube de Google | Sí |
| Ollama (modelo local, p. ej. Qwen) | `ollama` | Tu computador | No |

El chat muestra arriba cuál responde ("IA en la nube (Gemini)" o "IA local (modelo)"). Los tres modos (Preguntar, Pedir cambio, Revisar) funcionan con cualquiera de los dos: el proveedor local recibe **las mismas instrucciones** que Gemini (el prompt de cambios se extrajo a `build_change_prompt`, verificado idéntico al original).

> **Estado:** implementado, probado con pruebas automáticas y **evaluado con un modelo real (Qwen 3.5 de 9 B) el 2026-10-22**: 10 de 10 pedidos correctos, ver "Evaluación". También se probó el chat completo (Preguntar, Pedir cambio y Revisar) contra el modelo local a través de la API.

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

## En el servidor (AWS)

La instancia (2 vCPU, ~2 GB de RAM) **no** puede correr un modelo de 7 B. Para la demostración, lo razonable es mantener `AI_PROVIDER=gemini` en el servidor y mostrar la IA local en el computador de quien presenta, o instalar Ollama en otra máquina con GPU/más memoria y apuntar `OLLAMA_BASE_URL` allí.

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
