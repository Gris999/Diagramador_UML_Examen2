#!/usr/bin/env bash
# Uso: ml/train/entrenar.sh <ruta-del-modelo-base> <carpeta-de-la-corrida> [iteraciones]
# Entrena un adaptador LoRA y deja en la carpeta: train.log (crudo), loss.csv,
# equipo.txt, adaptador con su hash y la configuración usada.
set -euo pipefail
MODELO="$1"; CORRIDA="$2"; ITERS="${3:-}"
RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
DATOS="${DATOS:-ml/data/out}"
cd "$RAIZ"
mkdir -p "$CORRIDA"

{
  echo "fecha: $(date -Iseconds)"
  echo "equipo: $(sysctl -n machdep.cpu.brand_string), $(( $(sysctl -n hw.memsize) / 1073741824 )) GB"
  echo "sistema: $(sw_vers -productName) $(sw_vers -productVersion)"
  echo "modelo_base: $MODELO"
  echo "mlx_lm: $(ml/.venv/bin/python -c 'import mlx_lm; print(mlx_lm.__version__)')"
  echo "commit: $(git rev-parse --short HEAD)"
  echo "datos_sha256: $(shasum -a 256 "$DATOS/train.jsonl" | cut -d' ' -f1)"
} > "$CORRIDA/equipo.txt"
cp ml/train/config.yaml "$CORRIDA/config.yaml"
cp "$DATOS/MANIFEST.json" "$CORRIDA/MANIFEST.json"

EXTRA=()
if [ -n "$ITERS" ]; then EXTRA+=(--iters "$ITERS"); fi

ml/.venv/bin/python -m mlx_lm lora -c ml/train/config.yaml --model "$MODELO" --data "$DATOS" \
  --adapter-path "$CORRIDA/adapters" "${EXTRA[@]}" 2>&1 | tee "$CORRIDA/train.log"

ml/.venv/bin/python ml/train/extraer_perdida.py "$CORRIDA/train.log" "$CORRIDA/loss.csv"
shasum -a 256 "$CORRIDA"/adapters/*.safetensors | tee "$CORRIDA/adaptador.sha256"
ls -l "$CORRIDA"/adapters/ | tee -a "$CORRIDA/adaptador.sha256"
