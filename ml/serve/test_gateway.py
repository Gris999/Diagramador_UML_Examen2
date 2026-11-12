"""Pruebas de la puerta del modelo local (`gateway.py`), con servidores de atrás de mentira.

Correr desde la raíz del repositorio:  python3 -m unittest discover -s ml/serve -v
"""

import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import gateway

TOKEN = "clave-de-prueba"


class FakeBackend(ThreadingHTTPServer):
    """Hace de `mlx_lm.server`: devuelve qué modelo le pidieron y cuántos pedidos tiene a la vez."""

    daemon_threads = True

    def __init__(self, name, delay=0.0):
        super().__init__(("127.0.0.1", 0), FakeBackendHandler)
        self.name, self.delay = name, delay
        self.received = []
        self.active = self.peak = 0
        self.lock = threading.Lock()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}"


class FakeBackendHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._json(200, {"data": []})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with self.server.lock:
            self.server.received.append(body)
            self.server.active += 1
            self.server.peak = max(self.server.peak, self.server.active)
        time.sleep(self.server.delay)
        with self.server.lock:
            self.server.active -= 1
        self._json(200, {"choices": [{"message": {"content": f"respuesta de {self.server.name}"}}]})


def serve(server):
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.chat = serve(FakeBackend("chat"))
        self.change = serve(FakeBackend("cambios", delay=0.4))
        self.gateway = serve(gateway.Gateway(("127.0.0.1", 0), {"chat": self.chat.url, "cambios": self.change.url}, TOKEN))
        self.base = f"http://127.0.0.1:{self.gateway.server_address[1]}"
        self.addCleanup(lambda: [s.shutdown() or s.server_close() for s in (self.chat, self.change, self.gateway)])

    def call(self, path="/v1/chat/completions", body=None, token=TOKEN, method="POST", raw=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        request = urllib.request.Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        if token is not None:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def ask(self, model, **extra):
        return self.call(body={"model": model, "messages": [{"role": "user", "content": "hola"}], **extra})

    def test_the_key_is_required_for_every_route(self):
        self.assertEqual(self.call(body={"model": "chat", "messages": []}, token=None)[0], 401)
        self.assertEqual(self.call(body={"model": "chat", "messages": []}, token="otra")[0], 401)
        self.assertEqual(self.call("/v1/models", method="GET", token=None)[0], 401)
        self.assertEqual(self.chat.received, [])

    def test_each_model_name_goes_to_its_own_server_with_the_name_mlx_expects(self):
        self.assertEqual(self.ask("chat")[1]["choices"][0]["message"]["content"], "respuesta de chat")
        self.assertEqual(self.ask("cambios")[1]["choices"][0]["message"]["content"], "respuesta de cambios")
        self.assertEqual(self.chat.received[0]["model"], "default_model")
        self.assertEqual(self.change.received[0]["model"], "default_model")

    def test_an_unknown_model_or_a_malformed_request_is_refused(self):
        self.assertEqual(self.ask("gpt-4")[0], 400)
        self.assertEqual(self.call(body={"model": "chat"})[0], 400)
        self.assertEqual(self.call(raw=b"no es json")[0], 400)
        self.assertEqual(self.chat.received + self.change.received, [])

    def test_only_the_chat_route_and_the_model_list_exist(self):
        for path in ("/api/delete", "/api/pull", "/v1/completions", "/"):
            self.assertEqual(self.call(path, body={"model": "chat", "messages": []})[0], 404, path)
        self.assertEqual(self.call("/api/tags", method="GET")[0], 404)

    def test_streaming_is_turned_off_and_the_answer_length_is_capped(self):
        self.ask("chat", stream=True, max_tokens=999999)

        sent = self.chat.received[0]
        self.assertIs(sent["stream"], False)
        self.assertEqual(sent["max_tokens"], gateway.MAX_TOKENS)

    def test_a_huge_request_is_refused_without_reading_it(self):
        try:
            status, _ = self.call(raw=b"x" * (gateway.MAX_BODY_BYTES + 1))
        except (urllib.error.URLError, ConnectionError):
            status = 413  # la puerta corta la conexión sin leer el cuerpo: el cliente a veces ve el corte antes que la respuesta

        self.assertEqual(status, 413)
        self.assertEqual(self.chat.received + self.change.received, [])

    def test_the_model_list_says_whether_both_servers_are_up(self):
        self.assertEqual(self.call("/v1/models", method="GET")[0], 200)
        self.chat.shutdown()
        self.chat.server_close()

        status, payload = self.call("/v1/models", method="GET")

        self.assertEqual(status, 503)
        self.assertEqual(payload["caidos"], ["chat"])

    def test_a_server_that_is_down_gives_a_clear_error_not_a_crash(self):
        self.change.shutdown()
        self.change.server_close()

        self.assertEqual(self.ask("cambios")[0], 502)

    def test_requests_are_forwarded_at_the_same_time_not_one_after_another(self):
        started = time.monotonic()
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.ask("cambios")[0])) for _ in range(3)]
        [t.start() for t in threads]
        [t.join() for t in threads]

        self.assertEqual(results, [200, 200, 200])
        self.assertEqual(self.change.peak, 3)  # los tres llegaron juntos al servidor de atrás
        self.assertLess(time.monotonic() - started, 1.0)  # 3 × 0,4 s en fila serían 1,2 s


if __name__ == "__main__":
    unittest.main()
