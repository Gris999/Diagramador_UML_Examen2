import asyncio
import json
import logging
import time
import unicodedata
import uuid
from collections import deque
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer
from uml_api.services.services_gemini import call_gemini_analysis
import re

from .activity import ORMActivityStore
from .groups import room_group_name, viewers_group_name
from .identity import RedisGroupIdentityStore
from .roles import RedisGroupRoleStore


logger = logging.getLogger(__name__)


class CanvasConsumer(AsyncWebsocketConsumer):
    role_store_class = RedisGroupRoleStore
    identity_store_class = RedisGroupIdentityStore
    activity_store_class = ORMActivityStore
    activity_types = {"add_class", "delete", "add_link", "edit_text"}
    edit_coalesce_seconds = 5
    # Tope del registro de actividad: no limita el relé, solo lo que se guarda.
    activity_data_limit = 8192
    activity_rate_limit = 60
    activity_rate_window = 10
    # Un observador puede pedir el estado completo, pero cada pedido hace que
    # todos los editores respondan: se limita para que no sirva de amplificador.
    viewer_state_request_interval = 2
    # Además de por conexión, el pedido se limita por sala y se entrega solo al
    # host (no a todos los editores): así una sala no recibe más de un estado
    # completo por intervalo por muchos observadores que abran. Las cuentas
    # viven en el proceso, igual que el resto de los topes por conexión.
    room_state_request_interval = 1
    max_viewers_per_room = 10
    viewer_counts = {}
    last_room_state_request = {}
    # Cada `hello` con un token nuevo crea un participante: una conexión no
    # puede fabricar identidades sin fin.
    max_identity_changes = 5

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = room_group_name(self.room_name)
        self.viewers_group_name = viewers_group_name(self.room_name)
        self.is_viewer = self._requested_viewer()
        if self.is_viewer:
            await self._connect_viewer()
            return
        self.role_store = self.role_store_class(
            self.channel_layer,
            self.room_group_name,
        )
        self.identity_store = self.identity_store_class(
            self.channel_layer,
            self.room_group_name,
        )
        self.activity_store = self.activity_store_class()
        self.participant_id = None
        self.display_name = None
        self._edit_activity_times = {}
        self._identity = None
        self._identity_changes = 0
        self._activity_window_start = time.monotonic()
        self._activity_window_count = 0

        members = await self.role_store.join(self.channel_name)
        await self.accept()
        # Lo primero que recibe una conexión es su propio identificador. Sin
        # esto el cliente lo deducía del primer aviso de presencia, que puede
        # ser el de otra persona que entró en el mismo instante.
        await self.send(text_data=json.dumps({
            "type": "presence",
            "action": "self",
            "peer": self.channel_name,
        }))

        # Notificar presencia
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "presence",
                "action": "join",
                "peer": self.channel_name
            }
        )
        await self._broadcast_presence_state(members)

    async def disconnect(self, close_code):
        if getattr(self, "is_viewer", False):
            if getattr(self, "_viewer_counted", False):
                self._release_viewer_slot()
            await self.channel_layer.group_discard(
                self.viewers_group_name,
                self.channel_name,
            )
            return
        if not hasattr(self, "role_store"):
            return

        await self._delete_identity(self.channel_name)
        removed, members = await self.role_store.leave(self.channel_name)
        if not removed:
            return

        # Notificar salida
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "presence",
                "action": "leave",
                "peer": self.channel_name
            }
        )
        await self._broadcast_presence_state(members)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (TypeError, json.JSONDecodeError):
            return
        if not isinstance(data, dict):
            return
        if self.is_viewer:
            await self._receive_from_viewer(data)
            return

        # Si es un broadcast → enviar a todos
        if data.get("type") == "broadcast":
            if "payload" not in data:
                return
            payload = data["payload"]
            await self._send_to_room(
                {
                    "type": "broadcast_message",
                    "from": self.channel_name,
                    "payload": payload
                }
            )
            await self._record_activity(payload)

        # Si es una señal directa → mandar a un peer específico
        elif data.get("type") == "signal":
            to = data["to"]
            await self.channel_layer.send(
                to,
                {
                    "type": "signal_message",
                    "from": self.channel_name,
                    "payload": data["payload"]
                }
            )

        elif data.get("type") == "hello":
            await self._handle_hello(data)

        elif data.get("type") == "remove_participant":
            target = data.get("peer")
            if not isinstance(target, str):
                await self._reject_removal()
                return

            authorized, members = await self.role_store.remove_by_host(
                self.channel_name,
                target,
            )
            if not authorized:
                await self._reject_removal()
                return

            await self._delete_identity(target)
            await self.channel_layer.send(
                target,
                {
                    "type": "force_disconnect",
                    "removed_by": self.channel_name,
                },
            )
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "presence",
                    "action": "remove",
                    "peer": target,
                },
            )
            await self._broadcast_presence_state(members)

    def _requested_viewer(self):
        query = parse_qs(self.scope.get("query_string", b"").decode("utf-8", "ignore"))
        return "viewer" in query.get("mode", [])

    async def _connect_viewer(self):
        # Los observadores van en un grupo aparte: no entran al orden que define
        # al host, no figuran en la presencia y no pueden expulsar ni ser
        # expulsados. Solo reciben lo que ocurre en la sala.
        self._last_state_request = None
        self._viewer_counted = False
        if self.viewer_counts.get(self.room_name, 0) >= self.max_viewers_per_room:
            await self.close(code=4009)
            return
        self.viewer_counts[self.room_name] = self.viewer_counts.get(self.room_name, 0) + 1
        self._viewer_counted = True
        self._viewer_role_store = self.role_store_class(
            self.channel_layer,
            self.room_group_name,
        )
        await self.channel_layer.group_add(self.viewers_group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "presence",
            "action": "self",
            "peer": self.channel_name,
        }))

    def _release_viewer_slot(self):
        self._viewer_counted = False
        remaining = self.viewer_counts.get(self.room_name, 0) - 1
        if remaining > 0:
            self.viewer_counts[self.room_name] = remaining
        else:
            self.viewer_counts.pop(self.room_name, None)

    async def _receive_from_viewer(self, data):
        # Lo único que un observador puede pedir es el estado completo para
        # dibujar el diagrama; cualquier otra cosa se ignora.
        payload = data.get("payload")
        if (
            data.get("type") == "broadcast"
            and isinstance(payload, dict)
            and payload.get("t") == "request_full_state"
            and self._allow_viewer_state_request()
        ):
            await self._ask_host_for_state()

    async def _ask_host_for_state(self):
        # Solo el host contesta: si respondieran todos los editores, cada
        # pedido se multiplicaría por la cantidad de personas conectadas.
        try:
            members = await self._viewer_role_store.members()
        except Exception:
            logger.exception("Could not read the room members for a viewer")
            return
        if not members:
            return
        await self.channel_layer.send(
            members[0],
            {
                "type": "broadcast_message",
                "from": self.channel_name,
                "payload": {"t": "request_full_state"},
            },
        )

    def _allow_viewer_state_request(self):
        now = time.monotonic()
        last = self._last_state_request
        if last is not None and now - last < self.viewer_state_request_interval:
            return False
        last_room = self.last_room_state_request.get(self.room_name)
        if last_room is not None and now - last_room < self.room_state_request_interval:
            return False
        self._last_state_request = now
        self.last_room_state_request[self.room_name] = now
        # Las salas que ya no piden nada no se quedan en la tabla para siempre.
        if len(self.last_room_state_request) > 1000:
            for room, stamp in list(self.last_room_state_request.items()):
                if now - stamp > 60:
                    del self.last_room_state_request[room]
        return True

    async def _send_to_room(self, message):
        await self.channel_layer.group_send(self.room_group_name, message)
        await self.channel_layer.group_send(self.viewers_group_name, message)

    async def _reject_removal(self):
        await self.send(text_data=json.dumps({
            "type": "remove_rejected",
        }))

    async def _broadcast_presence_state(self, members):
        try:
            names = await self.identity_store.names(members)
        except Exception:
            logger.exception("Could not read collaboration identities")
            names = {}

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "presence",
                "action": "state",
                "members": [
                    {
                        "peer": peer,
                        "role": "host" if index == 0 else "participant",
                        "name": names.get(peer),
                    }
                    for index, peer in enumerate(members)
                ],
            },
        )

    async def _handle_hello(self, data):
        token = self._normalize_token(data.get("token"))
        name = self._clean_display_name(data.get("name"))
        if token is None or name is None:
            return
        # Un hello repetido no cambia nada: se evita reescribir la base de datos
        # y reemitir la presencia a toda la sala.
        if self._identity == (token, name):
            return
        if self._identity_changes >= self.max_identity_changes:
            return
        self._identity_changes += 1
        self._identity = (token, name)

        self.display_name = name
        try:
            await self.identity_store.set(self.channel_name, token, name)
        except Exception:
            logger.exception("Could not store collaboration identity")

        try:
            self.participant_id = await self.activity_store.identify(
                self.room_name,
                token,
                name,
            )
        except Exception:
            logger.exception("Could not persist collaboration participant")
            self.participant_id = None

        members = await self.role_store.members()
        await self._broadcast_presence_state(members)

    async def _delete_identity(self, channel_name):
        if not hasattr(self, "identity_store"):
            return
        try:
            await self.identity_store.delete(channel_name)
        except Exception:
            logger.exception("Could not delete collaboration identity")

    async def _record_activity(self, payload):
        if not isinstance(payload, dict):
            return

        event_type = payload.get("t")
        if event_type not in self.activity_types:
            return
        if event_type == "edit_text" and self._coalesce_edit(payload):
            return
        if not self._within_activity_rate_limit():
            return

        target_id = self._target_id(payload.get("id"))
        summary = self._activity_summary(event_type, payload)
        requester = self.display_name or "Usuario anónimo"
        # Los cambios que la IA aplica a pedido de alguien los envía el
        # navegador de esa persona marcados con via_ia: se registran a nombre
        # de la IA, indicando quién lo pidió.
        if payload.get("via_ia") is True:
            actor_kind = "ia"
            actor_name = "IA"
            summary = f"{summary} (a pedido de {requester})"[:255]
        else:
            actor_kind = "user"
            actor_name = requester

        try:
            event = await self.activity_store.record(
                room=self.room_name,
                actor_id=self.participant_id,
                actor_name=actor_name,
                event_type=event_type,
                target_id=target_id,
                summary=summary,
                data=self._activity_data(payload),
                actor_kind=actor_kind,
            )
        except Exception:
            logger.exception("Could not persist collaboration activity")
            return

        await self._send_to_room({"type": "activity", "event": event})

    def _within_activity_rate_limit(self):
        now = time.monotonic()
        if now - self._activity_window_start >= self.activity_rate_window:
            self._activity_window_start = now
            self._activity_window_count = 0
        self._activity_window_count += 1
        return self._activity_window_count <= self.activity_rate_limit

    @classmethod
    def _activity_data(cls, payload):
        try:
            size = len(json.dumps(payload, ensure_ascii=False))
        except (TypeError, ValueError):
            size = cls.activity_data_limit + 1
        if size <= cls.activity_data_limit:
            return payload
        return {
            "t": payload.get("t"),
            "id": cls._target_id(payload.get("id")),
            "truncated": True,
        }

    def _coalesce_edit(self, payload):
        now = time.monotonic()
        self._edit_activity_times = {
            key: timestamp
            for key, timestamp in self._edit_activity_times.items()
            if now - timestamp < self.edit_coalesce_seconds
        }
        field = payload.get("field")
        key = (
            self._target_id(payload.get("id")),
            field if isinstance(field, str) else "",
        )
        previous = self._edit_activity_times.get(key)
        self._edit_activity_times[key] = now
        return previous is not None

    @staticmethod
    def _normalize_token(value):
        if not isinstance(value, str):
            return None
        try:
            return str(uuid.UUID(value))
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _clean_display_name(value):
        if not isinstance(value, str):
            return None
        cleaned = "".join(
            character
            for character in value
            if not unicodedata.category(character).startswith("C")
        ).strip()
        if not 1 <= len(cleaned) <= 40:
            return None
        return cleaned

    @staticmethod
    def _target_id(value):
        if isinstance(value, (str, int)):
            return str(value)[:255]
        return ""

    @classmethod
    def _activity_summary(cls, event_type, payload):
        if event_type == "add_class":
            name = cls._short_text(payload.get("payload", {}).get("name")) \
                if isinstance(payload.get("payload"), dict) else ""
            return f"añadió la clase {name}" if name else "añadió una clase"
        if event_type == "delete":
            return "eliminó un elemento"
        if event_type == "add_link":
            return "añadió una relación"

        field = payload.get("field")
        if field == "name":
            name = cls._short_text(payload.get("value"))
            return f"renombró una clase como {name}" if name else "renombró una clase"
        labels = {
            "attributes": "editó los atributos",
            "methods": "editó los métodos",
        }
        return labels.get(field, "editó una clase")

    @staticmethod
    def _short_text(value):
        if not isinstance(value, str):
            return ""
        cleaned = "".join(
            character
            for character in value
            if not unicodedata.category(character).startswith("C")
        )
        return " ".join(cleaned.split())[:80]

    # Handlers para los eventos enviados
    async def broadcast_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "broadcast",
            "from": event["from"],
            "payload": event["payload"]
        }))

    async def signal_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "signal",
            "from": event["from"],
            "payload": event["payload"]
        }))

    async def activity(self, event):
        await self.send(text_data=json.dumps({
            "type": "activity",
            "event": event["event"],
        }, ensure_ascii=False))

    async def force_disconnect(self, event):
        await self.send(text_data=json.dumps({
            "type": "removed",
            "by": event["removed_by"],
        }))
        await self.close(code=4003)

    async def presence(self, event):
        message = {
            "type": "presence",
            "action": event["action"],
        }
        if "peer" in event:
            message["peer"] = event["peer"]
        if "members" in event:
            message["members"] = event["members"]
        await self.send(text_data=json.dumps(message))



class ValidationBudget:
    """Tope de validaciones con IA para todo el servicio, no por conexión.

    Un límite por conexión no frena a quien abre muchas: este cuenta cuántas
    validaciones hay en curso y cuántas empezaron en el último minuto. Todo corre
    en un solo bucle de eventos, así que no necesita candados.
    """

    def __init__(self, max_concurrent=3, max_per_minute=20):
        self.max_concurrent = max_concurrent
        self.max_per_minute = max_per_minute
        self.active = 0
        self.started = deque()

    def acquire(self):
        now = time.monotonic()
        while self.started and now - self.started[0] > 60:
            self.started.popleft()
        if self.active >= self.max_concurrent or len(self.started) >= self.max_per_minute:
            return False
        self.active += 1
        self.started.append(now)
        return True

    def release(self):
        self.active = max(0, self.active - 1)


class UMLConsumer(AsyncWebsocketConsumer):
    """Validación del modelo con IA (Gemini) tras cada cambio que borra algo.

    Gemini tarda segundos: la llamada se hace en un hilo para no congelar el
    bucle de eventos (que atiende a todas las salas). Una ráfaga de pedidos se
    reduce a dos validaciones como máximo: la primera, enseguida, y una última
    con el diagrama más reciente cuando pasa el intervalo; así el resultado
    final siempre corresponde al último estado. Si ese estado ya se validó, no
    se vuelve a llamar a la IA.
    """

    # Se acepta como máximo una validación cada tantos segundos por conexión.
    min_validation_interval = 5
    max_message_chars = 200_000
    budget = ValidationBudget()

    async def connect(self):
        self._last_validation_end = None
        self._last_validated = None
        self._pending = None
        self._has_pending = False
        self._worker = None
        await self.accept()

    async def disconnect(self, code):
        worker = getattr(self, "_worker", None)
        if worker is not None:
            worker.cancel()

    async def receive(self, text_data):
        if not isinstance(text_data, str) or len(text_data) > self.max_message_chars:
            return
        try:
            data = json.loads(text_data)
        except (TypeError, ValueError):
            return
        if not isinstance(data, dict) or data.get("action") != "validate_model":
            return

        # Solo importa el diagrama más reciente: los intermedios se descartan.
        self._pending = data.get("uml")
        self._has_pending = True
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._validate_pending())

    async def _validate_pending(self):
        try:
            while self._has_pending:
                last = self._last_validation_end
                wait = 0 if last is None else self.min_validation_interval - (time.monotonic() - last)
                if wait > 0:
                    await asyncio.sleep(wait)

                uml_json, self._pending, self._has_pending = self._pending, None, False
                fingerprint = json.dumps(uml_json, sort_keys=True, ensure_ascii=False)
                if fingerprint == self._last_validated:
                    continue

                analysis = await self._analyze(uml_json)
                self._last_validated = fingerprint
                await self.send(text_data=json.dumps({
                    "action": "validation_result",
                    "analysis": analysis,
                }, ensure_ascii=False))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Falló la validación del modelo (%s)", type(exc).__name__)

    async def _analyze(self, uml_json):
        if not self.budget.acquire():
            return {"error": "Hay muchas validaciones en curso. Se intentará con el próximo cambio."}

        prompt = f"""
Eres un experto en diseño de bases de datos.
Analiza si las relaciones de este UML son correctas en base a los nombres y atributos.

JSON UML:
{json.dumps(uml_json, indent=2)}
"""
        try:
            raw_output = await asyncio.to_thread(call_gemini_analysis, prompt)
        except Exception as exc:
            logger.warning("No se pudo validar el modelo (%s)", type(exc).__name__)
            return {"error": "No se pudo validar el modelo ahora."}
        finally:
            self.budget.release()
            self._last_validation_end = time.monotonic()

        # 🧹 limpiar markdown (```json ... ```)
        if isinstance(raw_output, str):
            raw_output = re.sub(r"^```json\s*|\s*```$", "", raw_output.strip(), flags=re.MULTILINE)
        try:
            return json.loads(raw_output)
        except Exception:
            return {"error": "Formato inválido", "raw": raw_output}
