import importlib.util
import json
from pathlib import Path
from unittest import mock, skipUnless

from django.test import SimpleTestCase, override_settings

from uml_api.services import modelo_reentrenado as modelo
from uml_api.services.ai_provider import AIProviderError, OllamaProvider, _parse_changes, describe_ai_provider

FORMATO = Path(__file__).resolve().parents[3] / "ml" / "data" / "formato.py"

REAL = {
    "classes": [
        {
            "id": "7f3a9c1e-0000-4000-8000-000000000001",
            "name": "Cliente",
            "attributes": [{"name": "id", "type": "int"}, {"name": "nombre", "type": "string"}],
            "methods": [{"name": "comprar", "parameters": "p: Producto", "returnType": "boolean"}],
            "position": {"x": 10, "y": 20},
            "size": {"width": 200, "height": 100},
        },
        {
            "id": "7f3a9c1e-0000-4000-8000-000000000002",
            "name": "Pedido",
            "attributes": [{"name": "total", "type": "float"}],
            "methods": [],
            "position": {"x": 300, "y": 20},
        },
    ],
    "relationships": [
        {
            "id": "rel-uuid-1",
            "type": "association",
            "sourceId": "7f3a9c1e-0000-4000-8000-000000000001",
            "targetId": "7f3a9c1e-0000-4000-8000-000000000002",
            "labels": ["1", "0..*"],
        },
        {"id": "rel-uuid-2", "type": "association", "sourceId": "no-existe", "targetId": "otra"},
    ],
}


@skipUnless(FORMATO.exists(), "la carpeta ml/ no está en este entorno (p. ej. dentro del contenedor)")
class MismoFormatoQueElEntrenamientoTests(SimpleTestCase):
    def test_the_system_prompt_is_identical_to_the_one_the_model_was_trained_with(self):
        spec = importlib.util.spec_from_file_location("formato_entrenamiento", FORMATO)
        entrenamiento = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entrenamiento)

        self.assertEqual(modelo.SISTEMA, entrenamiento.SISTEMA)

    def test_the_conversation_is_identical_to_the_training_one(self):
        spec = importlib.util.spec_from_file_location("formato_entrenamiento", FORMATO)
        entrenamiento = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entrenamiento)
        compacto, _ = modelo.compactar(REAL)

        self.assertEqual(
            modelo.mensajes(compacto, "Agrega la clase Factura"),
            entrenamiento.conversacion(compacto, "Agrega la clase Factura"),
        )


class CompactarYRestaurarTests(SimpleTestCase):
    def test_the_model_only_sees_short_ids_and_what_it_was_trained_on(self):
        compacto, alias = modelo.compactar(REAL)

        self.assertEqual([c["id"] for c in compacto["classes"]], ["c1", "c2"])
        self.assertEqual(set(compacto["classes"][0]), {"id", "name", "attributes", "methods"})
        self.assertEqual(compacto["classes"][0]["methods"], [{"name": "comprar"}])
        self.assertEqual(alias["c1"], REAL["classes"][0]["id"])

    def test_relationships_use_short_ids_and_dangling_ones_are_left_out(self):
        compacto, _ = modelo.compactar(REAL)

        self.assertEqual(
            compacto["relationships"],
            [{"id": "r1", "type": "association", "sourceId": "c1", "targetId": "c2"}],
        )

    def test_a_missing_or_malformed_diagram_is_an_empty_one(self):
        for uml in (None, "x", [], {"classes": "no"}, {"classes": [None, 3, {"name": "sin id"}]}):
            compacto, alias = modelo.compactar(uml)
            self.assertEqual(compacto, {"classes": [], "relationships": []})
            self.assertEqual(alias, {})

    def test_changes_go_back_to_the_real_ids(self):
        _, alias = modelo.compactar(REAL)
        cambios = {
            "classes": [{"id": "c2", "name": "Pedido", "eliminar": True}],
            "relationships": [{"id": "r1", "type": "association", "sourceId": "c1", "targetId": "c2", "eliminar": True}],
        }

        restaurado = modelo.restaurar(cambios, alias, REAL)

        self.assertEqual(restaurado["classes"][0]["id"], REAL["classes"][1]["id"])
        self.assertEqual(restaurado["relationships"][0]["id"], "rel-uuid-1")
        self.assertEqual(restaurado["relationships"][0]["sourceId"], REAL["classes"][0]["id"])
        self.assertEqual(restaurado["relationships"][0]["targetId"], REAL["classes"][1]["id"])

    def test_members_keep_the_data_the_model_never_saw(self):
        _, alias = modelo.compactar(REAL)
        cambios = {"classes": [{
            "id": "c1", "name": "Cliente",
            "attributes": [{"name": "id", "type": "int"}, {"name": "nombre", "type": "string"}, {"name": "email", "type": "string"}],
            "methods": [{"name": "comprar"}, {"name": "cancelar"}],
        }]}

        clase = modelo.restaurar(cambios, alias, REAL)["classes"][0]

        self.assertEqual(clase["methods"][0], {"name": "comprar", "parameters": "p: Producto", "returnType": "boolean"})
        self.assertEqual(clase["methods"][1], {"name": "cancelar"})
        self.assertEqual(len(clase["attributes"]), 3)

    def test_a_changed_type_wins_over_the_original_one(self):
        _, alias = modelo.compactar(REAL)
        cambios = {"classes": [{"id": "c2", "name": "Pedido", "attributes": [{"name": "total", "type": "decimal"}]}]}

        clase = modelo.restaurar(cambios, alias, REAL)["classes"][0]

        self.assertEqual(clase["attributes"], [{"name": "total", "type": "decimal"}])

    def test_the_name_of_an_existing_class_wins_over_a_wrong_id(self):
        # Caso real: el modelo devolvió «Pedido» con el id de Cliente; sin corregirlo, se renombraría Cliente.
        _, alias = modelo.compactar(REAL)
        cambios = {"classes": [{"id": "c1", "name": "Pedido", "attributes": [{"name": "total", "type": "decimal"}]}]}

        clase = modelo.restaurar(cambios, alias, REAL)["classes"][0]

        self.assertEqual(clase["id"], REAL["classes"][1]["id"])
        self.assertEqual(clase["name"], "Pedido")

    def test_renaming_a_class_keeps_its_id_because_the_new_name_does_not_exist_yet(self):
        _, alias = modelo.compactar(REAL)
        cambios = {"classes": [{"id": "c1", "name": "Zona", "attributes": [], "methods": []}]}

        clase = modelo.restaurar(cambios, alias, REAL)["classes"][0]

        self.assertEqual(clase["id"], REAL["classes"][0]["id"])

    def test_new_classes_keep_their_own_ids_and_the_input_is_not_modified(self):
        _, alias = modelo.compactar(REAL)
        cambios = {"classes": [{"id": "c9", "name": "Factura", "attributes": [], "methods": []}], "relationships": []}

        restaurado = modelo.restaurar(cambios, alias, REAL)

        self.assertEqual(restaurado["classes"][0]["id"], "c9")
        self.assertEqual(cambios["classes"][0]["id"], "c9")

    def test_the_empty_think_block_is_removed(self):
        self.assertEqual(modelo.quitar_razonamiento('<think>\n\n</think>\n\n{"a":1}'), '{"a":1}')
        self.assertEqual(modelo.quitar_razonamiento('{"a":1}'), '{"a":1}')


class OllamaConModeloReentrenadoTests(SimpleTestCase):
    def provider(self):
        return OllamaProvider(base_url="http://ollama.local:11434", model="qwen3.5:9b", change_model="uml-qwen-dia3")

    def respuesta(self, contenido):
        resp = mock.Mock()
        resp.json.return_value = {"message": {"content": contenido}}
        return resp

    def test_changes_use_the_retrained_model_with_the_short_prompt(self):
        contenido = '<think>\n\n</think>\n\n' + json.dumps({"classes": [{"id": "c1", "name": "Cliente", "eliminar": True}]})
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=self.respuesta(contenido)) as post:
            cambios = self.provider().change("Elimina la clase Cliente", REAL)

        url = post.call_args.args[0]
        cuerpo = post.call_args.kwargs["json"]
        self.assertTrue(url.endswith("/api/chat"))
        self.assertEqual(cuerpo["model"], "uml-qwen-dia3")
        self.assertIs(cuerpo["think"], False)
        self.assertEqual(cuerpo["messages"][0]["content"], modelo.SISTEMA)
        self.assertIn("PEDIDO: Elimina la clase Cliente", cuerpo["messages"][1]["content"])
        self.assertNotIn("7f3a9c1e", cuerpo["messages"][1]["content"])  # el modelo no ve ids largos
        self.assertEqual(cambios["classes"][0]["id"], REAL["classes"][0]["id"])

    def test_chat_and_review_keep_using_the_general_model(self):
        resp = mock.Mock()
        resp.json.return_value = {"response": "hola"}
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=resp) as post:
            self.provider().chat("¿qué hay?")

        self.assertTrue(post.call_args.args[0].endswith("/api/generate"))
        self.assertEqual(post.call_args.kwargs["json"]["model"], "qwen3.5:9b")

    def test_without_a_retrained_model_changes_use_the_long_prompt_as_before(self):
        resp = mock.Mock()
        resp.json.return_value = {"response": '{"classes": []}'}
        sin = OllamaProvider(base_url="http://ollama.local:11434", model="qwen3.5:9b", change_model="")
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=resp) as post:
            sin.change("Agrega la clase Factura", {"classes": []})

        self.assertTrue(post.call_args.args[0].endswith("/api/generate"))

    def test_an_unreachable_or_empty_retrained_model_is_a_clear_error(self):
        with mock.patch("uml_api.services.ai_provider.requests.post", side_effect=OSError("sin red")):
            with self.assertRaises(AIProviderError):
                self.provider().change("x", REAL)
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=self.respuesta("  ")):
            with self.assertRaises(AIProviderError):
                self.provider().change("x", REAL)
        with mock.patch("uml_api.services.ai_provider.requests.post", return_value=self.respuesta("no es json")):
            with self.assertRaises(AIProviderError):
                self.provider().change("x", REAL)

    def test_any_provider_ignores_a_think_block_before_the_json(self):
        self.assertEqual(_parse_changes('<think>\n\n</think>\n\n{"classes": []}'), {"classes": []})

    @override_settings(AI_PROVIDER="ollama", OLLAMA_MODEL="qwen3.5:9b", OLLAMA_CHANGE_MODEL="uml-qwen-dia3")
    def test_the_chat_label_says_which_model_makes_the_changes(self):
        etiqueta = describe_ai_provider()["label"]

        self.assertIn("qwen3.5:9b", etiqueta)
        self.assertIn("uml-qwen-dia3", etiqueta)
        self.assertIn("reentrenado", etiqueta)

    @override_settings(AI_PROVIDER="ollama", OLLAMA_MODEL="qwen3.5:9b", OLLAMA_CHANGE_MODEL="")
    def test_the_label_is_unchanged_without_a_retrained_model(self):
        self.assertEqual(describe_ai_provider()["label"], "IA local (qwen3.5:9b)")
