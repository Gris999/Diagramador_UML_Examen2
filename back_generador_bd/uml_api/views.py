import tempfile
from django.http import FileResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import BackupUML
import json
import re

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
import base64
from .services.services_gemini import (
    call_gemini,
    call_gemini_from_image,
    call_gemini_transcribe_audio,
)


from pathlib import Path
from .services.flutter_generator import FlutterCRUDGenerator
from .services.xmi_service import XMIError, export_uml_to_xmi, import_xmi_to_uml
from .utils.zip_utils import compress_folder_to_zip


class GenerateUMLView(APIView):
    def post(self, request):
        prompt = request.data.get("prompt")
        current_uml = request.data.get("uml")
        if not prompt:
            return Response({"error": "El campo 'prompt' es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            output = call_gemini(prompt, current_uml=current_uml)
        except Exception:
            return Response(
                {
                    "error": (
                        "No se pudo procesar la solicitud "
                        "con el servicio de IA."
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 🧹 Limpiar bloque de código Markdown si viene envuelto en ```json ... ```
        if isinstance(output, str):
            output = re.sub(r"^```json\s*|\s*```$", "",
                            output.strip(), flags=re.MULTILINE)

        try:
            parsed_json = json.loads(output)
        except Exception:
            return Response({
                "error": "La IA devolvió un modelo UML inválido."
            }, status=status.HTTP_502_BAD_GATEWAY)

        return Response(parsed_json, status=status.HTTP_200_OK)


@api_view(['POST'])
def set_backupUML(request, room_id):
    if not room_id:
        return Response({"error": "Se requiere el campo 'room_id'"}, status=status.HTTP_400_BAD_REQUEST)

    data = request.data

    try:
        # Buscar si ya existe
        uml_backup, created = BackupUML.objects.update_or_create(
            room_id=room_id,
            defaults={"data": data}
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "message": "UML creado con éxito" if created else "UML actualizado con éxito",
        "room_id": str(uml_backup.room_id),
        "data": uml_backup.data
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET'])
def get_backupUML(request, room_id):
    if not room_id:
        return Response({"error": "Se requiere el campo 'room_id'"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        diagrama = BackupUML.objects.get(room_id=room_id)
    except BackupUML.DoesNotExist:
        return Response({"error": "No existe un diagrama con ese ID"}, status=status.HTTP_404_NOT_FOUND)

    # ✅ Devolver el JSON guardado exactamente como está en la BD
    return Response(diagrama.data, status=status.HTTP_200_OK)



@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def analyze_uml_audio(request):
    """
    Recibe audio de una instrucción UML, lo transcribe
    mediante Gemini y reutiliza el flujo de texto existente.
    """
    audio_file = request.FILES.get("audio")
    current_uml = request.data.get("uml")

    if isinstance(current_uml, str):
        try:
            current_uml = json.loads(current_uml)
        except json.JSONDecodeError:
            return Response(
                {"error": "El contexto UML debe ser JSON válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if not audio_file:
        return Response(
            {
                "error": (
                    "Debe enviar un archivo de audio "
                    "en el campo 'audio'."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if audio_file.size > 10 * 1024 * 1024:
        return Response(
            {
                "error": (
                    "El archivo de audio supera "
                    "el límite de 10 MB."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    mime_type = (
        audio_file.content_type
        or "audio/webm"
    ).split(";", 1)[0].lower()

    allowed_audio_types = {
        "audio/webm",
        "audio/ogg",
        "audio/wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/aac",
        "audio/m4a",
        "audio/opus",
        "audio/flac",
    }

    if mime_type not in allowed_audio_types:
        return Response(
            {
                "error": (
                    "Formato de audio no compatible: "
                    f"{mime_type}"
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    audio_base64 = base64.b64encode(
        audio_file.read()
    ).decode("utf-8")

    try:
        transcript = call_gemini_transcribe_audio(
            audio_base64,
            mime_type=mime_type,
        )

        output = call_gemini(transcript, current_uml=current_uml)

    except Exception:
        return Response(
            {
                "error": (
                    "No se pudo procesar la instrucción "
                    "de voz con el servicio de IA."
                )
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if isinstance(output, str):
        output = re.sub(
            r"^```json\s*|\s*```$",
            "",
            output.strip(),
            flags=re.MULTILINE,
        )

    try:
        parsed_json = json.loads(output)
    except Exception:
        return Response(
            {
                "error": (
                    "La IA devolvió un modelo UML "
                    "inválido para la instrucción de voz."
                )
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response(
        {
            "transcript": transcript,
            "uml_json": parsed_json,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def analyze_uml_image(request):
    """
    Espera un archivo de imagen (PNG o JPG).
    """
    image_file = request.FILES.get("image")

    if not image_file:
        return Response({"error": "Debe enviar un archivo 'image'"}, status=status.HTTP_400_BAD_REQUEST)

    if image_file.size > 10 * 1024 * 1024:
        return Response(
            {"error": "La imagen supera el límite de 10 MB."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    mime_type = (image_file.content_type or "").split(";", 1)[0].lower()
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        return Response(
            {"error": "Formato de imagen no compatible."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Convertir a Base64
    image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # Llamar al servicio Gemini
    try:
        result = call_gemini_from_image(
            image_base64,
            mime_type=mime_type,
        )
    except Exception:
        return Response(
            {"error": "No se pudo analizar la imagen con el servicio de IA."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if isinstance(result, dict) and result.get("error"):
        return Response(
            {
                "error": (
                    "No se pudo analizar la imagen "
                    "con el servicio de IA."
                )
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Intentar parsear el resultado JSON
    try:
        parsed = json.loads(result) if isinstance(result, str) else result
    except Exception:
        return Response(
            {"error": "La IA devolvió un modelo UML inválido."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({"uml_json": parsed}, status=status.HTTP_200_OK)


@api_view(["POST"])
def generar_flutter(request):
    """
    Genera un proyecto Flutter completo a partir de un JSON UML.
    Devuelve un ZIP descargable.
    """
    try:
        uml_json = request.data
        if not uml_json.get("classes"):
            return Response({"error": "El JSON UML debe contener 'classes'."}, status=400)

        # Crear carpeta temporal
        temp_dir = Path(tempfile.mkdtemp())

        # Generar el proyecto Flutter
        generator = FlutterCRUDGenerator(uml_json)
        generator.generate_project(output_dir=temp_dir / "flutter_app")

        # Comprimir el resultado
        zip_path = compress_folder_to_zip(temp_dir / "flutter_app")

        # Devolver como archivo descargable
        response = FileResponse(
            open(zip_path, "rb"),
            as_attachment=True,
            filename="flutter_project.zip"
        )
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def export_xmi(request):
    """
    Exporta el JSON UML interno a un archivo XMI 2.1.
    """
    try:
        xmi_bytes = export_uml_to_xmi(request.data)
    except XMIError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = HttpResponse(
        xmi_bytes,
        content_type="application/xml; charset=utf-8",
    )
    response["Content-Disposition"] = (
        'attachment; filename="diagram.xmi"'
    )
    return response


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_xmi(request):
    """
    Importa un archivo XMI/XML y devuelve el JSON UML interno.
    """
    xmi_file = request.FILES.get("file")

    if not xmi_file:
        return Response(
            {"error": "Debe enviar un archivo XMI en el campo 'file'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        uml_json = import_xmi_to_uml(xmi_file)
    except XMIError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        uml_json,
        status=status.HTTP_200_OK,
    )
