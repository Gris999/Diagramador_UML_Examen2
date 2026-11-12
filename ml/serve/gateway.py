"""Puerta del modelo local: una sola dirección y una clave delante de los dos `mlx_lm.server`.

El servidor de la aplicación (Django) le habla al modelo local con peticiones del estilo OpenAI (`/v1/chat/completions`). Detrás hay dos servidores
`mlx_lm.server` que mezclan varios pedidos en una sola pasada del modelo (Ollama, con el motor MLX de un Mac, atiende de uno en uno):

* `cambios`: Qwen3-4B con el adaptador que reentrenó el equipo (cambios al diagrama);
* `chat`: el mismo Qwen3-4B sin adaptador (preguntas y revisiones).

La puerta existe por dos razones. Una: darle a Django una sola dirección (y, si se abre un túnel hacia internet para que el sitio desplegado use el
modelo de este computador, un solo puerto que exponer). Dos: la seguridad, porque estos servidores no traen autenticación: la puerta exige la clave
(`Authorization: Bearer …`), deja pasar solo las dos rutas que hacen falta (nada de bajar o borrar modelos), limita el tamaño del pedido y de la
respuesta, y no acepta respuestas en flujo. Solo usa la biblioteca estándar de Python.
"""

import argparse
import hmac
import http.client
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_NAME = "default_model"  # el nombre que `mlx_lm.server` da al único modelo que carga
MAX_BODY_BYTES = 1_000_000
MAX_TOKENS = 1500
BACKEND_TIMEOUT_SECONDS = 150


class Gateway(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, routes, token):
        super().__init__(address, Handler)
        self.routes = routes  # {nombre del modelo: URL base del servidor que lo atiende}
        self.token = token


class Handler(BaseHTTPRequestHandler):
    server_version = "UmlLocalAi/1"  # HTTP/1.0: una conexión por pedido, así un pedido rechazado sin leer su cuerpo no ensucia el siguiente

    def log_message(self, format, *args):  # noqa: A002 - firma de la clase base
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), format % args))

    # -- respuestas -------------------------------------------------------------------------------------------------
    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        token = self.server.token
        if not token:
            return True
        given = self.headers.get("Authorization", "")
        return given.startswith("Bearer ") and hmac.compare_digest(given[len("Bearer "):], token)

    # -- rutas --------------------------------------------------------------------------------------------------------
    def do_GET(self):
        if not self._authorized():
            return self._send(401, {"error": "Falta la clave del modelo local."})
        if self.path.split("?", 1)[0] != "/v1/models":
            return self._send(404, {"error": "Ruta no disponible."})
        down = [name for name, url in self.server.routes.items() if not self._backend_up(url)]
        if down:
            return self._send(503, {"error": "El modelo local no está listo.", "caidos": down})
        self._send(200, {"object": "list", "data": [{"id": name, "object": "model"} for name in self.server.routes]})

    def do_POST(self):
        if not self._authorized():
            return self._send(401, {"error": "Falta la clave del modelo local."})
        if self.path.split("?", 1)[0] != "/v1/chat/completions":
            return self._send(404, {"error": "Ruta no disponible."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length <= 0 or length > MAX_BODY_BYTES:
            return self._send(413 if length > MAX_BODY_BYTES else 400, {"error": "Pedido vacío o demasiado grande."})
        try:
            body = json.loads(self.rfile.read(length))
            backend = self.server.routes[body["model"]]
            if not isinstance(body.get("messages"), list):
                raise ValueError("messages")
        except (KeyError, ValueError, TypeError):
            return self._send(400, {"error": "Pedido inválido: hace falta `model` (chat o cambios) y `messages`."})

        body["model"] = MODEL_NAME
        body["stream"] = False
        body["max_tokens"] = min(int(body.get("max_tokens") or MAX_TOKENS), MAX_TOKENS)
        status, payload = self._forward(backend, body)
        self._send(status, payload)

    # -- servidores de atrás ---------------------------------------------------------------------------------------
    @staticmethod
    def _connection(url):
        parts = urllib.parse.urlsplit(url)
        return http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=BACKEND_TIMEOUT_SECONDS)

    def _forward(self, backend, body):
        connection = self._connection(backend)
        try:
            connection.request("POST", "/v1/chat/completions", json.dumps(body), {"Content-Type": "application/json"})
            response = connection.getresponse()
            data = response.read()
            try:
                return response.status, json.loads(data)
            except ValueError:
                return 502, {"error": "El modelo local devolvió una respuesta ilegible."}
        except (OSError, http.client.HTTPException):
            return 502, {"error": "El modelo local no respondió."}
        finally:
            connection.close()

    def _backend_up(self, backend):
        connection = self._connection(backend)
        try:
            connection.request("GET", "/v1/models")
            return connection.getresponse().status == 200
        except (OSError, http.client.HTTPException):
            return False
        finally:
            connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--chat-url", default="http://127.0.0.1:8082")
    parser.add_argument("--change-url", default="http://127.0.0.1:8081")
    parser.add_argument("--token", default=os.environ.get("LOCAL_AI_TOKEN", ""), help="la clave; por defecto la variable LOCAL_AI_TOKEN")
    parser.add_argument("--no-auth", action="store_true", help="sin clave (solo para probar en este mismo computador)")
    args = parser.parse_args(argv)
    if not args.token and not args.no_auth:
        parser.error("hace falta una clave (--token o LOCAL_AI_TOKEN); usa --no-auth solo para pruebas locales")
    server = Gateway(("127.0.0.1", args.port), {"chat": args.chat_url, "cambios": args.change_url}, args.token)
    print(f"Puerta del modelo local en http://127.0.0.1:{args.port} (chat → {args.chat_url}, cambios → {args.change_url})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
