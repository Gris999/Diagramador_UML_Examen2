from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from collab import auth
from collab.models import RoomMember


class RoomAccessTests(TestCase):
    """Quién entra a cada sala: el primero que la abre es el propietario y los demás entran si alguien los invitó."""

    def test_the_first_to_open_a_room_becomes_its_owner(self):
        self.assertEqual(auth.room_access("sala-1", "ana@x.com", claim=True), "ok")

        self.assertEqual(auth.role_of("sala-1", "ana@x.com"), "owner")
        self.assertEqual(auth.list_members("sala-1"), [{"email": "ana@x.com", "role": "owner"}])

    def test_a_room_nobody_opened_is_not_claimed_just_by_asking_about_it(self):
        self.assertEqual(auth.room_access("sala-1", "ana@x.com"), "unclaimed")
        self.assertEqual(auth.list_members("sala-1"), [])

    def test_somebody_else_is_denied_once_the_room_has_an_owner_even_when_asking_to_claim(self):
        auth.room_access("sala-1", "ana@x.com", claim=True)

        self.assertEqual(auth.room_access("sala-1", "beto@x.com"), "denied")
        self.assertEqual(auth.room_access("sala-1", "beto@x.com", claim=True), "denied")
        self.assertEqual(auth.list_members("sala-1"), [{"email": "ana@x.com", "role": "owner"}])

    def test_an_invited_address_gets_in_and_the_owner_is_listed_first(self):
        auth.room_access("sala-1", "ana@x.com", claim=True)

        added = auth.add_invited("sala-1", ["beto@x.com", "luis@x.com"], "ana@x.com")

        self.assertEqual(added, ["beto@x.com", "luis@x.com"])
        self.assertEqual(auth.room_access("sala-1", "beto@x.com"), "ok")
        self.assertEqual(auth.role_of("sala-1", "beto@x.com"), "invited")
        self.assertEqual([m["email"] for m in auth.list_members("sala-1")], ["ana@x.com", "beto@x.com", "luis@x.com"])
        self.assertEqual(RoomMember.objects.get(room="sala-1", email="beto@x.com").invited_by, "ana@x.com")

    def test_inviting_someone_who_already_has_access_changes_nothing(self):
        auth.room_access("sala-1", "ana@x.com", claim=True)
        auth.add_invited("sala-1", ["beto@x.com"], "ana@x.com")

        self.assertEqual(auth.add_invited("sala-1", ["beto@x.com", "ana@x.com"], "beto@x.com"), [])
        self.assertEqual(auth.role_of("sala-1", "ana@x.com"), "owner")
        self.assertEqual(RoomMember.objects.get(room="sala-1", email="beto@x.com").invited_by, "ana@x.com")

    def test_removing_invited_addresses_never_removes_the_owner(self):
        auth.room_access("sala-1", "ana@x.com", claim=True)
        auth.add_invited("sala-1", ["beto@x.com"], "ana@x.com")

        auth.remove_invited("sala-1", ["beto@x.com", "ana@x.com"])

        self.assertEqual(auth.list_members("sala-1"), [{"email": "ana@x.com", "role": "owner"}])

    def test_rooms_do_not_share_their_lists(self):
        auth.room_access("sala-1", "ana@x.com", claim=True)

        self.assertEqual(auth.room_access("sala-2", "ana@x.com"), "unclaimed")
        self.assertEqual(auth.room_access("sala-2", "beto@x.com", claim=True), "ok")
        self.assertEqual(auth.room_access("sala-1", "beto@x.com"), "denied")

    def test_there_can_only_be_one_owner_even_if_two_try_at_once(self):
        auth.room_access("sala-1", "ana@x.com", claim=True)

        with self.assertRaises(Exception):
            RoomMember.objects.create(room="sala-1", email="beto@x.com", role="owner")


class RoomPathTests(SimpleTestCase):
    def test_it_finds_the_room_of_a_room_route_and_of_the_backups(self):
        self.assertEqual(auth.room_of_path("/api/rooms/sala-1/ia/chat/"), "sala-1")
        self.assertEqual(auth.room_of_path("/api/rooms/sala-1/access/"), "sala-1")
        self.assertEqual(auth.room_of_path("/api/set_backup_uml/3f2c1b7e-9a4d-4c55-8e21-0b6f7d9a1c42/"), "3f2c1b7e-9a4d-4c55-8e21-0b6f7d9a1c42")
        self.assertEqual(auth.room_of_path("/api/get_backup_uml/abc/"), "abc")

    def test_other_routes_do_not_belong_to_a_room(self):
        for path in ("/api/ia/provider/", "/api/auth/config/", "/api/xmi/export/", "/api/generar_todo/", "/", "/api/rooms/", "/api/rooms"):
            self.assertIsNone(auth.room_of_path(path), path)


@override_settings(AUTH_REQUIRED=True)
class RoomMiddlewareTests(TestCase):
    def call(self, path, email, method="get"):
        header = {"HTTP_AUTHORIZATION": f"Bearer {auth.make_session(email)}"} if email else {}
        request = getattr(RequestFactory(), method)(path, **header)
        return auth.EmailSessionMiddleware(lambda req: JsonResponse({"ok": True}))(request)

    def test_a_member_reaches_the_routes_of_the_room(self):
        auth.room_access("sala-1", "ana@x.com", claim=True)

        for path in ("/api/rooms/sala-1/activity/", "/api/rooms/sala-1/ia/chat/", "/api/get_backup_uml/sala-1/"):
            self.assertEqual(self.call(path, "ana@x.com").status_code, 200, path)

    def test_somebody_who_was_not_invited_gets_a_403_that_says_so(self):
        auth.room_access("sala-1", "ana@x.com", claim=True)

        response = self.call("/api/rooms/sala-1/activity/", "beto@x.com")

        self.assertEqual(response.status_code, 403)
        self.assertIn(b"not_invited", response.content)

    def test_every_route_of_the_room_is_closed_to_them_including_the_backups(self):
        auth.room_access("sala-1", "ana@x.com", claim=True)

        for path in ("/api/rooms/sala-1/chat/", "/api/rooms/sala-1/ia/chat/", "/api/rooms/sala-1/ia/provider/",
                     "/api/rooms/sala-1/invite/", "/api/rooms/sala-1/activity/3/apply/0/",
                     "/api/set_backup_uml/sala-1/", "/api/get_backup_uml/sala-1/"):
            self.assertEqual(self.call(path, "beto@x.com", "post").status_code, 403, path)

    def test_the_access_route_is_left_to_its_own_view_so_the_first_person_can_claim_the_room(self):
        self.assertEqual(self.call("/api/rooms/sala-nueva/access/", "ana@x.com", "post").status_code, 200)

    def test_a_room_nobody_has_claimed_is_closed_until_someone_opens_it_properly(self):
        self.assertEqual(self.call("/api/rooms/sala-nueva/activity/", "ana@x.com").status_code, 403)

    def test_an_invited_address_reaches_the_room(self):
        auth.room_access("sala-1", "ana@x.com", claim=True)
        auth.add_invited("sala-1", ["beto@x.com"], "ana@x.com")

        self.assertEqual(self.call("/api/rooms/sala-1/activity/", "beto@x.com").status_code, 200)

    def test_routes_that_are_not_of_a_room_only_need_a_session(self):
        self.assertEqual(self.call("/api/ia/provider/", "ana@x.com").status_code, 200)
        self.assertEqual(self.call("/api/ia/provider/", None).status_code, 401)

    @override_settings(AUTH_REQUIRED=False)
    def test_without_the_switch_nobody_is_asked_about_rooms(self):
        self.assertEqual(self.call("/api/rooms/sala-1/activity/", None).status_code, 200)
