# Reentrenamiento del modelo de IA (LoRA)

Reproduce la prueba de viabilidad del 2026-10-22. Diseño y resultados: [`docs/PLAN_REENTRENAMIENTO_IA.md`](../docs/PLAN_REENTRENAMIENTO_IA.md).

Requisitos: Mac con Apple Silicon (probado en M5, 16 GB), Python 3.12, [Ollama](https://ollama.com) y el modelo base `Qwen3-4B-Instruct-2507` en 4 bits (formato MLX, p. ej. el de LM Studio).

```bash
# 1. Entorno aislado (una vez)
python3 -m venv ml/.venv && ml/.venv/bin/pip install mlx-lm

# 2. Datos (semilla fija: siempre salen los mismos)
ml/.venv/bin/python ml/data/generar_dataset.py --salida ml/data/out --train 240 --valid 36 --test 60 --semilla 42

# 3. Medir el modelo base sin entrenar
BASE=~/.lmstudio/models/lmstudio-community/Qwen3-4B-Instruct-2507-MLX-4bit
ml/.venv/bin/python ml/eval/evaluar.py --modelo $BASE --salida ml/runs/spike/eval-base.json --nombre base

# 4. Entrenar (deja log crudo, loss.csv, hash del adaptador y datos del equipo)
ml/train/entrenar.sh $BASE ml/runs/spike 100

# 5. Medir el reentrenado
ml/.venv/bin/python ml/eval/evaluar.py --modelo $BASE --adaptador ml/runs/spike/adapters \
    --salida ml/runs/spike/eval-reentrenado.json --nombre reentrenado

# 6. Desplegar en Ollama y medir lo desplegado
ml/.venv/bin/python -m mlx_lm fuse --model $BASE --adapter-path ml/runs/spike/adapters --save-path ml/models/fused-spike --dequantize
ollama create uml-qwen-spike -f ml/export/Modelfile.spike --quantize int4   # la ruta FROM es relativa al Modelfile
ml/.venv/bin/python ml/eval/evaluar_ollama.py --modelo uml-qwen-spike --salida ml/runs/spike/eval-ollama.json
```

`ml/runs/spike/` conserva la evidencia de la corrida: `train.log` (crudo), `loss.csv`, `equipo.txt`, `config.yaml`, `MANIFEST.json` (datos), `adaptador.sha256`, `eval-*.json` (cada respuesta cruda) y `ollama-*.txt`. El adaptador y los modelos fusionados pesan demasiado y no se versionan.
