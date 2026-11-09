import re
import uuid

from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from collab import auth
from collab.limits import InMemoryRateLimiter
from collab.models import Participant
from collab.room_state import InMemoryRoomState


class AuthApiBase(APITestCase):
    def setUp(self):
        InMemoryRoomState.reset()
        InMemoryRateLimiter.reset()
        mail.outbox = []
        self.addCleanup(InMemoryRoomState.reset)
        self.addCleanup(InMemoryRateLimiter.reset)

    def request_code(self, email="ana@x.com", **extra):
        return self.client.post("/api/auth/code/", {"email": email}, format="json", **extra)

    def last_code(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def verify(self, email, code, **extra):
        return self.client.post("/api/auth/verify/", {"email": email, "code": code}, format="json", **extra)


class AuthConfigApiTests(AuthApiBase):
    @override_settings(AUTH_REQUIRED=True)
    def test_it_tells_whether_login_is_required_and_whether_mail_can_be_sent(self):
        data = self.client.get("/api/auth/config/").data

        self.assertEqual(data, {"authRequired": True, "mailConfigured": True})

    @override_settings(AUTH_REQUIRED=False, EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="", EMAIL_HOST_PASSWORD="")
    def test_it_says_when_nothing_is_required_and_mail_is_not_set_up(self):
        data = self.client.get("/api/auth/config/").data

        self.assertEqual(data, {"authRequired": False, "mailConfigured": False})

    @override_settings(AUTH_REQUIRED=True)
    def test_it_is_public_even_when_login_is_required(self):
        self.assertEqual(self.client.get("/api/auth/config/").status_code, 200)


class RequestCodeApiTests(AuthApiBase):
    def test_a_code_is_mailed_to_the_address(self):
        response = self.request_code("Ana@X.com")

        self.assertEqual((response.status_code, response.data), (200, {"sent": True}))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana@x.com"])
        self.assertRegex(mail.outbox[0].body, r"\b\d{6}\b")

    def test_the_code_is_never_in_the_response(self):
        response = self.request_code()

        self.assertNotIn(self.last_code(), str(response.data))

    def test_a_bad_address_is_refused_and_nothing_is_sent(self):
        for email in ("", "nada", "a@b", None, 5, "a@b.com\nBcc: x@y.com"):
            response = self.request_code(email)
            self.assertEqual(response.status_code, 400, repr(email))
        self.assertEqual(mail.outbox, [])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="", EMAIL_HOST_PASSWORD="")
    def test_without_a_mail_server_it_says_so(self):
        response = self.request_code()

        self.assertEqual(response.status_code, 503)
        self.assertIn("no puede enviar correos", response.data["error"])

    def test_the_same_address_cannot_ask_for_codes_without_end(self):
        results = [self.request_code("ana@x.com").status_code for _ in range(5)]

        self.assertEqual(results[:3], [200, 200, 200])
        self.assertEqual(results[3:], [429, 429])
        self.assertEqual(len(mail.outbox), 3)

    def test_one_place_cannot_flood_many_addresses(self):
        results = [self.request_code(f"p{n}@x.com", REMOTE_ADDR="9.9.9.9").status_code for n in range(12)]

        self.assertEqual(results[:10], [200] * 10)
        self.assertEqual(results[10:], [429, 429])

    def test_the_whole_service_has_a_ceiling_too(self):
        results = [self.request_code(f"p{n}@x.com", REMOTE_ADDR=f"10.0.0.{n}").status_code for n in range(62)]

        self.assertEqual(results.count(200), 60)
        self.assertEqual(results[60:], [429, 429])

    def test_if_the_mail_fails_the_person_is_told_to_try_again(self):
        from unittest import mock

        with mock.patch("collab.auth.send_code_email", side_effect=OSError("smtp caído")):
            response = self.request_code()

        self.assertEqual(response.status_code, 502)
        self.assertIn("Intenta de nuevo", response.data["error"])


class VerifyApiTests(AuthApiBase):
    def test_the_right_code_gives_a_session_for_that_address(self):
        self.request_code("ana.perez@x.com")

        response = self.verify("ana.perez@x.com", self.last_code())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "ana.perez@x.com")
        self.assertEqual(response.data["name"], "Ana Perez")
        self.assertEqual(auth.read_session(response.data["token"]), "ana.perez@x.com")

    def test_the_session_then_opens_the_api_when_login_is_required(self):
        self.request_code()
        token = self.verify("ana@x.com", self.last_code()).data["token"]

        with override_settings(AUTH_REQUIRED=True):
            without = self.client.get("/api/ia/provider/")
            with_session = self.client.get("/api/ia/provider/", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual((without.status_code, with_session.status_code), (401, 200))

    def test_a_wrong_code_gives_nothing(self):
        self.request_code()
        wrong = "000000" if self.last_code() != "000000" else "111111"

        response = self.verify("ana@x.com", wrong)

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("token", response.data)
        self.assertIn("no es válido", response.data["error"])

    def test_the_code_works_only_once(self):
        self.request_code()
        code = self.last_code()

        self.assertEqual(self.verify("ana@x.com", code).status_code, 200)
        self.assertEqual(self.verify("ana@x.com", code).status_code, 400)

    def test_a_code_for_one_address_does_not_open_another(self):
        self.request_code("ana@x.com")

        self.assertEqual(self.verify("beto@x.com", self.last_code()).status_code, 400)

    def test_guessing_is_stopped_after_five_mistakes(self):
        self.request_code()
        code = self.last_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.verify("ana@x.com", wrong)

        self.assertEqual(self.verify("ana@x.com", code).status_code, 400)

    def test_asking_for_a_new_code_gives_a_fresh_chance(self):
        self.request_code()
        wrong = "000000" if self.last_code() != "000000" else "111111"
        for _ in range(5):
            self.verify("ana@x.com", wrong)

        self.request_code()

        self.assertEqual(self.verify("ana@x.com", self.last_code()).status_code, 200)

    def test_a_bad_address_or_code_shape_is_refused(self):
        self.assertEqual(self.verify("nada", "123456").status_code, 400)
        self.assertEqual(self.verify("ana@x.com", "12").status_code, 400)
        self.assertEqual(self.verify("ana@x.com", None).status_code, 400)

    def test_one_place_cannot_try_codes_without_end(self):
        results = [self.verify(f"p{n}@x.com", "123456", REMOTE_ADDR="8.8.8.8").status_code for n in range(32)]

        self.assertEqual(results.count(429), 2)


class MeApiTests(AuthApiBase):
    def test_it_says_who_the_session_belongs_to(self):
        token = auth.make_session("ana.perez@x.com")

        response = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.data, {"email": "ana.perez@x.com", "name": "Ana Perez"})

    def test_without_a_valid_session_it_is_401(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me/", HTTP_AUTHORIZATION="Bearer mala").status_code, 401)


class InviteApiTests(AuthApiBase):
    room = "sala-inv"

    def setUp(self):
        super().setUp()
        self.ana = Participant.objects.create(room=self.room, token=uuid.uuid4(), display_name="Ana")

    def invite(self, emails, message="", participant=None, session=None, room=None):
        headers = {"HTTP_X_PARTICIPANT_TOKEN": str((participant or self.ana).token)}
        if session:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {session}"
        return self.client.post(
            f"/api/rooms/{room or self.room}/invite/", {"emails": emails, "message": message}, format="json", **headers
        )

    def test_it_mails_the_link_of_the_room_to_each_address(self):
        response = self.invite(["beto@x.com", "Luis@X.com"], "Ven a modelar")

        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.data["sent"], response.data["failed"]), (["beto@x.com", "luis@x.com"], []))
        self.assertEqual([m.to for m in mail.outbox], [["beto@x.com"], ["luis@x.com"]])
        self.assertIn(f"/diagram/{self.room}", mail.outbox[0].body)
        self.assertIn("Ana te invitó", mail.outbox[0].subject)
        self.assertIn("Ven a modelar", mail.outbox[0].body)

    def test_replies_go_to_the_person_who_invited_when_they_are_logged_in(self):
        token = auth.make_session("ana@x.com")

        self.invite(["beto@x.com"], session=token)

        self.assertEqual(mail.outbox[0].reply_to, ["ana@x.com"])

    def test_only_someone_in_the_room_can_invite(self):
        stranger = Participant(room=self.room, token=uuid.uuid4(), display_name="X")

        self.assertEqual(self.invite(["beto@x.com"], participant=stranger).status_code, 403)
        self.assertEqual(self.client.post(f"/api/rooms/{self.room}/invite/", {"emails": ["b@x.com"]}, format="json").status_code, 403)
        self.assertEqual(mail.outbox, [])

    @override_settings(AUTH_REQUIRED=True)
    def test_when_login_is_required_the_invitation_needs_a_session_too(self):
        auth.room_access(self.room, "ana@x.com", claim=True)

        self.assertEqual(self.invite(["beto@x.com"]).status_code, 401)
        self.assertEqual(self.invite(["beto@x.com"], session=auth.make_session("ana@x.com")).status_code, 200)

    def test_repeated_addresses_get_one_mail(self):
        response = self.invite(["beto@x.com", "BETO@x.com", "beto@x.com"])

        self.assertEqual(response.data["sent"], ["beto@x.com"])
        self.assertEqual(len(mail.outbox), 1)

    def test_a_bad_list_is_refused_whole(self):
        for emails in ([], None, "beto@x.com", ["beto@x.com", "mal"], ["a@b.com\nBcc: x@y.com"], [5]):
            self.assertEqual(self.invite(emails).status_code, 400, repr(emails))
        self.assertEqual(mail.outbox, [])

    def test_there_is_a_limit_of_people_per_invitation(self):
        too_many = [f"p{n}@x.com" for n in range(auth.MAX_RECIPIENTS + 1)]

        self.assertEqual(self.invite(too_many).status_code, 400)
        self.assertEqual(self.invite(too_many[: auth.MAX_RECIPIENTS]).status_code, 200)

    def test_a_message_with_a_link_is_refused(self):
        response = self.invite(["beto@x.com"], "entra a http://malo.com")

        self.assertEqual(response.status_code, 400)
        self.assertIn("enlaces", response.data["error"])
        self.assertEqual(mail.outbox, [])

    def test_a_very_long_message_is_cut(self):
        self.invite(["beto@x.com"], "a" * 1000)

        self.assertNotIn("a" * 301, mail.outbox[0].body)

    def test_a_person_cannot_send_without_end(self):
        results = [self.invite([f"p{n}@x.com"]).status_code for n in range(22)]

        self.assertEqual(results[:20], [200] * 20)
        self.assertEqual(results[20:], [429, 429])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="", EMAIL_HOST_PASSWORD="")
    def test_without_a_mail_server_it_says_so_and_the_interface_can_offer_the_mail_app(self):
        response = self.invite(["beto@x.com"])

        self.assertEqual(response.status_code, 503)

    def test_if_every_mail_fails_it_is_a_gateway_error_that_lists_them(self):
        from unittest import mock

        with mock.patch("collab.auth.send_invitations", return_value=([], ["beto@x.com"])):
            response = self.invite(["beto@x.com"])

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["failed"], ["beto@x.com"])

    def test_if_some_fail_the_others_still_count(self):
        from unittest import mock

        with mock.patch("collab.auth.send_invitations", return_value=(["a@x.com"], ["b@x.com"])):
            response = self.invite(["a@x.com", "b@x.com"])

        self.assertEqual((response.status_code, response.data["sent"], response.data["failed"]), (200, ["a@x.com"], ["b@x.com"]))


class RoomAccessApiTests(AuthApiBase):
    """Con el interruptor prendido, a una sala solo entran el propietario y quienes invitó alguien de la sala."""

    room = "sala-acc"

    def setUp(self):
        super().setUp()
        self.ana = Participant.objects.create(room=self.room, token=uuid.uuid4(), display_name="Ana")

    def session(self, email):
        return {"HTTP_AUTHORIZATION": f"Bearer {auth.make_session(email)}"}

    def enter(self, email, method="post", room=None):
        return getattr(self.client, method)(f"/api/rooms/{room or self.room}/access/", **self.session(email))

    def invite(self, as_email, emails, message=""):
        return self.client.post(
            f"/api/rooms/{self.room}/invite/", {"emails": emails, "message": message}, format="json",
            HTTP_X_PARTICIPANT_TOKEN=str(self.ana.token), **self.session(as_email),
        )

    @override_settings(AUTH_REQUIRED=False)
    def test_without_the_switch_there_is_no_access_control_and_it_says_so(self):
        response = self.client.post(f"/api/rooms/{self.room}/access/")

        self.assertEqual((response.status_code, response.data["required"], response.data["members"]), (200, False, []))

    @override_settings(AUTH_REQUIRED=True)
    def test_it_needs_a_session(self):
        self.assertEqual(self.client.post(f"/api/rooms/{self.room}/access/").status_code, 401)

    @override_settings(AUTH_REQUIRED=True)
    def test_the_first_person_to_enter_becomes_the_owner(self):
        response = self.enter("ana@x.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.data["role"], response.data["email"]), ("owner", "ana@x.com"))
        self.assertEqual(response.data["members"], [{"email": "ana@x.com", "role": "owner"}])

    @override_settings(AUTH_REQUIRED=True)
    def test_somebody_who_was_not_invited_is_told_so_and_with_which_address(self):
        self.enter("ana@x.com")

        response = self.enter("beto@x.com")

        self.assertEqual(response.status_code, 403)
        self.assertEqual((response.data["code"], response.data["email"]), ("not_invited", "beto@x.com"))
        self.assertEqual(self.enter("ana@x.com", "get").data["members"], [{"email": "ana@x.com", "role": "owner"}])

    @override_settings(AUTH_REQUIRED=True)
    def test_only_entering_claims_a_room_looking_at_it_does_not(self):
        self.assertEqual(self.enter("ana@x.com", "get").status_code, 403)
        self.assertEqual(self.enter("beto@x.com").status_code, 200)

    @override_settings(AUTH_REQUIRED=True)
    def test_an_invitation_gives_access_to_that_address_and_the_answer_lists_everyone(self):
        self.enter("ana@x.com")

        response = self.invite("ana@x.com", ["beto@x.com", "luis@x.com"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual([m["email"] for m in response.data["members"]], ["ana@x.com", "beto@x.com", "luis@x.com"])
        self.assertEqual(self.enter("beto@x.com").data["role"], "invited")
        self.assertEqual(self.enter("luis@x.com").status_code, 200)

    @override_settings(AUTH_REQUIRED=True)
    def test_the_link_alone_is_not_enough_only_the_invited_address_enters(self):
        self.enter("ana@x.com")
        self.invite("ana@x.com", ["beto@x.com"])

        self.assertEqual(self.enter("beto@x.com").status_code, 200)
        self.assertEqual(self.enter("otro@x.com").status_code, 403)

    @override_settings(AUTH_REQUIRED=True)
    def test_someone_who_was_not_invited_cannot_invite_others(self):
        self.enter("ana@x.com")

        response = self.invite("intruso@x.com", ["amigo@x.com"])

        self.assertEqual(response.status_code, 403)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(self.enter("amigo@x.com").status_code, 403)

    @override_settings(AUTH_REQUIRED=True)
    def test_an_invited_person_can_invite_more_people(self):
        self.enter("ana@x.com")
        self.invite("ana@x.com", ["beto@x.com"])

        self.assertEqual(self.invite("beto@x.com", ["luis@x.com"]).status_code, 200)
        self.assertEqual(self.enter("luis@x.com").status_code, 200)

    @override_settings(AUTH_REQUIRED=True)
    def test_an_address_whose_mail_did_not_go_does_not_keep_the_access(self):
        from unittest import mock

        self.enter("ana@x.com")
        with mock.patch("collab.auth.send_invitations", return_value=(["ok@x.com"], ["malo@x.com"])):
            response = self.invite("ana@x.com", ["ok@x.com", "malo@x.com"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual([m["email"] for m in response.data["members"]], ["ana@x.com", "ok@x.com"])
        self.assertEqual(self.enter("malo@x.com").status_code, 403)

    @override_settings(AUTH_REQUIRED=True)
    def test_if_no_mail_goes_nobody_new_gets_access(self):
        from unittest import mock

        self.enter("ana@x.com")
        with mock.patch("collab.auth.send_invitations", return_value=([], ["a@x.com", "b@x.com"])):
            response = self.invite("ana@x.com", ["a@x.com", "b@x.com"])

        self.assertEqual(response.status_code, 502)
        self.assertEqual([m["email"] for m in response.data["members"]], ["ana@x.com"])

    @override_settings(AUTH_REQUIRED=True)
    def test_inviting_again_someone_who_was_already_in_does_not_demote_the_owner(self):
        self.enter("ana@x.com")

        self.invite("ana@x.com", ["ana@x.com", "beto@x.com"])

        self.assertEqual(self.enter("ana@x.com", "get").data["role"], "owner")

    @override_settings(AUTH_REQUIRED=True)
    def test_the_backups_and_the_chat_of_a_room_follow_the_same_list(self):
        room = "3f2c1b7e-9a4d-4c55-8e21-0b6f7d9a1c42"
        self.enter("ana@x.com", room=room)

        mine = self.client.get(f"/api/get_backup_uml/{room}/", **self.session("ana@x.com"))
        other = self.client.get(f"/api/get_backup_uml/{room}/", **self.session("beto@x.com"))

        self.assertNotEqual(mine.status_code, 403)
        self.assertEqual(other.status_code, 403)

    @override_settings(AUTH_REQUIRED=False)
    def test_without_the_switch_inviting_does_not_create_a_list(self):
        response = self.client.post(
            f"/api/rooms/{self.room}/invite/", {"emails": ["beto@x.com"]}, format="json", HTTP_X_PARTICIPANT_TOKEN=str(self.ana.token)
        )

        self.assertEqual((response.status_code, response.data["members"]), (200, []))
        from collab.models import RoomMember
        self.assertEqual(RoomMember.objects.count(), 0)

