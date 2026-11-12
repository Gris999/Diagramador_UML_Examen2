from unittest import mock

import requests
from django.test import SimpleTestCase, override_settings

from uml_api.services import ai_provider
from uml_api.services.ai_provider import AIProviderError, LocalParallelProvider, OllamaProvider


def completion(text):
    response = mock.Mock()
    response.json.return_value = {"choices": [{"message": {"content": text}}]}
    return response


UML = {
    "classes": [{"id": "real-1", "name": "Cliente", "attributes": [{"name": "nombre", "type": "string"}], "methods": []}],
    "relationships": [],
}


class LocalParallelProviderTests(SimpleTestCase):
    def provider(self):
        return LocalParallelProvider(base_url="http://puerta.local:8090/", token="clave-secreta")

    def test_chat_goes_to_the_chat_model_through_the_gateway_with_the_key(self):
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=completion("  Hola  ")) as post:
            reply = self.provider().chat("pregunta")

        self.assertEqual(reply, "Hola")
        self.assertEqual(post.call_args.args[0], "http://puerta.local:8090/v1/chat/completions")
        self.assertEqual(post.call_args.kwargs["headers"], {"Authorization": "Bearer clave-secreta"})
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["model"], "chat")
        self.assertEqual(body["messages"], [{"role": "user", "content": "pregunta"}])
        self.assertIs(body["stream"], False)
        self.assertIn("timeout", post.call_args.kwargs)

    def test_without_a_key_no_authorization_header_is_sent(self):
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=completion("ok")) as post:
            LocalParallelProvider(base_url="http://127.0.0.1:8090", token="").chat("hola")

        self.assertEqual(post.call_args.kwargs["headers"], {})

    def test_change_uses_the_retrained_model_with_short_ids_and_restores_the_real_ones(self):
        reply = '<think>\n\n</think>\n\n{"classes":[{"id":"c1","name":"Cliente","attributes":[{"name":"nombre","type":"string"},{"name":"correo","type":"string"}],"methods":[]}],"relationships":[]}'
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=completion(reply)) as post:
            changes = self.provider().change("agrega correo a Cliente", UML)

        body = post.call_args.kwargs["json"]
        self.assertEqual(body["model"], "cambios")
        self.assertEqual(body["temperature"], 0)
        self.assertIn("PEDIDO: agrega correo a Cliente", body["messages"][1]["content"])
        self.assertNotIn("real-1", body["messages"][1]["content"])  # el modelo ve ids cortos, no los del editor
        self.assertEqual(changes["classes"][0]["id"], "real-1")
        self.assertEqual([a["name"] for a in changes["classes"][0]["attributes"]], ["nombre", "correo"])

    def test_a_new_class_that_the_model_numbers_like_an_existing_one_does_not_overwrite_it(self):
        reply = '{"classes":[{"id":"c1","name":"Producto","attributes":[{"name":"precio","type":"float"}],"methods":[]}],"relationships":[]}'
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=completion(reply)):
            changes = self.provider().change("agrega una clase Producto con precio", UML)

        self.assertNotEqual(changes["classes"][0]["id"], "real-1")  # Cliente sigue siendo Cliente
        self.assertEqual(changes["classes"][0]["name"], "Producto")

    def test_an_answer_that_is_not_a_valid_change_is_an_error(self):
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=completion("no sé")):
            with self.assertRaises(AIProviderError):
                self.provider().change("haz algo", UML)

    def test_network_and_http_failures_become_a_clear_error_that_does_not_leak_the_address_or_the_key(self):
        failures = [requests.ConnectionError("http://puerta.local:8090 clave-secreta"), requests.Timeout("lento")]
        for failure in failures:
            with mock.patch("uml_api.services.ai_provider.requests.post", side_effect=failure):
                with self.assertRaises(AIProviderError) as raised:
                    self.provider().chat("hola")
            self.assertNotIn("puerta.local", str(raised.exception))
            self.assertNotIn("clave-secreta", str(raised.exception))

    def test_a_401_from_the_gateway_is_an_error(self):
        unauthorized = mock.Mock()
        unauthorized.raise_for_status.side_effect = requests.HTTPError("401")
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=unauthorized):
            with self.assertRaises(AIProviderError):
                self.provider().chat("hola")

    def test_an_empty_answer_is_an_error(self):
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=completion("   ")):
            with self.assertRaises(AIProviderError):
                self.provider().chat("hola")

    def test_reachable_asks_the_gateway_for_its_models_with_the_key(self):
        with mock.patch("uml_api.services.ai_provider.requests.get", return_value=mock.Mock(ok=True)) as get:
            self.assertTrue(self.provider().reachable())

        self.assertEqual(get.call_args.args[0], "http://puerta.local:8090/v1/models")
        self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer clave-secreta"})

    def test_reachable_is_false_when_nothing_answers(self):
        with mock.patch("uml_api.services.ai_provider.requests.get", side_effect=requests.ConnectionError()):
            self.assertFalse(self.provider().reachable())


class LocalEngineSelectionTests(SimpleTestCase):
    def setUp(self):
        ai_provider.forget_ollama_check()
        self.addCleanup(ai_provider.forget_ollama_check)

    def test_the_local_model_is_ollama_unless_the_engine_is_mlx(self):
        self.assertIsInstance(ai_provider.get_ai_provider("ollama"), OllamaProvider)
        with override_settings(LOCAL_ENGINE="mlx", LOCAL_AI_URL="http://x:1", LOCAL_AI_TOKEN="t"):
            provider = ai_provider.get_ai_provider("ollama")
        self.assertIsInstance(provider, LocalParallelProvider)
        self.assertEqual((provider.base_url, provider.token), ("http://x:1", "t"))

    def test_an_unknown_engine_falls_back_to_ollama(self):
        with override_settings(LOCAL_ENGINE="otro"):
            self.assertIsInstance(ai_provider.get_ai_provider("ollama"), OllamaProvider)

    def test_the_label_says_which_engine_answers(self):
        with override_settings(LOCAL_ENGINE="mlx"):
            self.assertIn("varios a la vez", ai_provider.describe_ai_provider("ollama")["label"])
        with override_settings(LOCAL_ENGINE="ollama", OLLAMA_MODEL="qwen3.5:9b", OLLAMA_CHANGE_MODEL=""):
            self.assertEqual(ai_provider.describe_ai_provider("ollama")["label"], "IA local (qwen3.5:9b)")

    def test_availability_of_the_local_model_follows_the_engine(self):
        with override_settings(LOCAL_ENGINE="mlx", LOCAL_AI_URL="http://puerta:8090", LOCAL_AI_TOKEN="t"), \
                mock.patch("uml_api.services.ai_provider.requests.get", return_value=mock.Mock(ok=True)) as get:
            options = ai_provider.provider_options()

        self.assertEqual(options[1], {"id": "ollama", "label": "Local (Qwen3-4B)", "available": True})
        self.assertEqual(get.call_args.args[0], "http://puerta:8090/v1/models")

    def test_without_a_tunnel_the_local_model_is_not_available(self):
        with override_settings(LOCAL_ENGINE="mlx", LOCAL_AI_URL="http://127.0.0.1:1"), \
                mock.patch("uml_api.services.ai_provider.requests.get", side_effect=requests.ConnectionError()):
            self.assertFalse(ai_provider.provider_options()[1]["available"])


class ConcurrencyTests(SimpleTestCase):
    def test_the_cloud_and_the_mlx_engine_attend_four_at_once_and_ollama_one(self):
        self.assertEqual(ai_provider.concurrency("gemini"), 4)
        with override_settings(LOCAL_ENGINE="ollama"):
            self.assertEqual(ai_provider.concurrency("ollama"), 1)
        with override_settings(LOCAL_ENGINE="mlx"):
            self.assertEqual(ai_provider.concurrency("ollama"), 4)

    def test_the_slots_can_be_configured_and_are_never_less_than_one(self):
        with override_settings(AI_CONCURRENCY_GEMINI=2, AI_CONCURRENCY_LOCAL=3, LOCAL_ENGINE="ollama"):
            self.assertEqual(ai_provider.concurrency("gemini"), 2)
            self.assertEqual(ai_provider.concurrency("ollama"), 3)
        with override_settings(AI_CONCURRENCY_GEMINI=-5):
            self.assertEqual(ai_provider.concurrency("gemini"), 1)

    def test_without_a_name_it_uses_the_servers_default_provider(self):
        with override_settings(AI_PROVIDER="ollama", LOCAL_ENGINE="ollama"):
            self.assertEqual(ai_provider.concurrency(), 1)
        with override_settings(AI_PROVIDER="gemini"):
            self.assertEqual(ai_provider.concurrency(), 4)
