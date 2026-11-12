"""Interfaz de proveedor de IA para el chat de la sala.

El chat habla con la IA a través de `AIProvider`, de modo que se pueda cambiar
de proveedor (Gemini hoy; un modelo local después) sin tocar vistas ni
interfaz. Los proveedores solo conversan: no devuelven operaciones sobre el
diagrama.
"""

import json
import re
import time

import requests
from django.conf import settings

from . import modelo_reentrenado
from .services_gemini import _post_gemini, build_change_prompt, call_gemini


class AIProviderError(Exception):
    """La IA no pudo responder (configuración, red o respuesta inválida)."""


def _parse_changes(output) -> dict:
    """Interpreta la respuesta de un cambio (JSON, con o sin cerco de Markdown)."""
    try:
        if isinstance(output, str):
            output = modelo_reentrenado.quitar_razonamiento(output)
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

    def __init__(self, base_url=None, model=None, change_model=None):
        self.base_url = (
            base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self.model = model or getattr(settings, "OLLAMA_MODEL", "qwen3.5:9b")
        # Modelo reentrenado para los cambios al diagrama (opcional). Las preguntas
        # y la revisión siguen con `model`, que es de propósito general.
        self.change_model = change_model or getattr(settings, "OLLAMA_CHANGE_MODEL", "") or ""

    def _generate(self, prompt: str) -> str:
        # `think: False`: los modelos con razonamiento (Qwen 3.5) piensan en voz
        # alta antes de responder, lo que multiplica el tiempo; aquí se quiere
        # la respuesta directa. No se usa `format: "json"`: Qwen 3.5 en Ollama
        # responde "structured output is unavailable"; el prompt ya exige JSON y
        # `_parse_changes` tolera el cerco de Markdown.
        body = {"model": self.model, "prompt": prompt, "stream": False, "think": False}
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

    def _chat_reentrenado(self, mensajes) -> str:
        body = {
            "model": self.change_model,
            "messages": mensajes,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_predict": 700, "num_ctx": 4096},
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/chat", json=body, timeout=self.request_timeout
            )
            response.raise_for_status()
            text = response.json()["message"]["content"]
        except Exception as exc:
            raise AIProviderError(
                f"El modelo reentrenado no respondió ({type(exc).__name__})."
            ) from None
        if not isinstance(text, str) or not text.strip():
            raise AIProviderError("El modelo reentrenado devolvió una respuesta vacía.")
        return text.strip()

    def change(self, instruction: str, uml) -> dict:
        if self.change_model:
            compacto, alias = modelo_reentrenado.compactar(uml)
            respuesta = self._chat_reentrenado(modelo_reentrenado.mensajes(compacto, instruction))
            return modelo_reentrenado.restaurar(_parse_changes(respuesta), alias, uml)
        prompt = (
            build_change_prompt(instruction, uml)
            + "\n\nResponde ÚNICAMENTE con el JSON, sin explicaciones ni Markdown."
        )
        return _parse_changes(self._generate(prompt))


class LocalParallelProvider(AIProvider):
    """Modelo local que contesta varios pedidos a la vez: `mlx_lm.server` mezcla los pedidos en una sola pasada del modelo.

    Ollama en un Mac con Apple Silicon (motor MLX) atiende de uno en uno aunque se le suba `OLLAMA_NUM_PARALLEL`; `mlx_lm.server` con
    `--decode-concurrency` sí los atiende juntos. Este proveedor le habla a la puerta de `ml/serve` (una sola dirección y una clave), que
    reparte según el nombre del modelo: `cambios` es el Qwen3-4B con el adaptador que reentrenó el equipo y `chat` es el mismo modelo
    sin adaptador, para preguntas y revisiones.
    """

    request_timeout = 100
    CHAT_MODEL = "chat"
    CHANGE_MODEL = "cambios"
    CHAT_MAX_TOKENS = 800
    CHANGE_MAX_TOKENS = 700

    def __init__(self, base_url=None, token=None):
        self.base_url = (base_url or getattr(settings, "LOCAL_AI_URL", "http://127.0.0.1:8090")).rstrip("/")
        self.token = token if token is not None else getattr(settings, "LOCAL_AI_TOKEN", "")

    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _complete(self, model: str, messages: list, max_tokens: int, temperature: float) -> str:
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=body,
                headers=self.headers(),
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            # Solo el tipo del error: el mensaje de `requests` lleva la dirección y no hace falta mostrarla.
            raise AIProviderError(f"El modelo local no respondió ({type(exc).__name__}).") from None
        if not isinstance(text, str) or not text.strip():
            raise AIProviderError("El modelo local devolvió una respuesta vacía.")
        return text.strip()

    def chat(self, prompt: str) -> str:
        return self._complete(self.CHAT_MODEL, [{"role": "user", "content": prompt}], self.CHAT_MAX_TOKENS, 0.3)

    def change(self, instruction: str, uml) -> dict:
        compacto, alias = modelo_reentrenado.compactar(uml)
        respuesta = self._complete(
            self.CHANGE_MODEL, modelo_reentrenado.mensajes(compacto, instruction), self.CHANGE_MAX_TOKENS, 0
        )
        return modelo_reentrenado.restaurar(_parse_changes(respuesta), alias, uml)

    def reachable(self) -> bool:
        try:
            return requests.get(
                f"{self.base_url}/v1/models", headers=self.headers(), timeout=OLLAMA_CHECK_TIMEOUT
            ).ok
        except Exception:
            return False


GEMINI = "gemini"
# El modelo "Local" de la sala. Detrás puede estar Ollama (un pedido a la vez) o la puerta de `ml/serve` con `mlx_lm.server` (varios a la vez): `LOCAL_ENGINE`.
OLLAMA = "ollama"
ENGINE_OLLAMA = "ollama"
ENGINE_MLX = "mlx"
# Cuántas personas atiende a la vez en una sala si no se configura otra cosa: la nube y el motor mlx contestan varias a la vez; Ollama, una.
DEFAULT_SLOTS = {GEMINI: 4, ENGINE_MLX: 4, ENGINE_OLLAMA: 1}
# Cuánto tiempo se recuerda si el modelo local responde, para no preguntarle en cada pedido de la pantalla.
OLLAMA_CHECK_SECONDS = 10
OLLAMA_CHECK_TIMEOUT = 1.5
_ollama_check = {"at": None, "up": False}


def default_provider_name() -> str:
    """El proveedor que el servidor usa mientras la sala no elija otro (variable `AI_PROVIDER`)."""
    return str(getattr(settings, "AI_PROVIDER", GEMINI)).strip().lower()


def forget_ollama_check() -> None:
    _ollama_check["at"] = None


def _gemini_configured() -> bool:
    key = getattr(settings, "GEMINI_API_KEY", None)
    return bool(key) and str(key).strip().lower() not in {"placeholder", "change-me"}


def local_engine() -> str:
    """El motor del modelo local: `ollama` (por defecto) o `mlx` (varios pedidos a la vez)."""
    engine = str(getattr(settings, "LOCAL_ENGINE", ENGINE_OLLAMA)).strip().lower()
    return ENGINE_MLX if engine == ENGINE_MLX else ENGINE_OLLAMA


def concurrency(name=None) -> int:
    """Cuántas personas puede atender a la vez la IA en una sala con ese modelo (al menos una)."""
    name = str(name).strip().lower() if name else default_provider_name()
    if name == OLLAMA:
        configured = int(getattr(settings, "AI_CONCURRENCY_LOCAL", 0) or 0)
        return max(1, configured or DEFAULT_SLOTS[local_engine()])
    configured = int(getattr(settings, "AI_CONCURRENCY_GEMINI", 0) or 0)
    return max(1, configured or DEFAULT_SLOTS[GEMINI])


def _ollama_reachable() -> bool:
    """El modelo local contesta ahora (se recuerda unos segundos). En el servidor de AWS sin túnel no hay modelo local y da `False`."""
    now = time.monotonic()
    if _ollama_check["at"] is not None and now - _ollama_check["at"] < OLLAMA_CHECK_SECONDS:
        return _ollama_check["up"]
    if local_engine() == ENGINE_MLX:
        up = LocalParallelProvider().reachable()
    else:
        base_url = str(getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        try:
            up = requests.get(f"{base_url}/api/tags", timeout=OLLAMA_CHECK_TIMEOUT).ok
        except Exception:
            up = False
    _ollama_check.update(at=now, up=up)
    return up


def get_ai_provider(name=None) -> AIProvider:
    name = str(name).strip().lower() if name else default_provider_name()
    if name == GEMINI:
        return GeminiProvider()
    if name == OLLAMA:
        return LocalParallelProvider() if local_engine() == ENGINE_MLX else OllamaProvider()
    raise AIProviderError(f"Proveedor de IA desconocido: {name}")


def _ollama_label() -> str:
    if local_engine() == ENGINE_MLX:
        return "IA local (Qwen3-4B; cambios: reentrenado, varios a la vez)"
    model = getattr(settings, "OLLAMA_MODEL", "qwen3.5:9b")
    change_model = getattr(settings, "OLLAMA_CHANGE_MODEL", "")
    if change_model:
        return f"IA local ({model}; cambios: {change_model} reentrenado)"
    return f"IA local ({model})"


def describe_ai_provider(name=None) -> dict:
    """Qué proveedor responde, para mostrarlo en la interfaz (sin datos sensibles)."""
    name = str(name).strip().lower() if name else default_provider_name()
    if name == OLLAMA:
        return {"provider": OLLAMA, "label": _ollama_label()}
    return {"provider": GEMINI, "label": "IA en la nube (Gemini)"}


def provider_options() -> list:
    """Los modelos entre los que puede elegir una sala y si cada uno está disponible en este servidor."""
    return [
        {"id": GEMINI, "label": "Nube (Gemini)", "available": _gemini_configured()},
        {
            "id": OLLAMA,
            "label": "Local (Qwen3-4B)" if local_engine() == ENGINE_MLX else f"Local ({getattr(settings, 'OLLAMA_MODEL', 'qwen3.5:9b')})",
            "available": _ollama_reachable(),
        },
    ]
