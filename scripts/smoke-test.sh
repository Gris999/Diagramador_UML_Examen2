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
check "API informa si hace falta iniciar sesión" 200 "$(code "https://$DOMAIN/api/auth/config/")"

# Con el servidor en modo «entrar con el correo» (AUTH_REQUIRED) la API pide sesión: sin ella contesta 401 en vez de 200/403.
if curl -s -m 15 "https://$DOMAIN/api/auth/config/" | grep -Eq '"authRequired": *true'; then
  ACTIVIDAD=401; PROVEEDOR=401; CHAT=401
  printf 'INFO  el servidor pide iniciar sesión (AUTH_REQUIRED): la API sin sesión debe dar 401\n'
else
  ACTIVIDAD=200; PROVEEDOR=200; CHAT=403
fi
check "API de actividad responde"              $ACTIVIDAD "$(code "https://$DOMAIN/api/rooms/prueba-humo/activity/")"
check "API informa el proveedor de IA"         $PROVEEDOR "$(code "https://$DOMAIN/api/ia/provider/")"
check "Chat de IA exige participante"          $CHAT "$(code -X POST "https://$DOMAIN/api/rooms/prueba-humo/ia/chat/" -H 'Content-Type: application/json' --data '{"mode":"ask","message":"hola"}')"

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

IP=$(dig +short +time=3 +tries=1 "$DOMAIN" | tail -1)
if [ -n "$IP" ]; then
  for PORT in 4200 7001 8000; do
    # curl con plazo corto (nc se quedaba esperando en algunas redes): sale con error si el puerto está cerrado o filtrado
    if curl -s -o /dev/null --connect-timeout 4 -m 5 "http://$IP:$PORT/" >/dev/null 2>&1; then OPEN=abierto; else OPEN=cerrado; fi
    check "Puerto interno $PORT cerrado al exterior" cerrado "$OPEN"
  done
fi

echo
if [ "$FAILS" -eq 0 ]; then echo "Todo en orden."; else echo "$FAILS comprobación(es) fallaron."; fi
exit $([ "$FAILS" -eq 0 ] && echo 0 || echo 1)
