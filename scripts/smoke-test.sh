#!/usr/bin/env bash
# Prueba de humo del despliegue (RNF-07). Solo lectura: no modifica nada.
#
# Uso:  scripts/smoke-test.sh [dominio]        (por defecto diagramador.dev)
# Sale con código 0 si todo está bien y 1 si algo falla.
set -u

DOMAIN="${1:-diagramador.dev}"
FAILS=0

check() { # descripción, esperado, obtenido
  if [ "$2" = "$3" ]; then
    printf 'OK    %s\n' "$1"
  else
    printf 'FALLA %s (esperado %s, obtenido %s)\n' "$1" "$2" "$3"
    FAILS=$((FAILS + 1))
  fi
}

code() { curl -s -o /dev/null -m 15 -w '%{http_code}' "$@" || true; }

check "HTTPS responde"                         200 "$(code "https://$DOMAIN/")"
check "HTTP redirige a HTTPS"                  301 "$(code "http://$DOMAIN/")"
check "Vista móvil de seguimiento (ruta SPA)"  200 "$(code "https://$DOMAIN/sala/prueba-humo/seguir")"
check "API de actividad responde"              200 "$(code "https://$DOMAIN/api/rooms/prueba-humo/activity/")"
check "API informa el proveedor de IA"         200 "$(code "https://$DOMAIN/api/ia/provider/")"
check "Chat de IA exige participante"          403 "$(code -X POST "https://$DOMAIN/api/rooms/prueba-humo/ia/chat/" -H 'Content-Type: application/json' --data '{"mode":"ask","message":"hola"}')"

WS=$(curl -s -m 8 -o /dev/null -w '%{http_code}' \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  "https://$DOMAIN/ws/canvas/prueba-humo/" || true)
# curl corta la conexión de WebSocket por tiempo (código 28 → "000"), lo que importa es el 101 inicial
check "WebSocket negocia (101)"                101 "$WS"

ZIP=$(mktemp)
GEN=$(curl -s -m 60 -X POST "https://$DOMAIN/generate" -H 'Content-Type: application/json' \
  --data '{"classes":[{"id":"c1","name":"Persona","attributes":[{"name":"id","type":"int"}],"methods":[]}],"relationships":[]}' \
  -o "$ZIP" -w '%{http_code}' || true)
check "Generador Spring devuelve un ZIP"       200 "$GEN"
if [ "$GEN" = "200" ]; then
  KIND=$(file -b "$ZIP" | cut -c1-3)
  check "El archivo generado es un ZIP"        Zip "$KIND"
fi
rm -f "$ZIP"

IP=$(dig +short "$DOMAIN" | tail -1)
if [ -n "$IP" ] && command -v nc >/dev/null 2>&1; then
  for PORT in 4200 7001 8000; do
    if nc -z -w 4 "$IP" "$PORT" >/dev/null 2>&1; then OPEN=abierto; else OPEN=cerrado; fi
    check "Puerto interno $PORT cerrado al exterior" cerrado "$OPEN"
  done
fi

echo
if [ "$FAILS" -eq 0 ]; then echo "Todo en orden."; else echo "$FAILS comprobación(es) fallaron."; fi
exit $([ "$FAILS" -eq 0 ] && echo 0 || echo 1)
