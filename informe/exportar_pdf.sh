#!/usr/bin/env bash
# Abre build/Informe.docx en Microsoft Word, actualiza el índice, guarda el .docx
# actualizado y exporta el PDF. Requiere Word instalado (macOS) y permiso de automatización.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
DOCX="$DIR/build/Informe.docx"
PDF="$DIR/build/Informe.pdf"
rm -f "$PDF"
osascript <<APPLESCRIPT
with timeout of 1200 seconds
  tell application "Microsoft Word"
    activate
    -- Si el informe quedó abierto de una vez anterior, se cierra sin guardar: si no, Word reutiliza esa copia vieja y la guarda
    -- encima del archivo recién generado. Se compara por nombre porque Word entrega rutas con otro formato que la POSIX.
    repeat with n from (count of documents) to 1 by -1
      try
        if (name of document n) is "Informe.docx" then close document n saving no
      end try
    end repeat
    open POSIX file "$DOCX"
    set d to active document
    -- el primer campo del cuerpo es el índice
    update field (field 1 of d)
    save as d file name "$PDF" file format format PDF
    save d
    try
      close d saving yes
    end try
  end tell
end timeout
APPLESCRIPT
echo "PDF: $PDF"
