#!/usr/bin/env bash
# Modelo local que atiende varios pedidos a la vez (Qwen3-4B con MLX), listo para la aplicación.
#
#   ml/serve/iniciar.sh start    levanta los dos servidores mlx_lm y la puerta con clave (puerto 8090)
#   ml/serve/iniciar.sh tunel    abre un túnel ngrok hacia la puerta y muestra la dirección pública (para el sitio desplegado)
#   ml/serve/iniciar.sh status   dice qué está corriendo y muestra la clave y la dirección
#   ml/serve/iniciar.sh stop     lo apaga todo (también el túnel)
#
# Detalle y motivos en docs/IA_LOCAL.md ("Varios pedidos a la vez").
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$AQUI/../.." && pwd)"
RUN="$AQUI/.run"
PY="${ML_PYTHON:-$RAIZ/ml/.venv/bin/python}"
BASE="${ML_BASE_MODEL:-$HOME/.lmstudio/models/lmstudio-community/Qwen3-4B-Instruct-2507-MLX-4bit}"
ADAPTADOR="${ML_ADAPTER:-$RAIZ/ml/runs/dia3/adapters}"
PUERTO_CAMBIOS=8081
PUERTO_CHAT=8082
PUERTO_PUERTA="${LOCAL_AI_GATEWAY_PORT:-8090}"
SIMULTANEOS="${ML_CONCURRENCY:-4}"
mkdir -p "$RUN"

clave() {
  if [[ -n "${LOCAL_AI_TOKEN:-}" ]]; then printf '%s' "$LOCAL_AI_TOKEN"; return; fi
  if [[ ! -s "$RUN/clave" ]]; then
    umask 077
    LC_ALL=C tr -dc 'a-f0-9' < /dev/urandom | head -c 32 > "$RUN/clave"
  fi
  cat "$RUN/clave"
}

vivo() { [[ -s "$RUN/$1.pid" ]] && kill -0 "$(cat "$RUN/$1.pid")" 2>/dev/null; }

arrancar() { # nombre, comando...
  local nombre="$1"; shift
  if vivo "$nombre"; then echo "  $nombre ya estaba corriendo"; return; fi
  nohup "$@" > "$RUN/$nombre.log" 2>&1 &
  echo $! > "$RUN/$nombre.pid"
  echo "  $nombre arrancó (pid $(cat "$RUN/$nombre.pid"))"
}

esperar() { # url, nombre, cabecera opcional
  for _ in $(seq 1 90); do
    if curl -fs -m 2 ${3:+-H "$3"} "$1" > /dev/null 2>&1; then return 0; fi
    sleep 1
  done
  echo "  ✗ $2 no respondió; mira $RUN/*.log" >&2
  return 1
}

# La primera vez que el motor mezcla varios pedidos en una sola pasada tarda unos segundos de más: se hace aquí, con pedidos de mentira,
# para que la primera vez que lo haga de verdad (en la demostración) ya esté caliente.
calentar() { # puerto
  local pids=()
  for i in 1 2 3 4; do
    curl -s -m 90 "http://127.0.0.1:$1/v1/chat/completions" -H 'Content-Type: application/json' \
      -d "{\"model\":\"default_model\",\"messages\":[{\"role\":\"user\",\"content\":\"Explica en una frase para qué sirve la clase número $i en un diagrama UML.\"}],\"max_tokens\":40}" > /dev/null &
    pids+=($!)
  done
  wait "${pids[@]}" || true  # solo estos pedidos: un `wait` a secas esperaría también a los servidores que este script dejó corriendo
}

case "${1:-status}" in
  start)
    [[ -x "$PY" ]] || { echo "Falta el entorno de ml/ ($PY). Ver ml/README.md." >&2; exit 1; }
    [[ -d "$BASE" ]] || { echo "Falta el modelo base: $BASE (variable ML_BASE_MODEL)." >&2; exit 1; }
    [[ -d "$ADAPTADOR" ]] || { echo "Falta el adaptador: $ADAPTADOR (variable ML_ADAPTER)." >&2; exit 1; }
    echo "Levantando el modelo local…"
    arrancar cambios "$PY" -m mlx_lm server --model "$BASE" --adapter-path "$ADAPTADOR" --host 127.0.0.1 --port "$PUERTO_CAMBIOS" \
      --decode-concurrency "$SIMULTANEOS" --prompt-concurrency "$SIMULTANEOS" --max-tokens 700
    arrancar chat "$PY" -m mlx_lm server --model "$BASE" --host 127.0.0.1 --port "$PUERTO_CHAT" \
      --decode-concurrency "$SIMULTANEOS" --prompt-concurrency "$SIMULTANEOS" --max-tokens 800
    esperar "http://127.0.0.1:$PUERTO_CAMBIOS/v1/models" "el servidor de cambios"
    esperar "http://127.0.0.1:$PUERTO_CHAT/v1/models" "el servidor de chat"
    LOCAL_AI_TOKEN="$(clave)" arrancar puerta python3 "$AQUI/gateway.py" --port "$PUERTO_PUERTA" \
      --chat-url "http://127.0.0.1:$PUERTO_CHAT" --change-url "http://127.0.0.1:$PUERTO_CAMBIOS"
    esperar "http://127.0.0.1:$PUERTO_PUERTA/v1/models" "la puerta" "Authorization: Bearer $(clave)"
    echo "  calentando los modelos (cuatro pedidos juntos a cada uno)…"
    calentar "$PUERTO_CAMBIOS"; calentar "$PUERTO_CHAT"
    echo "Listo: http://127.0.0.1:$PUERTO_PUERTA  (clave en $RUN/clave)"
    echo "Para probarlo en tu computador: LOCAL_ENGINE=mlx LOCAL_AI_URL=http://127.0.0.1:$PUERTO_PUERTA LOCAL_AI_TOKEN=\$(cat $RUN/clave)"
    ;;
  tunel)
    command -v ngrok > /dev/null || { echo "Falta ngrok (brew install ngrok y ngrok config add-authtoken …)." >&2; exit 1; }
    vivo puerta || { echo "Primero: $0 start" >&2; exit 1; }
    arrancar tunel ngrok http "$PUERTO_PUERTA" --log=stdout
    URL=""
    for _ in $(seq 1 20); do
      URL="$(curl -s -m 2 http://127.0.0.1:4040/api/tunnels | python3 -c 'import json,sys
try:
    print(next(t["public_url"] for t in json.load(sys.stdin)["tunnels"] if t["public_url"].startswith("https")))
except Exception:
    pass' 2>/dev/null || true)"
      [[ -n "$URL" ]] && break
      sleep 1
    done
    [[ -n "$URL" ]] || { echo "  ✗ ngrok no dio una dirección; mira $RUN/tunel.log" >&2; exit 1; }
    echo "$URL" > "$RUN/tunel.url"
    echo "Túnel abierto: $URL"
    echo "Variables para el servidor desplegado:  LOCAL_ENGINE=mlx  LOCAL_AI_URL=$URL  LOCAL_AI_TOKEN=(la de $RUN/clave)"
    ;;
  stop)
    for nombre in tunel puerta chat cambios; do
      if vivo "$nombre"; then kill "$(cat "$RUN/$nombre.pid")" 2>/dev/null && echo "  $nombre apagado"; fi
      rm -f "$RUN/$nombre.pid"
    done
    rm -f "$RUN/tunel.url"
    ;;
  status)
    for nombre in cambios chat puerta tunel; do
      if vivo "$nombre"; then echo "  $nombre: corriendo (pid $(cat "$RUN/$nombre.pid"))"; else echo "  $nombre: apagado"; fi
    done
    [[ -s "$RUN/tunel.url" ]] && echo "  dirección pública: $(cat "$RUN/tunel.url")"
    [[ -s "$RUN/clave" ]] && echo "  clave: $RUN/clave"
    ;;
  *) echo "Uso: $0 start | tunel | status | stop" >&2; exit 1 ;;
esac
