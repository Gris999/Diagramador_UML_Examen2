"""Interfaz de proveedor de IA para el chat de la sala.

El chat habla con la IA a través de `AIProvider`, de modo que se pueda cambiar
de proveedor (Gemini hoy; un modelo local después) sin tocar vistas ni
interfaz. Los proveedores solo conversan: no devuelven operaciones sobre el
diagrama.
"""

import json
import re

import requests
from django.conf import settings

from .services_gemini import _post_gemini, build_change_prompt, call_gemini


class AIProviderError(Exception):
    """La IA no pudo responder (configuración, red o respuesta inválida)."""


def _parse_changes(output) -> dict:
    """Interpreta la respuesta de un cambio (JSON, con o sin cerco de Markdown)."""
    try:
        if isinstance(output, str):
            output = re.sub(r"^```json\s*|\s*```$", "", output.strip(), flags=re.MULTILINE)
        changes = json.loads(output)
    except Exception as exc:
        raise AIProviderError(
            f"La IA no devolvió un cambio válido ({type(exc).__name__})."
        ) from None
    if not isinstance(changes, dict) or changes.get("error"):
        raise AIProviderError("La IA no devolvió un cambio válido.")
    return changes


class AIProvider:
    def chat(self, prompt: str) -> str:
        """Respuesta en texto (preguntas y revisión). Nunca modifica el diagrama."""
        raise NotImplementedError

    def change(self, instruction: str, uml) -> dict:
        """Cambios al diagrama pedidos explícitamente, en el formato que ya
        consume `DiagramService.loadFromJson` (crear, editar o eliminar)."""
        raise NotImplementedError


class GeminiProvider(AIProvider):
    def chat(self, prompt: str) -> str:
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key or str(api_key).strip().lower() in {"placeholder", "change-me"}:
            raise AIProviderError("GEMINI_API_KEY no está configurada.")

        data = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            # En el chat se espera una respuesta corta: se corta antes que en
            # las demás llamadas para no dejar a la sala esperando minutos.
            response = _post_gemini(
                data,
                {"Content-Type": "application/json"},
                {"key": api_key},
                max_attempts=2,
                timeout=30,
            )
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            # No se propaga el mensaje original: las excepciones de `requests`
            # incluyen la URL completa, y esa URL lleva la clave de la API.
            raise AIProviderError(
                f"Gemini no respondió ({type(exc).__name__})."
            ) from None

        if not isinstance(text, str) or not text.strip():
            raise AIProviderError("Gemini devolvió una respuesta vacía.")
        return text.strip()


    def change(self, instruction: str, uml) -> dict:
        try:
            output = call_gemini(instruction, current_uml=uml)
        except Exception as exc:
            raise AIProviderError(
                f"Gemini no devolvió un cambio válido ({type(exc).__name__})."
            ) from None
        return _parse_changes(output)


class OllamaProvider(AIProvider):
    """Modelo local (p. ej. Qwen) servido por Ollama: la IA funciona sin internet.

    Usa las mismas instrucciones que Gemini; un modelo pequeño puede fallar más
    en el formato de los cambios, y entonces el cliente ve el error claro de
    siempre y el diagrama no se toca.
    """

    request_timeout = 100

    def __init__(self, base_url=None, model=None):
        self.base_url = (
            base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self.model = model or getattr(settings, "OLLAMA_MODEL", "qwen2.5:7b")

    def _generate(self, prompt: str, json_format: bool = False) -> str:
        body = {"model": self.model, "prompt": prompt, "stream": False}
        if json_format:
            body["format"] = "json"
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=body,
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            text = response.json()["response"]
        except Exception as exc:
            raise AIProviderError(
                f"El modelo local no respondió ({type(exc).__name__})."
            ) from None
        if not isinstance(text, str) or not text.strip():
            raise AIProviderError("El modelo local devolvió una respuesta vacía.")
        return text.strip()

    def chat(self, prompt: str) -> str:
        return self._generate(prompt)

    def change(self, instruction: str, uml) -> dict:
        return _parse_changes(
            self._generate(build_change_prompt(instruction, uml), json_format=True)
        )


def get_ai_provider() -> AIProvider:
    name = str(getattr(settings, "AI_PROVIDER", "gemini")).strip().lower()
    if name == "gemini":
        return GeminiProvider()
    if name == "ollama":
        return OllamaProvider()
    raise AIProviderError(f"Proveedor de IA desconocido: {name}")


def describe_ai_provider() -> dict:
    """Qué proveedor responde, para mostrarlo en la interfaz (sin datos sensibles)."""
    name = str(getattr(settings, "AI_PROVIDER", "gemini")).strip().lower()
    if name == "ollama":
        model = getattr(settings, "OLLAMA_MODEL", "qwen2.5:7b")
        return {"provider": "ollama", "label": f"IA local ({model})"}
    return {"provider": "gemini", "label": "IA en la nube (Gemini)"}
