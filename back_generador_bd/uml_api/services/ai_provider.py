"""Interfaz de proveedor de IA para el chat de la sala.

El chat habla con la IA a través de `AIProvider`, de modo que se pueda cambiar
de proveedor (Gemini hoy; un modelo local después) sin tocar vistas ni
interfaz. Los proveedores solo conversan: no devuelven operaciones sobre el
diagrama.
"""

from django.conf import settings

from .services_gemini import _post_gemini


class AIProviderError(Exception):
    """La IA no pudo responder (configuración, red o respuesta inválida)."""


class AIProvider:
    def chat(self, prompt: str) -> str:
        raise NotImplementedError


class GeminiProvider(AIProvider):
    def chat(self, prompt: str) -> str:
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key or str(api_key).strip().lower() in {"placeholder", "change-me"}:
            raise AIProviderError("GEMINI_API_KEY no está configurada.")

        data = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = _post_gemini(
                data,
                {"Content-Type": "application/json"},
                {"key": api_key},
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


def get_ai_provider() -> AIProvider:
    name = str(getattr(settings, "AI_PROVIDER", "gemini")).strip().lower()
    if name == "gemini":
        return GeminiProvider()
    raise AIProviderError(f"Proveedor de IA desconocido: {name}")
