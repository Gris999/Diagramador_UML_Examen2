import json
from channels.generic.websocket import AsyncWebsocketConsumer
from uml_api.services.services_gemini import call_gemini_analysis
import re
from .roles import RedisGroupRoleStore


class CanvasConsumer(AsyncWebsocketConsumer):
    role_store_class = RedisGroupRoleStore

    async def connect(self):
        print("[CanvasConsumer.connect] scope:", self.scope)
        print("[CanvasConsumer.connect] url_route:", self.scope.get("url_route"))
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"canvas_{self.room_name}"
        self.role_store = self.role_store_class(
            self.channel_layer,
            self.room_group_name,
        )

        members = await self.role_store.join(self.channel_name)
        await self.accept()

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
        if not hasattr(self, "role_store"):
            return

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
        data = json.loads(text_data)

        # Si es un broadcast → enviar a todos
        if data.get("type") == "broadcast":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "broadcast_message",
                    "from": self.channel_name,
                    "payload": data["payload"]
                }
            )

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

    async def _reject_removal(self):
        await self.send(text_data=json.dumps({
            "type": "remove_rejected",
        }))

    async def _broadcast_presence_state(self, members):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "presence",
                "action": "state",
                "members": [
                    {
                        "peer": peer,
                        "role": "host" if index == 0 else "participant",
                    }
                    for index, peer in enumerate(members)
                ],
            },
        )

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



class UMLConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "validate_model":
            uml_json = data.get("uml")

            prompt = f"""
Eres un experto en diseño de bases de datos.
Analiza si las relaciones de este UML son correctas en base a los nombres y atributos.

JSON UML:
{json.dumps(uml_json, indent=2)}
"""

            # Llamar a Gemini
            raw_output = call_gemini_analysis(prompt)

            # 🧹 limpiar markdown (```json ... ```)
            if isinstance(raw_output, str):
                raw_output = re.sub(r"^```json\s*|\s*```$", "", raw_output.strip(), flags=re.MULTILINE)

            try:
                analysis = json.loads(raw_output)
            except Exception:
                analysis = {"error": "Formato inválido", "raw": raw_output}

            # Enviar al front
            await self.send(text_data=json.dumps({
                "action": "validation_result",
                "analysis": analysis
            }, ensure_ascii=False))
