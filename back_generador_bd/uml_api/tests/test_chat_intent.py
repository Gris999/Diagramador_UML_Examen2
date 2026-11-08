from django.test import SimpleTestCase

from uml_api.services.chat_intent import ASK, CHANGE, CONFIRM, DISCARD, HISTORY, REVIEW, classify, normalize

NAMES = ["Ana", "Beto", "IA", "Luis Pérez"]


class NormalizeTests(SimpleTestCase):
    def test_ignores_case_accents_and_signs(self):
        self.assertEqual(normalize("¿Qué hizo BETO?!"), "que hizo beto")
        self.assertEqual(normalize("  Añade   una   clase. "), "anade una clase")

    def test_anything_that_is_not_text_is_empty(self):
        self.assertEqual(normalize(None), "")
        self.assertEqual(normalize(42), "")


class ClassifyChangeTests(SimpleTestCase):
    def intent(self, message, **kwargs):
        return classify(message, NAMES, **kwargs)["intent"]

    def test_an_order_to_edit_the_diagram_is_a_change(self):
        for message in (
            "Agrega una clase Cliente con nombre y correo",
            "añade el atributo edad a Persona",
            "elimina la clase Usuario",
            "Borra la relación entre Persona y Cliente",
            "cambia fecha:Date a fecha_hora:String",
            "renombra la clase Pedido a Orden",
            "relaciona Cliente con Factura",
        ):
            self.assertEqual(self.intent(message), CHANGE, message)

    def test_courtesy_words_before_the_verb_do_not_hide_the_order(self):
        for message in (
            "por favor agrega una clase Producto",
            "¿Puedes agregar una clase Producto?",
            "Quiero que elimines el atributo edad",
            "necesito que crees una clase Venta",
            "me gustaría que cambies el tipo de total",
            "y ahora quita la relación entre A y B",
        ):
            self.assertEqual(self.intent(message), CHANGE, message)

    def test_a_question_about_how_to_do_something_is_not_a_change(self):
        for message in (
            "¿Cómo agrego una clase?",
            "¿Se puede eliminar una relación?",
            "¿Qué agrega la clase Pedido?",
            "Explícame este diagrama",
            "¿Cuántas clases hay?",
            "¿Para qué sirve la composición?",
            "quiero saber qué atributos tiene Cliente",
        ):
            self.assertEqual(self.intent(message), ASK, message)

    def test_it_only_skips_the_permission_when_the_person_says_so(self):
        self.assertFalse(classify("agrega una clase Cliente", NAMES)["direct"])
        for message in (
            "agrega una clase Cliente directamente",
            "Agrega una clase Cliente, sin preguntar",
            "elimina Pedido sin confirmar",
            "crea la clase Venta de una vez",
        ):
            decision = classify(message, NAMES)
            self.assertEqual((decision["intent"], decision["direct"]), (CHANGE, True), message)

    def test_an_empty_message_is_a_question(self):
        self.assertEqual(self.intent(""), ASK)
        self.assertEqual(self.intent("   "), ASK)


class ClassifyReviewTests(SimpleTestCase):
    def test_asking_for_a_review_is_a_review(self):
        for message in (
            "Revisa el diagrama",
            "¿puedes revisar el diagrama?",
            "valida mi modelo",
            "¿Qué mejorarías?",
            "dame sugerencias",
            "¿Qué le falta al diagrama?",
            "¿Hay errores en el diagrama?",
        ):
            self.assertEqual(classify(message, NAMES)["intent"], REVIEW, message)


class ClassifyHistoryTests(SimpleTestCase):
    def test_asking_what_a_person_did_names_that_person(self):
        for message, person in (
            ("¿Qué hizo Beto?", "Beto"),
            ("que hizo beto", "Beto"),
            ("Dime el historial de Ana", "Ana"),
            ("¿Qué cambios hizo Luis Pérez hoy?", "Luis Pérez"),
            ("¿Qué hizo la IA?", "IA"),
            ("actividad de Ana", "Ana"),
        ):
            decision = classify(message, NAMES)
            self.assertEqual((decision["intent"], decision["person"]), (HISTORY, person), message)

    def test_asking_for_the_history_of_everyone_names_nobody(self):
        for message in ("Muéstrame el historial", "¿Qué hicieron todos?", "dime los últimos cambios"):
            decision = classify(message, NAMES)
            self.assertEqual((decision["intent"], decision["person"]), (HISTORY, None), message)

    def test_an_unknown_name_is_left_to_the_ai(self):
        self.assertEqual(classify("¿Qué hizo Carlos?", NAMES)["intent"], ASK)

    def test_a_name_inside_another_word_does_not_match(self):
        # «ia» está dentro de «historia» y «Ana» dentro de «banana»
        self.assertEqual(classify("¿Qué hizo la historia?", NAMES)["intent"], ASK)
        self.assertEqual(classify("¿Qué hizo la banana?", NAMES)["intent"], ASK)

    def test_a_loose_question_about_what_happened_goes_to_the_ai_which_reads_the_activity(self):
        self.assertEqual(classify("¿qué pasó mientras no estaba?", NAMES)["intent"], ASK)
        self.assertEqual(classify("Resume lo que pasó con la clase Factura", NAMES)["intent"], ASK)

    def test_what_a_class_does_is_not_history(self):
        self.assertEqual(classify("¿Qué hace la clase Cliente?", NAMES)["intent"], ASK)


class ClassifyAnswerTests(SimpleTestCase):
    def test_yes_and_no_only_answer_a_pending_proposal(self):
        for message in ("sí", "Sí, aplícalo", "ok", "dale", "adelante", "hazlo"):
            self.assertEqual(classify(message, NAMES, has_pending=True)["intent"], CONFIRM, message)
            self.assertEqual(classify(message, NAMES, has_pending=False)["intent"], ASK, message)
        for message in ("no", "No, descártalo", "cancela", "mejor no", "olvídalo"):
            self.assertEqual(classify(message, NAMES, has_pending=True)["intent"], DISCARD, message)
            self.assertEqual(classify(message, NAMES, has_pending=False)["intent"], ASK, message)

    def test_a_long_message_is_a_new_request_not_an_answer(self):
        decision = classify("sí pero cambia el nombre de la clase a Orden", NAMES, has_pending=True)
        self.assertNotEqual(decision["intent"], CONFIRM)
        self.assertEqual(classify("no entiendo qué significa esta relación", NAMES, has_pending=True)["intent"], ASK)

    def test_a_new_order_while_waiting_is_still_a_change(self):
        self.assertEqual(classify("agrega una clase Venta", NAMES, has_pending=True)["intent"], CHANGE)
