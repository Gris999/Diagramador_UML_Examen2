#!/usr/bin/env bash
# Corrida completa y repetible: medir el base, entrenar, medir el reentrenado,
# fusionar, importar a Ollama y medir lo desplegado. Deja todo en ml/runs/<nombre>/.
#
# Uso: ml/pipeline.sh <nombre-de-la-corrida> [iteraciones]
# Variable opcional: BASE=<ruta del modelo base en formato MLX>
set -euo pipefail
NOMBRE="$1"; ITERS="${2:-}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ"
BASE="${BASE:-$HOME/.lmstudio/models/lmstudio-community/Qwen3-4B-Instruct-2507-MLX-4bit}"
CORRIDA="ml/runs/$NOMBRE"
PY=ml/.venv/bin/python
mkdir -p "$CORRIDA"
paso() { echo; echo "=== [$(date +%H:%M:%S)] $* ==="; }

paso "1/6 Medir el modelo base sin entrenar"
$PY ml/eval/evaluar.py --modelo "$BASE" --salida "$CORRIDA/eval-base.json" --nombre "base (sin entrenar)" | tee "$CORRIDA/eval-base.log"

paso "2/6 Entrenar (LoRA)"
ml/train/entrenar.sh "$BASE" "$CORRIDA" $ITERS

paso "3/6 Medir el modelo reentrenado"
$PY ml/eval/evaluar.py --modelo "$BASE" --adaptador "$CORRIDA/adapters" --salida "$CORRIDA/eval-reentrenado.json" --nombre "reentrenado ($NOMBRE)" | tee "$CORRIDA/eval-reentrenado.log"

paso "4/6 Fusionar el adaptador con el modelo base"
$PY -m mlx_lm fuse --model "$BASE" --adapter-path "$CORRIDA/adapters" --save-path "ml/models/fused-$NOMBRE" --dequantize

paso "5/6 Importar a Ollama como uml-qwen-$NOMBRE"
printf 'FROM ../../models/fused-%s\nPARAMETER temperature 0\nPARAMETER num_ctx 4096\n' "$NOMBRE" > "$CORRIDA/Modelfile"
ollama create "uml-qwen-$NOMBRE" -f "$CORRIDA/Modelfile" --quantize int4 2>&1 | tr '\r' '\n' | grep -E "success|rror" | tee "$CORRIDA/ollama-create.log"
ollama list > "$CORRIDA/ollama-list.txt"
ollama show "uml-qwen-$NOMBRE" --modelfile > "$CORRIDA/ollama-modelfile.txt"

paso "6/6 Medir el modelo desplegado en Ollama"
$PY ml/eval/evaluar_ollama.py --modelo "uml-qwen-$NOMBRE" --salida "$CORRIDA/eval-ollama.json" | tee "$CORRIDA/eval-ollama.log"

paso "Listo"
