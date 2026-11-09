from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from collab import auth, rooms
from collab.models import RoomMember, RoomSettings


class RoomEntryTests(TestCase):
    """Quién entra a cada sala: el primero que la abre es el propietario y los demás entran según lo que el propietario comparte."""

    def test_the_first_to_open_a_room_becomes_its_owner_and_the_room_gets_its_settings(self):
        self.assertEqual(rooms.enter("sala-1", "ana@x.com", claim=True), ("ok", "owner"))

        self.assertEqual(rooms.effective_role("sala-1", "ana@x.com"), "owner")
        self.assertEqual(rooms.list_members("sala-1"), [{"email": "ana@x.com", "role": "owner", "source": "owner"}])
        cfg = RoomSettings.objects.get(room="sala-1")
        self.assertEqual((cfg.link_access, cfg.link_role, cfg.title, cfg.deleted), ("restricted", "viewer", "", False))

    def test_a_room_nobody_opened_is_not_claimed_just_by_asking_about_it(self):
        self.assertEqual(rooms.enter("sala-1", "ana@x.com"), ("unclaimed", None))
        self.assertEqual(rooms.list_members("sala-1"), [])

    def test_somebody_else_is_denied_even_when_asking_to_claim(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)

        self.assertEqual(rooms.enter("sala-1", "beto@x.com"), ("denied", None))
        self.assertEqual(rooms.enter("sala-1", "beto@x.com", claim=True), ("denied", None))
        self.assertEqual([m["email"] for m in rooms.list_members("sala-1")], ["ana@x.com"])

    def test_there_can_only_be_one_owner_even_if_two_try_at_once(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)

        with self.assertRaises(Exception):
            RoomMember.objects.create(room="sala-1", email="beto@x.com", role="owner")

    def test_rooms_do_not_share_their_lists(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)

        self.assertEqual(rooms.enter("sala-2", "ana@x.com"), ("unclaimed", None))
        self.assertEqual(rooms.enter("sala-2", "beto@x.com", claim=True), ("ok", "owner"))
        self.assertEqual(rooms.enter("sala-1", "beto@x.com"), ("denied", None))

    def test_entering_notes_when_the_room_was_opened(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)
        RoomMember.objects.filter(room="sala-1").update(last_opened_at=None)

        rooms.enter("sala-1", "ana@x.com")

        self.assertIsNotNone(RoomMember.objects.get(room="sala-1", email="ana@x.com").last_opened_at)

    def test_a_room_from_before_the_permissions_gets_the_usual_ones_when_it_is_entered(self):
        RoomMember.objects.create(room="vieja", email="ana@x.com", role="owner", source="owner")

        self.assertEqual(rooms.enter("vieja", "ana@x.com"), ("ok", "owner"))
        self.assertTrue(RoomSettings.objects.filter(room="vieja", link_access="restricted").exists())


class RoomRolesTests(TestCase):
    def setUp(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)

    def test_an_invited_address_gets_the_role_it_was_invited_with(self):
        added = rooms.add_members("sala-1", ["beto@x.com", "luis@x.com"], "ana@x.com", "editor")
        rooms.add_members("sala-1", ["eva@x.com"], "ana@x.com", "viewer")

        self.assertEqual(added, ["beto@x.com", "luis@x.com"])
        self.assertEqual(rooms.effective_role("sala-1", "beto@x.com"), "editor")
        self.assertEqual(rooms.effective_role("sala-1", "eva@x.com"), "viewer")
        self.assertEqual(RoomMember.objects.get(room="sala-1", email="beto@x.com").invited_by, "ana@x.com")

    def test_the_list_has_the_owner_first_and_then_who_came_in_order(self):
        rooms.add_members("sala-1", ["beto@x.com"], "ana@x.com", "editor")
        rooms.add_members("sala-1", ["eva@x.com"], "ana@x.com", "viewer")

        self.assertEqual(
            [(m["email"], m["role"]) for m in rooms.list_members("sala-1")],
            [("ana@x.com", "owner"), ("beto@x.com", "editor"), ("eva@x.com", "viewer")],
        )

    def test_inviting_someone_already_in_keeps_their_role_and_never_touches_the_owner(self):
        rooms.add_members("sala-1", ["beto@x.com"], "ana@x.com", "viewer")

        added = rooms.add_members("sala-1", ["beto@x.com", "ana@x.com"], "beto@x.com", "editor")

        self.assertEqual(added, [])
        self.assertEqual(rooms.effective_role("sala-1", "beto@x.com"), "viewer")
        self.assertEqual(rooms.effective_role("sala-1", "ana@x.com"), "owner")

    def test_only_viewer_and_editor_can_be_given(self):
        for role in ("owner", "admin", "", None, "invited"):
            with self.assertRaises(rooms.SharingError):
                rooms.add_members("sala-1", ["beto@x.com"], "ana@x.com", role)

    def test_the_owner_changes_a_role_but_not_their_own(self):
        rooms.add_members("sala-1", ["beto@x.com"], "ana@x.com", "editor")

        self.assertTrue(rooms.set_member_role("sala-1", "beto@x.com", "viewer"))
        self.assertEqual(rooms.effective_role("sala-1", "beto@x.com"), "viewer")
        self.assertFalse(rooms.set_member_role("sala-1", "ana@x.com", "viewer"))
        self.assertFalse(rooms.set_member_role("sala-1", "nadie@x.com", "viewer"))
        self.assertEqual(rooms.effective_role("sala-1", "ana@x.com"), "owner")
        with self.assertRaises(rooms.SharingError):
            rooms.set_member_role("sala-1", "beto@x.com", "owner")

    def test_removing_a_person_takes_their_access_but_never_the_owners(self):
        rooms.add_members("sala-1", ["beto@x.com"], "ana@x.com", "editor")

        self.assertTrue(rooms.remove_member("sala-1", "beto@x.com"))
        self.assertIsNone(rooms.effective_role("sala-1", "beto@x.com"))
        self.assertFalse(rooms.remove_member("sala-1", "ana@x.com"))
        self.assertEqual(rooms.effective_role("sala-1", "ana@x.com"), "owner")

    def test_taking_back_the_ones_just_added_never_removes_the_owner(self):
        rooms.add_members("sala-1", ["beto@x.com"], "ana@x.com", "editor")

        rooms.remove_added("sala-1", ["beto@x.com", "ana@x.com"])

        self.assertEqual([m["email"] for m in rooms.list_members("sala-1")], ["ana@x.com"])

    def test_the_helpers_order_the_roles(self):
        self.assertTrue(rooms.at_least("owner", "editor"))
        self.assertTrue(rooms.at_least("editor", "viewer"))
        self.assertFalse(rooms.at_least("viewer", "editor"))
        self.assertFalse(rooms.at_least(None, "viewer"))
        self.assertFalse(rooms.at_least("invited", "viewer"))
        self.assertEqual(rooms.higher("viewer", "editor"), "editor")


class RoomLinkAccessTests(TestCase):
    """Acceso general, como en Google Docs: restringido o cualquiera con el enlace (como lector o como editor)."""

    def setUp(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)

    def test_a_restricted_room_stays_closed_to_whoever_only_has_the_link(self):
        self.assertEqual(rooms.enter("sala-1", "luis@x.com"), ("denied", None))
        self.assertEqual(rooms.my_rooms("luis@x.com"), [])

    def test_with_the_link_open_anyone_enters_with_the_role_of_the_link(self):
        rooms.update_settings("sala-1", link_access="anyone", link_role="viewer")

        self.assertEqual(rooms.enter("sala-1", "luis@x.com"), ("ok", "viewer"))

        rooms.update_settings("sala-1", link_role="editor")
        self.assertEqual(rooms.enter("sala-1", "luis@x.com"), ("ok", "editor"))

    def test_whoever_opened_a_public_link_finds_the_room_in_their_list_without_being_listed_in_the_room(self):
        rooms.update_settings("sala-1", title="Mi modelo", link_access="anyone", link_role="viewer")

        rooms.enter("sala-1", "luis@x.com")

        documents = rooms.my_rooms("luis@x.com")
        self.assertEqual([(d["room"], d["title"], d["role"], d["owner"]) for d in documents], [("sala-1", "Mi modelo", "viewer", "ana@x.com")])
        self.assertEqual([m["email"] for m in rooms.list_members("sala-1")], ["ana@x.com"])

    def test_closing_the_link_takes_the_access_away_and_the_room_leaves_their_list(self):
        rooms.update_settings("sala-1", link_access="anyone", link_role="editor")
        rooms.enter("sala-1", "luis@x.com")

        rooms.update_settings("sala-1", link_access="restricted")

        self.assertIsNone(rooms.effective_role("sala-1", "luis@x.com"))
        self.assertEqual(rooms.enter("sala-1", "luis@x.com"), ("denied", None))
        self.assertEqual(rooms.my_rooms("luis@x.com"), [])

    def test_the_higher_role_wins_between_the_one_given_and_the_one_of_the_link(self):
        rooms.add_members("sala-1", ["beto@x.com"], "ana@x.com", "viewer")
        rooms.add_members("sala-1", ["eva@x.com"], "ana@x.com", "editor")
        rooms.update_settings("sala-1", link_access="anyone", link_role="editor")

        self.assertEqual(rooms.effective_role("sala-1", "beto@x.com"), "editor")

        rooms.update_settings("sala-1", link_role="viewer")
        self.assertEqual(rooms.effective_role("sala-1", "beto@x.com"), "viewer")
        self.assertEqual(rooms.effective_role("sala-1", "eva@x.com"), "editor")

    def test_somebody_invited_after_opening_the_link_becomes_a_real_member(self):
        rooms.update_settings("sala-1", link_access="anyone", link_role="viewer")
        rooms.enter("sala-1", "luis@x.com")

        added = rooms.add_members("sala-1", ["luis@x.com"], "ana@x.com", "editor")
        rooms.update_settings("sala-1", link_access="restricted")

        self.assertEqual(added, ["luis@x.com"])
        self.assertEqual(rooms.effective_role("sala-1", "luis@x.com"), "editor")
        self.assertIn("luis@x.com", [m["email"] for m in rooms.list_members("sala-1")])

    def test_a_link_person_cannot_be_given_a_role_through_the_member_routes(self):
        rooms.update_settings("sala-1", link_access="anyone", link_role="viewer")
        rooms.enter("sala-1", "luis@x.com")

        self.assertFalse(rooms.set_member_role("sala-1", "luis@x.com", "editor"))


class RoomSettingsTests(TestCase):
    def setUp(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)

    def test_the_name_is_cleaned_and_kept(self):
        rooms.update_settings("sala-1", title="  Modelo   de\ttienda \x00 ")

        self.assertEqual(rooms.settings_of("sala-1").title, "Modelo de tienda")

    def test_the_name_can_be_cleared_and_does_not_change_when_not_sent(self):
        rooms.update_settings("sala-1", title="Uno")
        rooms.update_settings("sala-1", link_access="anyone")
        self.assertEqual(rooms.settings_of("sala-1").title, "Uno")

        rooms.update_settings("sala-1", title="")
        self.assertEqual(rooms.settings_of("sala-1").title, "")

    def test_a_name_that_is_not_text_or_too_long_is_refused(self):
        for value in (5, ["x"], {}, "x" * (rooms.MAX_TITLE_CHARS + 1)):
            with self.assertRaises(rooms.SharingError):
                rooms.update_settings("sala-1", title=value)
        self.assertEqual(len(rooms.clean_title("x" * rooms.MAX_TITLE_CHARS)), rooms.MAX_TITLE_CHARS)

    def test_general_access_and_its_role_only_accept_known_values(self):
        for link_access in ("publico", "", 3):
            with self.assertRaises(rooms.SharingError):
                rooms.update_settings("sala-1", link_access=link_access)
        for link_role in ("owner", "admin", "", 3):
            with self.assertRaises(rooms.SharingError):
                rooms.update_settings("sala-1", link_role=link_role)
        cfg = rooms.settings_of("sala-1")
        self.assertEqual((cfg.link_access, cfg.link_role), ("restricted", "viewer"))

    def test_a_refused_change_does_not_save_the_valid_part(self):
        with self.assertRaises(rooms.SharingError):
            rooms.update_settings("sala-1", title="Nuevo", link_access="mal")

        self.assertEqual(rooms.settings_of("sala-1").title, "")

    def test_describe_gives_the_screen_everything_it_needs(self):
        rooms.add_members("sala-1", ["beto@x.com"], "ana@x.com", "viewer")
        rooms.update_settings("sala-1", title="Mi modelo", link_access="anyone", link_role="editor")

        mine = rooms.describe("sala-1", "ana@x.com", "owner")
        his = rooms.describe("sala-1", "beto@x.com", "viewer")

        self.assertEqual(
            (mine["is_owner"], mine["can_edit"], mine["title"], mine["link_access"], mine["link_role"], mine["owner"]),
            (True, True, "Mi modelo", "anyone", "editor", "ana@x.com"),
        )
        self.assertEqual((his["is_owner"], his["can_edit"], his["role"]), (False, False, "viewer"))
        self.assertEqual([m["email"] for m in his["members"]], ["ana@x.com", "beto@x.com"])


class RoomDeleteAndListTests(TestCase):
    def test_a_deleted_room_closes_to_everyone_including_the_owner(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)
        rooms.add_members("sala-1", ["beto@x.com"], "ana@x.com", "editor")

        rooms.delete_room("sala-1")

        for email in ("ana@x.com", "beto@x.com"):
            self.assertIsNone(rooms.effective_role("sala-1", email))
            self.assertEqual(rooms.enter("sala-1", email), ("denied", None))
            self.assertEqual(rooms.my_rooms(email), [])
        self.assertEqual(rooms.enter("sala-1", "nuevo@x.com", claim=True), ("denied", None))
        self.assertEqual(RoomMember.objects.filter(room="sala-1").count(), 2)

    def test_my_rooms_lists_the_created_the_invited_and_the_opened_most_recent_first(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)
        rooms.update_settings("sala-1", title="Uno")
        rooms.enter("sala-2", "beto@x.com", claim=True)
        rooms.update_settings("sala-2", title="Dos")
        rooms.add_members("sala-2", ["ana@x.com"], "beto@x.com", "viewer")
        rooms.enter("sala-2", "ana@x.com")
        rooms.enter("sala-1", "ana@x.com")

        documents = rooms.my_rooms("ana@x.com")

        self.assertEqual([(d["room"], d["title"], d["role"], d["owner"]) for d in documents],
                         [("sala-1", "Uno", "owner", "ana@x.com"), ("sala-2", "Dos", "viewer", "beto@x.com")])
        self.assertEqual([d["room"] for d in rooms.my_rooms("beto@x.com")], ["sala-2"])

    def test_a_room_opened_after_the_other_goes_first(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)
        rooms.enter("sala-2", "ana@x.com", claim=True)
        rooms.enter("sala-1", "ana@x.com")

        self.assertEqual([d["room"] for d in rooms.my_rooms("ana@x.com")], ["sala-1", "sala-2"])

    def test_nobody_has_nothing_in_the_list(self):
        self.assertEqual(rooms.my_rooms("nadie@x.com"), [])


class RoomPathTests(SimpleTestCase):
    def test_it_finds_the_room_of_a_room_route_and_of_the_backups(self):
        self.assertEqual(auth.room_of_path("/api/rooms/sala-1/ia/chat/"), "sala-1")
        self.assertEqual(auth.room_of_path("/api/rooms/sala-1/access/"), "sala-1")
        self.assertEqual(auth.room_of_path("/api/rooms/sala-1/"), "sala-1")
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

    def setUp(self):
        rooms.enter("sala-1", "ana@x.com", claim=True)
        rooms.add_members("sala-1", ["beto@x.com"], "ana@x.com", "editor")
        rooms.add_members("sala-1", ["eva@x.com"], "ana@x.com", "viewer")

    def test_the_owner_and_an_editor_read_and_write(self):
        for email in ("ana@x.com", "beto@x.com"):
            for method in ("get", "post", "put", "delete"):
                self.assertEqual(self.call("/api/rooms/sala-1/ia/chat/", email, method).status_code, 200, (email, method))
            self.assertEqual(self.call("/api/set_backup_uml/sala-1/", email, "post").status_code, 200)

    def test_a_viewer_can_read_but_not_write(self):
        for path in ("/api/rooms/sala-1/activity/", "/api/rooms/sala-1/chat/", "/api/get_backup_uml/sala-1/"):
            self.assertEqual(self.call(path, "eva@x.com").status_code, 200, path)
        for path, method in (("/api/rooms/sala-1/ia/chat/", "post"), ("/api/set_backup_uml/sala-1/", "post"),
                             ("/api/rooms/sala-1/invite/", "post"), ("/api/rooms/sala-1/activity/3/apply/0/", "put"),
                             ("/api/rooms/sala-1/settings/", "put"), ("/api/rooms/sala-1/", "delete")):
            response = self.call(path, "eva@x.com", method)
            self.assertEqual(response.status_code, 403, path)
            self.assertIn(b"read_only", response.content)

    def test_somebody_who_was_not_added_gets_a_403_that_says_so(self):
        response = self.call("/api/rooms/sala-1/activity/", "luis@x.com")

        self.assertEqual(response.status_code, 403)
        self.assertIn(b"not_invited", response.content)
        self.assertEqual(self.call("/api/rooms/sala-1/ia/chat/", "luis@x.com", "post").status_code, 403)

    def test_a_public_link_gives_the_role_of_the_link_to_anyone_logged_in(self):
        rooms.update_settings("sala-1", link_access="anyone", link_role="viewer")

        self.assertEqual(self.call("/api/rooms/sala-1/activity/", "luis@x.com").status_code, 200)
        self.assertEqual(self.call("/api/rooms/sala-1/ia/chat/", "luis@x.com", "post").status_code, 403)

        rooms.update_settings("sala-1", link_role="editor")
        self.assertEqual(self.call("/api/rooms/sala-1/ia/chat/", "luis@x.com", "post").status_code, 200)

    def test_a_deleted_room_is_closed_to_everyone(self):
        rooms.delete_room("sala-1")

        for email in ("ana@x.com", "beto@x.com", "eva@x.com"):
            self.assertEqual(self.call("/api/rooms/sala-1/activity/", email).status_code, 403, email)

    def test_the_access_route_is_left_to_its_own_view_so_the_first_person_can_claim_the_room(self):
        self.assertEqual(self.call("/api/rooms/sala-nueva/access/", "ana@x.com", "post").status_code, 200)

    def test_a_room_nobody_has_claimed_is_closed_until_someone_opens_it_properly(self):
        self.assertEqual(self.call("/api/rooms/sala-nueva/activity/", "ana@x.com").status_code, 403)

    def test_routes_that_are_not_of_a_room_only_need_a_session(self):
        self.assertEqual(self.call("/api/ia/provider/", "ana@x.com").status_code, 200)
        self.assertEqual(self.call("/api/rooms/", "ana@x.com").status_code, 200)
        self.assertEqual(self.call("/api/ia/provider/", None).status_code, 401)

    @override_settings(AUTH_REQUIRED=False)
    def test_without_the_switch_nobody_is_asked_about_rooms(self):
        self.assertEqual(self.call("/api/rooms/sala-1/activity/", None).status_code, 200)
        self.assertEqual(self.call("/api/rooms/sala-1/ia/chat/", None, "post").status_code, 200)
