#!/usr/bin/env bash
# Pone la clave del servicio de correo (Resend) en el .env del servidor de AWS y reinicia Django.
# La clave se escribe sin que se vea, viaja por SSH y queda solo en el servidor: no se guarda en git ni en el historial de la terminal.
#
# Uso:  scripts/poner-clave-correo.sh
# Variables opcionales: LLAVE (ruta del .pem), SERVIDOR (usuario@ip).
set -euo pipefail

LLAVE="${LLAVE:-$HOME/Downloads/software1-case-key.pem}"
SERVIDOR="${SERVIDOR:-ubuntu@18.188.167.127}"

[ -f "$LLAVE" ] || { echo "No encuentro la llave de AWS en $LLAVE (usa LLAVE=/ruta/llave.pem)"; exit 1; }

read -rsp "Pega la clave de Resend (empieza con re_) y pulsa Enter: " CLAVE
echo
case "$CLAVE" in
  re_*) ;;
  *) echo "Esa no parece una clave de Resend (debe empezar con re_). No se cambió nada."; exit 1 ;;
esac

# La clave va por la entrada estándar de SSH (no en la línea de comandos): así no aparece en la lista de procesos.
printf '%s\n' "$CLAVE" | ssh -i "$LLAVE" -o IdentitiesOnly=yes "$SERVIDOR" 'read -r CLAVE; cd ~/Diagramador_UML_Examen2 \
  && cp back_generador_bd/.env back_generador_bd/.env.antes-correo \
  && sed -i "/^EMAIL_/d;/^DEFAULT_FROM_EMAIL=/d;/^PUBLIC_APP_URL=/d" back_generador_bd/.env \
  && { echo "EMAIL_HOST=smtp.resend.com"; echo "EMAIL_PORT=587"; echo "EMAIL_HOST_USER=resend"; echo "EMAIL_HOST_PASSWORD=$CLAVE"; \
       echo "DEFAULT_FROM_EMAIL=\"Diagramador UML <noreply@diagramador.dev>\""; echo "PUBLIC_APP_URL=https://diagramador.dev"; } >> back_generador_bd/.env \
  && docker-compose -f docker-compose.app.yml restart django >/dev/null 2>&1 \
  && echo "LISTO: la clave quedó en el servidor y Django se reinició."'
unset CLAVE
