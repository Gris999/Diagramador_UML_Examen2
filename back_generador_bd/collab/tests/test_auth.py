import time
from unittest import mock

from django.core import mail
from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from collab import auth
from collab.limits import InMemoryRateLimiter
from collab.room_state import InMemoryRoomState


class AuthTestBase(SimpleTestCase):
    def setUp(self):
        InMemoryRoomState.reset()
        InMemoryRateLimiter.reset()
        mail.outbox = []
        self.addCleanup(InMemoryRoomState.reset)
        self.addCleanup(InMemoryRateLimiter.reset)


class NormalizeEmailTests(SimpleTestCase):
    def test_a_normal_address_is_lowercased_and_trimmed(self):
        self.assertEqual(auth.normalize_email("  Ana.Perez+uagrm@Gmail.COM "), "ana.perez+uagrm@gmail.com")

    def test_things_that_are_not_an_address_are_refused(self):
        for value in (None, 12, "", "   ", "sin-arroba", "a@b", "a@@b.com", "a b@c.com", "a@b..com", "a@.com",
                      "a@b.com\nBcc: x@y.com", "a@b.com,c@d.com", "a@b.com;c@d.com", "<a@b.com>", "x" * 250 + "@b.com"):
            self.assertIsNone(auth.normalize_email(value), repr(value))


class DisplayNameTests(SimpleTestCase):
    def test_the_name_comes_from_the_local_part(self):
        self.assertEqual(auth.display_name_from_email("pedro.alaca@x.com"), "Pedro Alaca")
        self.assertEqual(auth.display_name_from_email("ana_maria-lopez+tag@x.com"), "Ana Maria Lopez")

    def test_a_long_or_empty_part_still_gives_a_usable_name(self):
        self.assertEqual(len(auth.display_name_from_email("x" * 60 + "@b.com")), 40)
        self.assertEqual(auth.display_name_from_email("...@b.com"), "Usuario")


class CodeTests(AuthTestBase):
    def test_a_code_has_six_digits_and_is_stored_only_as_a_hash(self):
        code = auth.issue_code("ana@x.com")

        self.assertRegex(code, r"^\d{6}$")
        stored = InMemoryRoomState().get("login-code:ana@x.com")
        self.assertNotIn(code, str(stored))

    def test_the_right_code_works_once(self):
        code = auth.issue_code("ana@x.com")

        self.assertTrue(auth.check_code("ana@x.com", code))
        self.assertFalse(auth.check_code("ana@x.com", code))

    def test_a_code_does_not_work_for_another_address(self):
        code = auth.issue_code("ana@x.com")

        self.assertFalse(auth.check_code("beto@x.com", code))
        self.assertTrue(auth.check_code("ana@x.com", code))

    def test_a_wrong_or_malformed_code_is_refused(self):
        code = auth.issue_code("ana@x.com")
        wrong = "000000" if code != "000000" else "111111"

        for attempt in (wrong, "12345", "1234567", "abcdef", "", None, 123456):
            self.assertFalse(auth.check_code("ana@x.com", attempt), repr(attempt))

    def test_after_five_mistakes_not_even_the_right_code_works(self):
        code = auth.issue_code("ana@x.com")
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(auth.MAX_CODE_ATTEMPTS):
            self.assertFalse(auth.check_code("ana@x.com", wrong))

        self.assertFalse(auth.check_code("ana@x.com", code))

    def test_a_new_code_replaces_the_old_one(self):
        first = auth.issue_code("ana@x.com")
        second = auth.issue_code("ana@x.com")

        if first != second:
            self.assertFalse(auth.check_code("ana@x.com", first))
        self.assertTrue(auth.check_code("ana@x.com", second))

    def test_there_is_nothing_to_check_without_a_code(self):
        self.assertFalse(auth.check_code("ana@x.com", "123456"))

    def test_a_stored_entry_with_an_unexpected_shape_is_ignored(self):
        InMemoryRoomState().set("login-code:ana@x.com", "raro", 60)
        InMemoryRoomState().set("login-code:beto@x.com", {"h": 5}, 60)

        self.assertFalse(auth.check_code("ana@x.com", "123456"))
        self.assertFalse(auth.check_code("beto@x.com", "123456"))


class SessionTests(SimpleTestCase):
    def test_a_session_gives_back_the_address_it_was_made_for(self):
        self.assertEqual(auth.read_session(auth.make_session("ana@x.com")), "ana@x.com")

    def test_a_tampered_or_foreign_session_is_refused(self):
        token = auth.make_session("ana@x.com")

        for value in (token + "x", "x" + token, "", None, 5, "a" * 2000, "abc:def:ghi"):
            self.assertIsNone(auth.read_session(value), repr(value))

    def test_a_session_signed_with_another_key_is_refused(self):
        token = auth.make_session("ana@x.com")

        with override_settings(SECRET_KEY="otra-clave"):
            self.assertIsNone(auth.read_session(token))

    def test_a_session_expires(self):
        token = auth.make_session("ana@x.com")

        with mock.patch("django.core.signing.time.time", return_value=time.time() + 31 * 86400):
            self.assertIsNone(auth.read_session(token))
        with mock.patch("django.core.signing.time.time", return_value=time.time() + 29 * 86400):
            self.assertEqual(auth.read_session(token), "ana@x.com")

    def test_the_header_must_be_a_bearer_session(self):
        token = auth.make_session("ana@x.com")

        self.assertEqual(auth.session_from_header(f"Bearer {token}"), "ana@x.com")
        self.assertEqual(auth.session_from_header(f"bearer {token}"), "ana@x.com")
        for value in (token, f"Basic {token}", "Bearer ", "", None):
            self.assertIsNone(auth.session_from_header(value), repr(value))


class MiddlewareTests(SimpleTestCase):
    def call(self, path, header=None, method="get"):
        factory = RequestFactory()
        extra = {"HTTP_AUTHORIZATION": header} if header else {}
        request = getattr(factory, method)(path, **extra)
        seen = {}

        def view(req):
            seen["email"] = req.auth_email
            return JsonResponse({"ok": True})

        response = auth.EmailSessionMiddleware(view)(request)
        return response, seen

    @override_settings(AUTH_REQUIRED=False)
    def test_without_the_switch_nothing_is_required_but_a_valid_session_is_still_read(self):
        response, seen = self.call("/api/ia/provider/")
        self.assertEqual((response.status_code, seen["email"]), (200, None))

        response, seen = self.call("/api/ia/provider/", f"Bearer {auth.make_session('ana@x.com')}")
        self.assertEqual((response.status_code, seen["email"]), (200, "ana@x.com"))

    @override_settings(AUTH_REQUIRED=True)
    def test_with_the_switch_the_api_needs_a_session(self):
        response, seen = self.call("/api/ia/provider/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(seen, {})

        response, seen = self.call("/api/ia/provider/", "Bearer inventada")
        self.assertEqual(response.status_code, 401)

        response, seen = self.call("/api/ia/provider/", f"Bearer {auth.make_session('ana@x.com')}")
        self.assertEqual((response.status_code, seen["email"]), (200, "ana@x.com"))

    @override_settings(AUTH_REQUIRED=True)
    def test_the_routes_to_get_a_session_stay_open(self):
        for path in ("/api/auth/config/", "/api/auth/code/", "/api/auth/verify/"):
            response, _ = self.call(path, method="post")
            self.assertEqual(response.status_code, 200, path)

    @override_settings(AUTH_REQUIRED=True)
    def test_the_rest_of_the_site_and_the_preflight_are_not_touched(self):
        response, _ = self.call("/")
        self.assertEqual(response.status_code, 200)
        response, _ = self.call("/api/ia/provider/", method="options")
        self.assertEqual(response.status_code, 200)

    @override_settings(AUTH_REQUIRED=True)
    def test_a_path_that_only_looks_like_the_open_prefix_is_still_protected(self):
        for path in ("/api/authentic/", "/api/x/api/auth/"):
            response, _ = self.call(path)
            self.assertEqual(response.status_code, 401, path)


class AllowTests(AuthTestBase):
    def test_it_counts_and_refuses_after_the_limit(self):
        results = [auth.allow("k", 3, 60) for _ in range(5)]

        self.assertEqual(results, [True, True, True, False, False])

    def test_if_the_counter_fails_it_refuses(self):
        with mock.patch("collab.auth.get_rate_limiter", side_effect=ConnectionError("redis")):
            self.assertFalse(auth.allow("k", 3, 60))


class ClientIpTests(SimpleTestCase):
    def test_it_prefers_what_the_proxy_wrote_last(self):
        request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(auth.client_ip(request), "2.2.2.2")

    def test_without_a_proxy_it_uses_the_connection(self):
        self.assertEqual(auth.client_ip(RequestFactory().get("/", REMOTE_ADDR="3.3.3.3")), "3.3.3.3")


class MailTests(AuthTestBase):
    def test_the_code_email_carries_the_code_and_goes_only_to_that_address(self):
        auth.send_code_email("ana@x.com", "123456")

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["ana@x.com"])
        self.assertIn("123456", message.body)
        self.assertIn("123456", message.subject)

    @override_settings(PUBLIC_APP_URL="https://diagramador.dev", AUTH_REQUIRED=True)
    def test_an_invitation_has_the_link_of_the_room_the_sender_and_a_reply_address(self):
        sent, failed = auth.send_invitations(
            sender_name="Ana", sender_email="ana@x.com", room="sala-1", recipients=["beto@x.com", "luis@x.com"], message="¡Ven!"
        )

        self.assertEqual((sent, failed), (["beto@x.com", "luis@x.com"], []))
        self.assertEqual([m.to for m in mail.outbox], [["beto@x.com"], ["luis@x.com"]])
        message = mail.outbox[0]
        self.assertIn("https://diagramador.dev/diagram/sala-1", message.body)
        self.assertIn("Ana te invitó", message.subject)
        self.assertIn("Mensaje de Ana: ¡Ven!", message.body)
        self.assertIn("mismo correo", message.body)
        self.assertIn("modo lectura", message.body)
        self.assertEqual(message.reply_to, ["ana@x.com"])

    @override_settings(AUTH_REQUIRED=False)
    def test_without_login_the_invitation_does_not_talk_about_a_code(self):
        auth.send_invitations(sender_name="Ana", sender_email=None, room="s", recipients=["b@x.com"], message="")

        self.assertNotIn("código", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].reply_to, [])

    def test_one_address_that_fails_does_not_stop_the_others(self):
        real_send = mail.EmailMessage.send

        def flaky(message, fail_silently=False):
            if message.to == ["malo@x.com"]:
                raise OSError("rechazado")
            return real_send(message, fail_silently)

        with mock.patch.object(mail.EmailMessage, "send", flaky):
            sent, failed = auth.send_invitations(
                sender_name="Ana", sender_email=None, room="s", recipients=["malo@x.com", "bueno@x.com"], message=""
            )

        self.assertEqual((sent, failed), (["bueno@x.com"], ["malo@x.com"]))

    def test_the_sender_name_cannot_inject_headers(self):
        auth.send_invitations(sender_name="Ana\nBcc: x@y.com", sender_email=None, room="s", recipients=["b@x.com"], message="")

        self.assertNotIn("\n", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].bcc, [])

    def test_a_message_with_a_link_is_refused_and_a_plain_one_is_not(self):
        for text in ("mira http://malo.com", "ve a www.malo.com", "x://y"):
            self.assertIsNotNone(auth.invitation_problem(text), text)
        self.assertIsNone(auth.invitation_problem("Ven a trabajar en el modelo"))
        self.assertIsNone(auth.invitation_problem(""))

    def test_clean_line_drops_control_characters_and_cuts_the_length(self):
        self.assertEqual(auth.clean_line("a\x00b\n c", 10), "ab c")
        self.assertEqual(len(auth.clean_line("x" * 500, 300)), 300)
        self.assertEqual(auth.clean_line(None, 10), "")


class MailConfiguredTests(SimpleTestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="", EMAIL_HOST_PASSWORD="")
    def test_smtp_without_server_or_key_is_not_configured(self):
        self.assertFalse(auth.mail_configured())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="smtp.resend.com", EMAIL_HOST_PASSWORD="re_x")
    def test_smtp_with_server_and_key_is_configured(self):
        self.assertTrue(auth.mail_configured())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_a_backend_that_does_not_leave_the_machine_counts_as_configured(self):
        self.assertTrue(auth.mail_configured())
