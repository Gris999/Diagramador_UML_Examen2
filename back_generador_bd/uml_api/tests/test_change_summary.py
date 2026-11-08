from django.test import SimpleTestCase

from uml_api.services.change_summary import MAX_LINES, summarize_changes

UML = {
    "classes": [
        {"id": "c1", "name": "Cliente", "attributes": [{"name": "nombre", "type": "String"}], "methods": []},
        {"id": "c2", "name": "Pedido", "attributes": [], "methods": []},
    ],
    "relationships": [],
}


class SummarizeChangesTests(SimpleTestCase):
    def test_a_new_class_says_its_attributes_and_methods(self):
        changes = {
            "classes": [{
                "id": "n1", "name": "Factura",
                "attributes": [{"name": "total", "type": "float"}, {"name": "fecha", "type": "Date"}],
                "methods": [{"name": "pagar"}],
            }],
            "relationships": [],
        }

        self.assertEqual(
            summarize_changes(changes, UML),
            ["Crear la clase Factura (atributos: total: float, fecha: Date; métodos: pagar)"],
        )

    def test_deleting_a_class_or_a_member_or_a_relationship(self):
        changes = {
            "classes": [
                {"name": "Pedido", "eliminar": True},
                {"name": "Cliente", "attributes": [{"name": "nombre", "eliminar": True}]},
            ],
            "relationships": [{"sourceId": "Cliente", "targetId": "Pedido", "eliminar": True}],
        }

        self.assertEqual(summarize_changes(changes, UML), [
            "Eliminar la clase Pedido",
            "Quitar «nombre» de la clase Cliente",
            "Quitar la relación entre Cliente y Pedido",
        ])

    def test_a_relationship_names_its_ends_even_when_it_uses_ids(self):
        changes = {"classes": [], "relationships": [{"type": "composition", "sourceId": "c1", "targetId": "c2"}]}

        self.assertEqual(summarize_changes(changes, UML), ["Relacionar Cliente con Pedido (composition)"])

    def test_an_edit_says_what_was_renamed(self):
        changes = {
            "original": {"classes": [{"id": "c1", "name": "Cliente"}], "relationships": []},
            "editado": {
                "classes": [{
                    "id": "c1", "name": "Cliente", "editado": True,
                    "attributes": [{"originalName": "nombre", "name": "nombre_completo", "type": "String", "editado": True}],
                }],
                "relationships": [],
            },
        }

        self.assertEqual(
            summarize_changes(changes, UML),
            ["En la clase Cliente, cambiar «nombre» por «nombre_completo»"],
        )

    def test_a_long_change_is_cut_with_a_count_of_what_is_left(self):
        changes = {"classes": [{"id": f"x{n}", "name": f"Clase{n}"} for n in range(MAX_LINES + 3)], "relationships": []}

        lines = summarize_changes(changes, UML)

        self.assertEqual(len(lines), MAX_LINES + 1)
        self.assertEqual(lines[-1], "… y 3 cambios más")

    def test_a_change_that_is_not_an_object_has_nothing_to_say(self):
        for changes in (None, [], "texto", 3):
            self.assertEqual(summarize_changes(changes, UML), [])

    def test_control_characters_and_long_names_do_not_get_through(self):
        changes = {"classes": [{"id": "z", "name": "Mala\x00\n" + "x" * 200}], "relationships": []}

        line = summarize_changes(changes, UML)[0]

        self.assertNotIn("\x00", line)
        self.assertNotIn("\n", line)
        self.assertLess(len(line), 100)
