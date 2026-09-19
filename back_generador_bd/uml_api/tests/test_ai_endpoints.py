import json
from io import BytesIO
from unittest.mock import Mock, patch

import requests
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from uml_api.services.services_gemini import _post_gemini, call_gemini


class GeminiTransportTests(SimpleTestCase):
    @patch("uml_api.services.services_gemini.time.sleep")
    @patch("uml_api.services.services_gemini.requests.post")
    @override_settings(GEMINI_MODEL="primary-model")
    def test_primary_503_uses_fallback_model(self, post, sleep):
        unavailable = Mock(status_code=503)
        unavailable.raise_for_status.side_effect = requests.HTTPError(
            response=unavailable
        )
        success = Mock(status_code=200)
        success.raise_for_status.return_value = None
        post.side_effect = [unavailable, unavailable, unavailable, success]

        response = _post_gemini({}, {}, {}, max_attempts=3)

        self.assertIs(response, success)
        self.assertIn("primary-model", post.call_args_list[0].args[0])
        self.assertIn("gemini-3.5-flash-lite", post.call_args_list[-1].args[0])
        self.assertEqual(sleep.call_count, 2)

    @patch("uml_api.services.services_gemini.time.sleep")
    @patch("uml_api.services.services_gemini.requests.post")
    @override_settings(GEMINI_MODEL="primary-model")
    def test_400_is_not_retried(self, post, sleep):
        invalid_request = Mock(status_code=400)
        invalid_request.raise_for_status.side_effect = requests.HTTPError(
            response=invalid_request
        )
        post.return_value = invalid_request

        with self.assertRaises(requests.HTTPError):
            _post_gemini({}, {}, {}, max_attempts=3)

        post.assert_called_once()
        sleep.assert_not_called()

    @patch("uml_api.services.services_gemini.requests.post")
    @override_settings(GEMINI_API_KEY="change-me")
    def test_invalid_api_key_fails_before_network_call(self, post):
        with self.assertRaises(RuntimeError):
            call_gemini("crear una clase")

        post.assert_not_called()

    @patch("uml_api.services.services_gemini._post_gemini")
    @override_settings(GEMINI_API_KEY="test-key")
    def test_current_uml_is_sent_as_edit_context(self, post_gemini):
        response = Mock()
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "{}"}]}}]
        }
        post_gemini.return_value = response
        current_uml = {"classes": [{"id": "customer-id", "name": "Customer"}]}

        call_gemini("edita Customer y añade email", current_uml=current_uml)

        prompt = post_gemini.call_args.args[0]["contents"][0]["parts"][0]["text"]
        self.assertIn("DIAGRAMA UML ACTUAL", prompt)
        self.assertIn("customer-id", prompt)


class AIEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("uml_api.views.call_gemini", return_value='{"classes": [], "relationships": []}')
    def test_generate_uml_success_passes_current_uml(self, call):
        current_uml = {"classes": [{"id": "existing", "name": "Existing"}]}

        response = self.client.post(
            "/api/chatbot/",
            {"prompt": "edita Existing", "uml": current_uml},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        call.assert_called_once_with("edita Existing", current_uml=current_uml)

    @patch("uml_api.views.call_gemini", side_effect=RuntimeError("private details"))
    def test_generate_uml_service_error_is_sanitized_502(self, call):
        response = self.client.post(
            "/api/chatbot/", {"prompt": "crear clase"}, format="json"
        )

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private details", response.data["error"])

    @patch("uml_api.views.call_gemini_from_image", side_effect=RuntimeError("private details"))
    def test_image_service_error_is_sanitized_502(self, image_service):
        image = BytesIO(b"png data")
        image.name = "diagram.png"

        response = self.client.post(
            "/api/uml_from_image/", {"image": image}, format="multipart"
        )

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private details", response.data["error"])

    def test_audio_is_required(self):
        response = self.client.post("/api/uml_from_audio/", {}, format="multipart")

        self.assertEqual(response.status_code, 400)

    @patch("uml_api.views.call_gemini", return_value='{"classes": [], "relationships": []}')
    @patch("uml_api.views.call_gemini_transcribe_audio", return_value="agrega una clase")
    def test_valid_audio_returns_uml(self, transcribe, generate):
        audio = SimpleUploadedFile(
            "instruction.webm", b"audio data", content_type="audio/webm"
        )
        current_uml = {"classes": [{"id": "existing", "name": "Existing"}]}

        response = self.client.post(
            "/api/uml_from_audio/",
            {"audio": audio, "uml": json.dumps(current_uml)},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        generate.assert_called_once_with("agrega una clase", current_uml=current_uml)

    @patch("uml_api.views.call_gemini_transcribe_audio", side_effect=RuntimeError("private details"))
    def test_audio_service_error_is_sanitized_502(self, transcribe):
        audio = SimpleUploadedFile(
            "instruction.webm", b"audio data", content_type="audio/webm"
        )

        response = self.client.post(
            "/api/uml_from_audio/", {"audio": audio}, format="multipart"
        )

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private details", response.data["error"])
