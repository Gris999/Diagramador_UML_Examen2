# IA local con Ollama (Qwen)

El chat de la sala habla con la IA a través de la interfaz `AIProvider` (`back_generador_bd/uml_api/services/ai_provider.py`). Hoy hay dos proveedores:

| Proveedor | Variable `AI_PROVIDER` | Dónde corre | Internet |
|---|---|---|---|
| Gemini (por defecto) | `gemini` | Nube de Google | Sí |
| Ollama (modelo local, p. ej. Qwen) | `ollama` | Tu computador | No |

El chat muestra arriba cuál responde ("IA en la nube (Gemini)" o "IA local (modelo)"). Los tres modos (Preguntar, Pedir cambio, Revisar) funcionan con cualquiera de los dos: el proveedor local recibe **las mismas instrucciones** que Gemini (el prompt de cambios se extrajo a `build_change_prompt`, verificado idéntico al original).

> **Estado:** el proveedor está implementado y probado con pruebas automáticas (respuestas simuladas). **Falta evaluarlo con un modelo real** (ver "Evaluación"); hasta entonces el requisito RF-33 figura como parcial en [`GAP_MATRIX.md`](GAP_MATRIX.md).

## Instalar (macOS)

```bash
brew install ollama
ollama serve            # déjalo corriendo en otra terminal
ollama pull qwen2.5:7b  # ≈ 4.7 GB; en un Mac de 16 GB va bien
```

Alternativas más ligeras si hay poca memoria: `qwen2.5:3b` (≈ 1.9 GB) o `qwen2.5:1.5b`. Los modelos pequeños fallan más al devolver el JSON de cambios; cuando fallan, el chat muestra el error de siempre y **el diagrama no se toca**.

## Activarlo

En `back_generador_bd/.env` (archivo local, no versionado):

```
AI_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

`host.docker.internal` es la dirección con la que el contenedor de Django alcanza el Ollama que corre en el Mac (Docker Desktop). Si Django corre fuera de Docker, usa `http://localhost:11434`. Reinicia Django (`docker restart django_backend_UML`).

Para volver a Gemini basta con `AI_PROVIDER=gemini` (o quitar la línea).

## En el servidor (AWS)

La instancia (2 vCPU, ~2 GB de RAM) **no** puede correr un modelo de 7 B. Para la demostración, lo razonable es mantener `AI_PROVIDER=gemini` en el servidor y mostrar la IA local en el computador de quien presenta, o instalar Ollama en otra máquina con GPU/más memoria y apuntar `OLLAMA_BASE_URL` allí.

## Evaluación (pendiente)

Para dejar evidencia se propone una tabla de 10 pedidos fijos (crear clase con atributos, agregar relación, editar un atributo, eliminar una clase, revisar un diagrama, etc.) ejecutados contra Gemini y contra el modelo local, registrando: ¿devolvió JSON válido?, ¿el resultado es el pedido?, tiempo de respuesta. Esa tabla se agrega aquí cuando se corra.

## Seguridad

- Las excepciones del proveedor nunca incluyen la URL con la clave de Gemini; el proveedor local no usa claves.
- `GET /api/ia/provider/` solo devuelve el nombre del proveedor y el modelo, sin ningún dato sensible.
