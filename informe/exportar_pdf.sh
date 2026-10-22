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
