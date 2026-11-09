import re
import uuid

from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from collab import auth, rooms
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

        self.assertEqual(response.data["email"], "ana.perez@x.com")
        self.assertEqual(response.data["name"], "Ana Perez")

    def test_it_hands_back_a_fresh_session_for_the_same_address(self):
        old = auth.make_session("ana.perez@x.com")

        response = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {old}")

        self.assertEqual(auth.read_session(response.data["token"]), "ana.perez@x.com")

    def test_the_fresh_session_works_on_the_next_request(self):
        first = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {auth.make_session('ana.perez@x.com')}")

        second = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {first.data['token']}")

        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["email"], "ana.perez@x.com")

    def test_a_session_that_is_not_valid_gets_nothing_renewed(self):
        response = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION="Bearer eyJlbWFpbCI6ImFuYUB4LmNvbSJ9:1aaaaa:falsa")

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("token", response.data)

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
        rooms.enter(self.room, "ana@x.com", claim=True)

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
        self.assertEqual(response.data["members"], [{"email": "ana@x.com", "role": "owner", "source": "owner"}])

    @override_settings(AUTH_REQUIRED=True)
    def test_somebody_who_was_not_invited_is_told_so_and_with_which_address(self):
        self.enter("ana@x.com")

        response = self.enter("beto@x.com")

        self.assertEqual(response.status_code, 403)
        self.assertEqual((response.data["code"], response.data["email"]), ("not_invited", "beto@x.com"))
        self.assertEqual(self.enter("ana@x.com", "get").data["members"], [{"email": "ana@x.com", "role": "owner", "source": "owner"}])

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
        self.assertEqual(self.enter("beto@x.com").data["role"], "editor")
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


@override_settings(AUTH_REQUIRED=True)
class SharingApiTests(AuthApiBase):
    """«Compartir» como en Google Docs: roles, acceso general, nombre, borrado y la lista «Mis diagramas»."""

    room = "sala-share"

    def setUp(self):
        super().setUp()
        self.ana = Participant.objects.create(room=self.room, token=uuid.uuid4(), display_name="Ana")
        self.client.post(f"/api/rooms/{self.room}/access/", **self.session("ana@x.com"))

    def session(self, email):
        return {"HTTP_AUTHORIZATION": f"Bearer {auth.make_session(email)}"}

    def put(self, path, data, email="ana@x.com"):
        return self.client.put(f"/api/rooms/{self.room}/{path}", data, format="json", **self.session(email))

    def delete(self, path, data=None, email="ana@x.com"):
        return self.client.delete(f"/api/rooms/{self.room}/{path}", data, format="json", **self.session(email))

    def invite(self, emails, role=None, email="ana@x.com"):
        body = {"emails": emails}
        if role is not None:
            body["role"] = role
        return self.client.post(
            f"/api/rooms/{self.room}/invite/", body, format="json", HTTP_X_PARTICIPANT_TOKEN=str(self.ana.token), **self.session(email)
        )

    def enter(self, email):
        return self.client.post(f"/api/rooms/{self.room}/access/", **self.session(email))

    # ---- lo que dice la sala de sí misma
    def test_the_access_answer_says_who_you_are_the_name_the_general_access_and_who_is_in(self):
        self.put("settings/", {"title": "Mi modelo", "link_access": "anyone", "link_role": "editor"})

        data = self.enter("ana@x.com").data

        self.assertEqual((data["role"], data["is_owner"], data["can_edit"], data["title"]), ("owner", True, True, "Mi modelo"))
        self.assertEqual((data["link_access"], data["link_role"], data["owner"]), ("anyone", "editor", "ana@x.com"))

    # ---- invitar con rol
    def test_an_invitation_gives_the_chosen_role_and_editor_is_the_default(self):
        self.invite(["beto@x.com"])
        self.invite(["eva@x.com"], role="viewer")

        self.assertEqual(self.enter("beto@x.com").data["role"], "editor")
        viewer = self.enter("eva@x.com").data
        self.assertEqual((viewer["role"], viewer["can_edit"]), ("viewer", False))

    def test_an_invitation_with_another_role_is_refused(self):
        for role in ("owner", "admin", "", 3):
            self.assertEqual(self.invite(["beto@x.com"], role=role).status_code, 400, repr(role))
        self.assertEqual(mail.outbox, [])

    def test_the_email_says_it_is_read_only_when_the_role_is_viewer(self):
        self.invite(["eva@x.com"], role="viewer")
        self.invite(["beto@x.com"], role="editor")

        by_to = {m.to[0]: m.body for m in mail.outbox}
        self.assertIn("solo lectura", by_to["eva@x.com"])
        self.assertIn("trabajar en equipo", by_to["beto@x.com"])

    def test_a_viewer_cannot_invite_anyone(self):
        self.invite(["eva@x.com"], role="viewer")

        response = self.invite(["amigo@x.com"], email="eva@x.com")

        self.assertEqual((response.status_code, response.json()["code"]), (403, "read_only"))
        self.assertEqual(self.enter("amigo@x.com").status_code, 403)

    # ---- acceso general y nombre
    def test_the_owner_opens_the_link_as_viewer_and_a_stranger_can_then_read_but_not_write(self):
        self.put("settings/", {"link_access": "anyone", "link_role": "viewer"})

        self.assertEqual(self.enter("luis@x.com").data["role"], "viewer")
        self.assertEqual(self.client.get(f"/api/rooms/{self.room}/activity/", **self.session("luis@x.com")).status_code, 200)
        denied = self.client.post(f"/api/rooms/{self.room}/ia/chat/", {"mode": "ask", "message": "hola"}, format="json", **self.session("luis@x.com"))
        self.assertEqual((denied.status_code, denied.json()["code"]), (403, "read_only"))

    def test_closing_the_link_shuts_the_stranger_out_again(self):
        self.put("settings/", {"link_access": "anyone", "link_role": "editor"})
        self.assertEqual(self.enter("luis@x.com").status_code, 200)

        self.put("settings/", {"link_access": "restricted"})

        self.assertEqual(self.enter("luis@x.com").status_code, 403)

    def test_only_the_owner_changes_the_settings(self):
        self.invite(["beto@x.com"], role="editor")

        response = self.put("settings/", {"title": "Mío ahora"}, email="beto@x.com")

        self.assertEqual((response.status_code, response.data["code"]), (403, "owner_only"))
        self.assertEqual(self.enter("ana@x.com").data["title"], "")

    def test_bad_settings_are_refused_with_the_reason(self):
        for data in ({"link_access": "publico"}, {"link_role": "owner"}, {"title": "x" * 200}, {"title": 5}):
            response = self.put("settings/", data)
            self.assertEqual(response.status_code, 400, data)
            self.assertIn("error", response.data)

    # ---- personas
    def test_the_owner_changes_a_role_and_takes_somebody_out(self):
        self.invite(["beto@x.com"], role="editor")

        changed = self.put("members/", {"email": "beto@x.com", "role": "viewer"})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.enter("beto@x.com").data["can_edit"], False)

        removed = self.delete("members/", {"email": "beto@x.com"})
        self.assertEqual(removed.status_code, 200)
        self.assertEqual([m["email"] for m in removed.data["members"]], ["ana@x.com"])
        self.assertEqual(self.enter("beto@x.com").status_code, 403)

    def test_only_the_owner_manages_people_and_the_owner_cannot_be_taken_out(self):
        self.invite(["beto@x.com"], role="editor")

        self.assertEqual(self.put("members/", {"email": "ana@x.com", "role": "viewer"}).status_code, 404)
        self.assertEqual(self.delete("members/", {"email": "ana@x.com"}).status_code, 404)
        self.assertEqual(self.put("members/", {"email": "beto@x.com", "role": "viewer"}, email="beto@x.com").status_code, 403)
        self.assertEqual(self.delete("members/", {"email": "ana@x.com"}, email="beto@x.com").status_code, 403)
        self.assertEqual(self.put("members/", {"email": "beto@x.com", "role": "owner"}).status_code, 400)
        self.assertEqual(self.put("members/", {"email": "nadie@x.com", "role": "viewer"}).status_code, 404)
        self.assertEqual(self.put("members/", {"email": "mal", "role": "viewer"}).status_code, 400)

    def test_someone_can_take_themselves_off_the_list_but_the_owner_cannot(self):
        self.invite(["beto@x.com"], role="editor")

        left = self.delete("members/", {"email": "beto@x.com"}, email="beto@x.com")

        self.assertEqual((left.status_code, left.data), (200, {"left": True}))
        self.assertEqual(self.enter("beto@x.com").status_code, 403)
        self.assertEqual(self.delete("members/", {"email": "ana@x.com"}, email="ana@x.com").status_code, 404)

    # ---- borrar y «Mis diagramas»
    def test_the_owner_deletes_the_room_and_it_closes_for_everyone(self):
        self.invite(["beto@x.com"], role="editor")

        response = self.delete("")

        self.assertEqual((response.status_code, response.data), (200, {"deleted": True}))
        for email in ("ana@x.com", "beto@x.com"):
            self.assertEqual(self.enter(email).status_code, 403, email)
        self.assertEqual(self.client.get("/api/rooms/", **self.session("ana@x.com")).data["rooms"], [])

    def test_only_the_owner_can_delete_the_room(self):
        self.invite(["beto@x.com"], role="editor")

        response = self.delete("", email="beto@x.com")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.enter("beto@x.com").status_code, 200)

    def test_my_diagrams_lists_what_i_created_what_i_was_invited_to_and_what_i_opened_by_link(self):
        self.put("settings/", {"title": "Tienda"})
        self.invite(["beto@x.com"], role="viewer")
        self.client.post("/api/rooms/otra-sala/access/", **self.session("beto@x.com"))
        self.client.put("/api/rooms/otra-sala/settings/", {"title": "Mía", "link_access": "anyone", "link_role": "editor"}, format="json", **self.session("beto@x.com"))
        self.client.post("/api/rooms/otra-sala/access/", **self.session("ana@x.com"))

        mine = self.client.get("/api/rooms/", **self.session("ana@x.com")).data["rooms"]
        his = self.client.get("/api/rooms/", **self.session("beto@x.com")).data["rooms"]

        self.assertEqual([(d["room"], d["title"], d["role"], d["owner"]) for d in mine],
                         [("otra-sala", "Mía", "editor", "beto@x.com"), (self.room, "Tienda", "owner", "ana@x.com")])
        self.assertEqual({d["room"]: d["role"] for d in his}, {"otra-sala": "owner", self.room: "viewer"})

    def test_my_diagrams_needs_a_session(self):
        self.assertEqual(self.client.get("/api/rooms/").status_code, 401)

    @override_settings(AUTH_REQUIRED=False)
    def test_without_the_switch_there_are_no_accounts_so_the_list_is_empty_and_the_sharing_routes_say_so(self):
        self.assertEqual(self.client.get("/api/rooms/").data, {"required": False, "rooms": []})
        self.assertEqual(self.client.put(f"/api/rooms/{self.room}/settings/", {"title": "x"}, format="json").status_code, 409)
        self.assertEqual(self.client.put(f"/api/rooms/{self.room}/members/", {"email": "a@b.co", "role": "viewer"}, format="json").status_code, 409)
        self.assertEqual(self.client.delete(f"/api/rooms/{self.room}/").status_code, 409)

