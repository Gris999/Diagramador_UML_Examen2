"""Generador determinista de ejemplos para reentrenar el modelo.

Cada ejemplo es (diagrama de entrada, pedido, respuesta correcta). La respuesta
la calcula este programa con reglas, no un modelo: es correcta por construcción.

Para medir sin trampa, la prueba usa entidades y redacciones que el
entrenamiento nunca ve (ENTIDADES_PRUEBA y las últimas plantillas de cada
operación). `MANIFEST.json` deja la semilla, los conteos y los hashes.

Uso (desde la raíz del repositorio):

    ml/.venv/bin/python ml/data/generar_dataset.py --salida ml/data/out \
        --train 1500 --valid 150 --test 200 --semilla 42
"""

import argparse
import copy
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from formato import conversacion

ENTIDADES = {
    "Cliente": [("id", "int"), ("nombre", "string"), ("email", "string"), ("telefono", "string")],
    "Pedido": [("id", "int"), ("fecha", "Date"), ("total", "float"), ("estado", "string")],
    "Producto": [("codigo", "string"), ("nombre", "string"), ("precio", "float"), ("stock", "int")],
    "Libro": [("isbn", "string"), ("titulo", "string"), ("paginas", "int"), ("disponible", "boolean")],
    "Autor": [("id", "int"), ("nombre", "string"), ("nacionalidad", "string")],
    "Estudiante": [("matricula", "string"), ("nombre", "string"), ("edad", "int"), ("carrera", "string")],
    "Curso": [("codigo", "string"), ("nombre", "string"), ("creditos", "int")],
    "Empleado": [("id", "int"), ("nombre", "string"), ("sueldo", "float"), ("cargo", "string")],
    "Factura": [("numero", "int"), ("fecha", "Date"), ("monto", "float"), ("pagada", "boolean")],
    "Proveedor": [("id", "int"), ("razonSocial", "string"), ("ciudad", "string")],
    "Sucursal": [("id", "int"), ("direccion", "string"), ("ciudad", "string")],
    "Reserva": [("id", "int"), ("fecha", "Date"), ("personas", "int"), ("confirmada", "boolean")],
    "Usuario": [("id", "int"), ("nombre", "string"), ("clave", "string"), ("activo", "boolean")],
    "Categoria": [("id", "int"), ("nombre", "string"), ("descripcion", "string")],
    "Almacen": [("codigo", "string"), ("ubicacion", "string"), ("capacidad", "int")],
    "Tarea": [("id", "int"), ("titulo", "string"), ("prioridad", "int"), ("terminada", "boolean")],
    "Proyecto": [("id", "int"), ("nombre", "string"), ("presupuesto", "float"), ("inicio", "Date")],
    "Materia": [("codigo", "string"), ("nombre", "string"), ("horas", "int")],
    "Hotel": [("id", "int"), ("nombre", "string"), ("estrellas", "int"), ("ciudad", "string")],
    "Ticket": [("numero", "int"), ("asunto", "string"), ("abierto", "boolean"), ("creado", "Date")],
}
# Solo para la prueba: el modelo nunca las ve entrenando.
ENTIDADES_PRUEBA = {
    "Paciente": [("id", "int"), ("nombre", "string"), ("fechaNacimiento", "Date"), ("seguro", "string")],
    "Doctor": [("matricula", "string"), ("nombre", "string"), ("especialidad", "string")],
    "Vehiculo": [("placa", "string"), ("marca", "string"), ("anio", "int"), ("disponible", "boolean")],
    "Cancion": [("id", "int"), ("titulo", "string"), ("duracion", "float")],
    "Mascota": [("id", "int"), ("nombre", "string"), ("especie", "string"), ("peso", "float")],
    "Pelicula": [("id", "int"), ("titulo", "string"), ("anio", "int"), ("estreno", "Date")],
    "Gimnasio": [("id", "int"), ("nombre", "string"), ("cupo", "int"), ("abierto", "boolean")],
    "Receta": [("id", "int"), ("nombre", "string"), ("calorias", "float"), ("porciones", "int")],
}
ATRIBUTOS_EXTRA = [
    ("observaciones", "string"), ("activo", "boolean"), ("creadoEn", "Date"), ("puntaje", "float"),
    ("cantidad", "int"), ("descuento", "float"), ("pais", "string"), ("notas", "string"),
    ("version", "int"), ("etiqueta", "string"),
]
METODOS = [
    "calcularTotal", "cancelar", "confirmar", "enviar", "pagar", "actualizar", "validar",
    "registrar", "buscar", "exportar", "notificar", "comprar",
]
NOMBRES_CLASE_NUEVOS = ["Cuenta", "Pago", "Ruta", "Evento", "Contrato", "Registro", "Zona", "Turno", "Ficha", "Plan"]
TIPOS = ["int", "string", "float", "Date", "boolean"]
RELACIONES = ["association", "aggregation", "composition"]
NOMBRE_RELACION = {"association": "asociación", "aggregation": "agregación", "composition": "composición"}

# Cada operación tiene redacciones de entrenamiento y otras reservadas a la prueba (las últimas).
# {C}/{D} clases, {a}/{b} atributos, {t} tipo, {m} método, {lista} atributos con tipo, {r} relación.
PLANTILLAS = {
    "crear_clase": (
        ["Agrega una clase {C} con los atributos {lista}", "Crea la clase {C} con {lista}",
         "Añade {C} con los atributos: {lista}", "Necesito una clase {C} que tenga {lista}",
         "Incluye la clase {C} ({lista})"],
        ["Quiero tener la clase {C}, con estos campos: {lista}", "Pon una clase llamada {C} con {lista}"],
    ),
    "agregar_atributo": (
        ["Agrega el atributo {a}: {t} a la clase {C}", "Añade a {C} el atributo {a} de tipo {t}",
         "A {C} ponle el atributo {a}: {t}", "Incluye {a}: {t} en {C}", "La clase {C} necesita el atributo {a} ({t})"],
        ["{C} debe tener además {a} de tipo {t}", "Sumale a {C} un campo {a}: {t}"],
    ),
    "agregar_metodo": (
        ["Agrega el método {m}() a la clase {C}", "Añade a {C} el método {m}", "A {C} ponle la operación {m}()",
         "Incluye el método {m} en {C}", "La clase {C} necesita el método {m}()"],
        ["{C} también debe poder hacer {m}()", "Dale a {C} la operación {m}"],
    ),
    "editar_tipo": (
        ["Cambia el tipo del atributo {a} de la clase {C} a {t}", "El atributo {a} de {C} debe ser de tipo {t}",
         "Modifica {a} en {C}: ahora es {t}", "En {C}, cambia {a} a {t}", "Actualiza el tipo de {a} en {C} a {t}"],
        ["{a} de {C} tiene que pasar a ser {t}", "Haz que {a} en {C} sea de tipo {t}"],
    ),
    "renombrar_atributo": (
        ["Renombra el atributo {a} de {C} a {b}", "En {C}, cambia el nombre de {a} por {b}",
         "El atributo {a} de {C} ahora se llama {b}", "Cámbiale el nombre a {a} en {C}: {b}", "En {C}, {a} pasa a llamarse {b}"],
        ["Llama {b} al atributo {a} de la clase {C}", "{C}: {a} se renombra como {b}"],
    ),
    "eliminar_atributo": (
        ["Elimina el atributo {a} de la clase {C}", "Quita {a} de {C}", "Borra el atributo {a} de {C}",
         "Saca el campo {a} de {C}", "{C} ya no necesita el atributo {a}"],
        ["Ya no quiero {a} en {C}", "Elimina de {C} el campo {a}"],
    ),
    "eliminar_metodo": (
        ["Elimina el método {m} de la clase {C}", "Quita el método {m} de {C}", "Borra la operación {m} de {C}",
         "{C} ya no debe tener el método {m}", "Saca {m}() de {C}"],
        ["Ya no quiero la operación {m} en {C}", "Elimina de {C} el método {m}()"],
    ),
    "eliminar_clase": (
        ["Elimina la clase {C}", "Borra {C}", "Quita la clase {C} del diagrama", "Elimina {C} del modelo",
         "Ya no necesitamos la clase {C}"],
        ["Deshazte de la clase {C}", "Saca {C} del diagrama"],
    ),
    "relacion": (
        ["Crea una {r} de {C} a {D}", "Relaciona {C} con {D} mediante una {r}", "Une {C} con {D} con una {r}",
         "Agrega una {r} entre {C} y {D}", "Haz una {r} desde {C} hacia {D}"],
        ["Quiero una {r} que vaya de {C} a {D}", "Conecta {C} con {D} usando una {r}"],
    ),
    "herencia": (
        ["Haz que {C} herede de {D}", "{C} es una especialización de {D}", "Crea una herencia de {C} hacia {D}",
         "{C} extiende a {D}", "Agrega generalización: {C} hereda de {D}"],
        ["La clase {C} debe ser hija de {D}", "Pon a {C} como subclase de {D}"],
    ),
    "eliminar_relacion": (
        ["Elimina la relación entre {C} y {D}", "Borra la relación de {C} a {D}", "Quita el vínculo entre {C} y {D}",
         "Ya no debe haber relación entre {C} y {D}", "Desconecta {C} de {D}"],
        ["Deshaz la relación que une {C} con {D}", "Suprime la relación {C}-{D}"],
    ),
    "crear_dos_con_relacion": (
        ["Crea las clases {C} y {D} y una {r} de {C} a {D}", "Agrega {C} y {D}, relacionadas con una {r}",
         "Necesito las clases {C} y {D} unidas por una {r} de {C} a {D}", "Crea {C} y {D} con una {r} entre ellas (de {C} a {D})",
         "Añade dos clases, {C} y {D}, con una {r} desde {C}"],
        ["Quiero {C} y {D} en el diagrama, con una {r} que parta de {C}", "Modela {C} y {D} y conéctalas con una {r} de {C} a {D}"],
    ),
}


# Más redacciones por operación (las de prueba siguen sin aparecer en el entrenamiento).
_EXTRA = {
    "crear_clase": (["Genera la clase {C} y dale {lista}", "Quiero la clase {C}: {lista}", "Dibuja una clase {C} con los campos {lista}"],
                    ["Arma la clase {C} con estos atributos: {lista}"]),
    "agregar_atributo": (["{C} debe incluir el atributo {a} ({t})", "Agrégale a {C} el campo {a} de tipo {t}", "Falta {a}: {t} en la clase {C}"],
                         ["Mete en {C} un atributo {a}: {t}"]),
    "agregar_metodo": (["Necesito que {C} tenga la operación {m}()", "Agrega la operación {m} a {C}", "{C} requiere el método {m}"],
                       ["Pon en {C} el método {m}()"]),
    "editar_tipo": (["Pon el atributo {a} de {C} como {t}", "El tipo de {a} en {C} debe cambiar a {t}", "Convierte {a} de {C} a {t}"],
                    ["En la clase {C}, {a} ahora es de tipo {t}"]),
    "renombrar_atributo": (["En {C}, renombra {a} como {b}", "Cambia {a} por {b} en la clase {C}", "El atributo {a} de {C} debe llamarse {b}"],
                           ["Reemplaza el nombre {a} por {b} en {C}"]),
    "eliminar_atributo": (["Elimina {a} de {C}", "Quítale a {C} el atributo {a}", "Ya no hace falta {a} en {C}"],
                          ["Suprime el atributo {a} de la clase {C}"]),
    "eliminar_metodo": (["Elimina {m}() de {C}", "Quítale a {C} la operación {m}", "En {C} sobra el método {m}"],
                        ["Suprime el método {m} de la clase {C}"]),
    "eliminar_clase": (["Elimina {C} del diagrama", "Borra la clase {C} del modelo", "Quiero quitar {C}"],
                       ["Suprime {C} del modelo"]),
    "relacion": (["Relaciona {C} y {D} con una {r}", "Agrega una {r} desde {C} hacia {D}", "Conecta {C} con {D} mediante una {r}"],
                 ["Establece una {r} que vaya de {C} a {D}"]),
    "herencia": (["{C} hereda de {D}", "Haz de {C} una subclase de {D}", "Agrega la herencia {C} -> {D}"],
                 ["{C} debe extender la clase {D}"]),
    "eliminar_relacion": (["Quita la relación que une {C} y {D}", "Elimina la asociación entre {C} y {D}", "Borra el vínculo de {C} con {D}"],
                          ["Suprime el vínculo {C}-{D}"]),
    "crear_dos_con_relacion": (["Agrega {C} y {D} unidas por una {r} (de {C} a {D})", "Crea dos clases, {C} y {D}, y relaciónalas con una {r} que salga de {C}", "Dibuja {C} y {D} con una {r} desde {C}"],
                               ["Genera {C} y {D} y une {C} hacia {D} con una {r}"]),
    "renombrar_clase": (["Renombra la clase {C} a {N}", "Cambia el nombre de {C} por {N}", "{C} ahora se llama {N}", "Llama {N} a la clase {C}", "Cambia {C} a {N}"],
                        ["La clase {C} pasa a llamarse {N}", "{C} se renombra como {N}"]),
    "agregar_varios_atributos": (["Agrega a {C} los atributos {lista}", "Añade a la clase {C} estos atributos: {lista}", "A {C} ponle {lista}", "Incluye en {C} los campos {lista}"],
                                 ["{C} necesita además estos atributos: {lista}", "Suma a {C}: {lista}"]),
    "crear_clase_con_metodos": (["Crea la clase {C} con los atributos {lista} y los métodos {metodos}", "Agrega {C} con {lista}; sus métodos son {metodos}", "Nueva clase {C}: atributos {lista}, métodos {metodos}"],
                                ["Quiero {C} con los atributos {lista} y las operaciones {metodos}"]),
    "crear_varias_clases": (["Crea las clases {clases}", "Agrega estas clases: {clases}", "Necesito las clases {clases}"],
                            ["Genera las siguientes clases: {clases}"]),
}
for _operacion, (_entrenamiento, _prueba) in _EXTRA.items():
    base = PLANTILLAS.setdefault(_operacion, ([], []))
    base[0].extend(_entrenamiento)
    base[1].extend(_prueba)


def ruido(rng, texto):
    """Variaciones de escritura reales: sin acentos, minúsculas, cortesía, punto final."""
    if rng.random() < 0.20 and texto[0] != "{":
        texto = texto[0].lower() + texto[1:]
    if rng.random() < 0.15:
        texto = texto.translate(str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU"))
    if rng.random() < 0.12 and texto[0] != "{":
        texto = "Por favor, " + texto[0].lower() + texto[1:]
    elif rng.random() < 0.10:
        texto = texto + ", por favor"
    if rng.random() < 0.15:
        texto = texto + "."
    return texto


class Contexto:
    """Estado de un ejemplo: ids nuevos y el vocabulario que puede usar."""

    def __init__(self, rng, entidades, prueba):
        self.rng = rng
        self.entidades = entidades
        self.prueba = prueba
        self.siguiente = 1

    def id_nuevo(self):
        valor = f"c{self.siguiente}"
        self.siguiente += 1
        return valor

    def clase(self, nombre, n_atributos=None, con_metodos=None):
        rng = self.rng
        base = self.entidades[nombre]
        n = n_atributos or rng.randint(2, min(4, len(base)))
        atributos = [{"name": a, "type": t} for a, t in rng.sample(base, n)]
        cantidad = rng.randint(0, 2) if con_metodos is None else con_metodos
        metodos = [{"name": m} for m in rng.sample(METODOS, cantidad)]
        return {"id": self.id_nuevo(), "name": nombre, "attributes": atributos, "methods": metodos}

    def otras(self, excluidas, maximo=2):
        disponibles = [e for e in self.entidades if e not in excluidas]
        cantidad = self.rng.randint(0, maximo)
        return [self.clase(n) for n in self.rng.sample(disponibles, cantidad)]

    def relaciones_previas(self, clases, excluidas=()):
        """A veces el diagrama ya trae una relación entre dos clases que no son el objetivo."""
        candidatas = [c for c in clases if c["id"] not in excluidas]
        if len(candidatas) < 2 or self.rng.random() > 0.3:
            return []
        origen, destino = self.rng.sample(candidatas, 2)
        tipo = self.rng.choice(RELACIONES + ["generalization"])
        return [{"id": "r1", "type": tipo, "sourceId": origen["id"], "targetId": destino["id"]}]

    def redactar(self, operacion, **valores):
        entrenamiento, prueba = PLANTILLAS[operacion]
        plantilla = self.rng.choice(prueba if self.prueba else entrenamiento)
        # El ruido se aplica a la plantilla, no a los nombres: "cliente" y "Cliente" serían clases distintas.
        return ruido(self.rng, plantilla).format(**valores)


def lista_atributos(atributos):
    return ", ".join(f"{a['name']}: {a['type']}" for a in atributos)


def _mezclar(rng, clases):
    clases = list(clases)
    rng.shuffle(clases)
    return clases


def op_crear_clase(cx):
    nombre = cx.rng.choice(list(cx.entidades))
    contexto = cx.otras({nombre}, 3)
    nueva = cx.clase(nombre, con_metodos=0)
    pedido = cx.redactar("crear_clase", C=nombre, lista=lista_atributos(nueva["attributes"]))
    return ({"classes": contexto, "relationships": cx.relaciones_previas(contexto)}, pedido,
            {"classes": [nueva], "relationships": []})


def _con_objetivo(cx, operacion, requisito=None):
    """Diagrama con una clase objetivo (y otras al azar). Devuelve (uml, objetivo)."""
    while True:
        nombre = cx.rng.choice(list(cx.entidades))
        objetivo = cx.clase(nombre)
        if requisito is None or requisito(objetivo):
            break
        cx.siguiente -= 1
    clases = _mezclar(cx.rng, [objetivo] + cx.otras({nombre}, 3))
    return {"classes": clases, "relationships": cx.relaciones_previas(clases, {objetivo["id"]})}, objetivo


def op_agregar_atributo(cx):
    uml, objetivo = _con_objetivo(cx, "agregar_atributo")
    existentes = {a["name"] for a in objetivo["attributes"]}
    nuevo = cx.rng.choice([(a, t) for a, t in cx.entidades[objetivo["name"]] + ATRIBUTOS_EXTRA if a not in existentes])
    pedido = cx.redactar("agregar_atributo", C=objetivo["name"], a=nuevo[0], t=nuevo[1])
    completa = copy.deepcopy(objetivo)
    completa["attributes"].append({"name": nuevo[0], "type": nuevo[1]})
    return uml, pedido, {"classes": [completa], "relationships": []}


def op_agregar_metodo(cx):
    uml, objetivo = _con_objetivo(cx, "agregar_metodo", lambda o: len(o["methods"]) < 3)
    existentes = {m["name"] for m in objetivo["methods"]}
    metodo = cx.rng.choice([m for m in METODOS if m not in existentes])
    pedido = cx.redactar("agregar_metodo", C=objetivo["name"], m=metodo)
    completa = copy.deepcopy(objetivo)
    completa["methods"].append({"name": metodo})
    return uml, pedido, {"classes": [completa], "relationships": []}


def op_editar_tipo(cx):
    uml, objetivo = _con_objetivo(cx, "editar_tipo")
    atributo = cx.rng.choice(objetivo["attributes"])
    nuevo = cx.rng.choice([t for t in TIPOS if t != atributo["type"]])
    pedido = cx.redactar("editar_tipo", C=objetivo["name"], a=atributo["name"], t=nuevo)
    completa = copy.deepcopy(objetivo)
    for a in completa["attributes"]:
        if a["name"] == atributo["name"]:
            a["type"] = nuevo
    return uml, pedido, {"classes": [completa], "relationships": []}


def op_renombrar_atributo(cx):
    uml, objetivo = _con_objetivo(cx, "renombrar_atributo")
    atributo = cx.rng.choice(objetivo["attributes"])
    usados = {a["name"] for a in objetivo["attributes"]}
    nuevo = cx.rng.choice([a for a, _ in ATRIBUTOS_EXTRA if a not in usados])
    pedido = cx.redactar("renombrar_atributo", C=objetivo["name"], a=atributo["name"], b=nuevo)
    completa = copy.deepcopy(objetivo)
    for a in completa["attributes"]:
        if a["name"] == atributo["name"]:
            a["name"] = nuevo
    return uml, pedido, {"classes": [completa], "relationships": []}


def op_eliminar_atributo(cx):
    uml, objetivo = _con_objetivo(cx, "eliminar_atributo", lambda o: len(o["attributes"]) >= 2)
    atributo = cx.rng.choice(objetivo["attributes"])
    pedido = cx.redactar("eliminar_atributo", C=objetivo["name"], a=atributo["name"])
    marca = {"id": objetivo["id"], "name": objetivo["name"],
             "attributes": [{"name": atributo["name"], "type": atributo["type"], "eliminar": True}]}
    return uml, pedido, {"classes": [marca], "relationships": []}


def op_eliminar_metodo(cx):
    uml, objetivo = _con_objetivo(cx, "eliminar_metodo", lambda o: len(o["methods"]) >= 1)
    metodo = cx.rng.choice(objetivo["methods"])
    pedido = cx.redactar("eliminar_metodo", C=objetivo["name"], m=metodo["name"])
    marca = {"id": objetivo["id"], "name": objetivo["name"],
             "methods": [{"name": metodo["name"], "eliminar": True}]}
    return uml, pedido, {"classes": [marca], "relationships": []}


def op_eliminar_clase(cx):
    uml, objetivo = _con_objetivo(cx, "eliminar_clase")
    pedido = cx.redactar("eliminar_clase", C=objetivo["name"])
    marca = {"id": objetivo["id"], "name": objetivo["name"], "eliminar": True}
    return uml, pedido, {"classes": [marca], "relationships": []}


def _dos_clases(cx):
    primera, segunda = cx.rng.sample(list(cx.entidades), 2)
    a, b = cx.clase(primera), cx.clase(segunda)
    clases = _mezclar(cx.rng, [a, b] + cx.otras({primera, segunda}, 2))
    return a, b, clases


def op_relacion(cx):
    a, b, clases = _dos_clases(cx)
    tipo = cx.rng.choice(RELACIONES)
    pedido = cx.redactar("relacion", C=a["name"], D=b["name"], r=NOMBRE_RELACION[tipo])
    relacion = {"type": tipo, "sourceId": a["id"], "targetId": b["id"]}
    return {"classes": clases, "relationships": []}, pedido, {"classes": [], "relationships": [relacion]}


def op_herencia(cx):
    hija, padre, clases = _dos_clases(cx)
    pedido = cx.redactar("herencia", C=hija["name"], D=padre["name"])
    relacion = {"type": "generalization", "sourceId": hija["id"], "targetId": padre["id"]}
    return {"classes": clases, "relationships": []}, pedido, {"classes": [], "relationships": [relacion]}


def op_eliminar_relacion(cx):
    a, b, clases = _dos_clases(cx)
    tipo = cx.rng.choice(RELACIONES + ["generalization"])
    existente = {"id": "r1", "type": tipo, "sourceId": a["id"], "targetId": b["id"]}
    pedido = cx.redactar("eliminar_relacion", C=a["name"], D=b["name"])
    marca = {"id": "r1", "type": tipo, "sourceId": a["id"], "targetId": b["id"], "eliminar": True}
    return {"classes": clases, "relationships": [existente]}, pedido, {"classes": [], "relationships": [marca]}


def op_crear_dos_con_relacion(cx):
    primera, segunda = cx.rng.sample(list(cx.entidades), 2)
    contexto = cx.otras({primera, segunda}, 1)
    a, b = cx.clase(primera, con_metodos=0), cx.clase(segunda, con_metodos=0)
    tipo = cx.rng.choice(RELACIONES)
    pedido = cx.redactar("crear_dos_con_relacion", C=primera, D=segunda, r=NOMBRE_RELACION[tipo])
    relacion = {"type": tipo, "sourceId": a["id"], "targetId": b["id"]}
    return ({"classes": contexto, "relationships": []}, pedido,
            {"classes": [a, b], "relationships": [relacion]})


def op_renombrar_clase(cx):
    uml, objetivo = _con_objetivo(cx, "renombrar_clase")
    usados = {c["name"] for c in uml["classes"]}
    nuevo = cx.rng.choice([n for n in NOMBRES_CLASE_NUEVOS if n not in usados])
    pedido = cx.redactar("renombrar_clase", C=objetivo["name"], N=nuevo)
    completa = copy.deepcopy(objetivo)
    completa["name"] = nuevo
    return uml, pedido, {"classes": [completa], "relationships": []}


def op_agregar_varios_atributos(cx):
    uml, objetivo = _con_objetivo(cx, "agregar_varios_atributos")
    existentes = {a["name"] for a in objetivo["attributes"]}
    candidatos = [(a, t) for a, t in cx.entidades[objetivo["name"]] + ATRIBUTOS_EXTRA if a not in existentes]
    nuevos = [{"name": a, "type": t} for a, t in cx.rng.sample(candidatos, 2)]
    pedido = cx.redactar("agregar_varios_atributos", C=objetivo["name"], lista=lista_atributos(nuevos))
    completa = copy.deepcopy(objetivo)
    completa["attributes"].extend(nuevos)
    return uml, pedido, {"classes": [completa], "relationships": []}


def op_crear_clase_con_metodos(cx):
    nombre = cx.rng.choice(list(cx.entidades))
    contexto = cx.otras({nombre}, 2)
    nueva = cx.clase(nombre, con_metodos=cx.rng.randint(1, 2))
    pedido = cx.redactar("crear_clase_con_metodos", C=nombre, lista=lista_atributos(nueva["attributes"]),
                         metodos=", ".join(m["name"] for m in nueva["methods"]))
    return ({"classes": contexto, "relationships": cx.relaciones_previas(contexto)}, pedido,
            {"classes": [nueva], "relationships": []})


def op_crear_varias_clases(cx):
    nombres = cx.rng.sample(list(cx.entidades), 3)
    nuevas = [cx.clase(n, n_atributos=2, con_metodos=0) for n in nombres]
    descripcion = [f"{c['name']} ({lista_atributos(c['attributes'])})" for c in nuevas]
    clases = f"{descripcion[0]}, {descripcion[1]} y {descripcion[2]}"
    pedido = cx.redactar("crear_varias_clases", clases=clases)
    return {"classes": [], "relationships": []}, pedido, {"classes": nuevas, "relationships": []}


OPERACIONES = {
    "crear_clase": op_crear_clase,
    "agregar_atributo": op_agregar_atributo,
    "agregar_metodo": op_agregar_metodo,
    "editar_tipo": op_editar_tipo,
    "renombrar_atributo": op_renombrar_atributo,
    "eliminar_atributo": op_eliminar_atributo,
    "eliminar_metodo": op_eliminar_metodo,
    "eliminar_clase": op_eliminar_clase,
    "relacion": op_relacion,
    "herencia": op_herencia,
    "eliminar_relacion": op_eliminar_relacion,
    "crear_dos_con_relacion": op_crear_dos_con_relacion,
    "renombrar_clase": op_renombrar_clase,
    "agregar_varios_atributos": op_agregar_varios_atributos,
    "crear_clase_con_metodos": op_crear_clase_con_metodos,
    "crear_varias_clases": op_crear_varias_clases,
}


def generar(rng, cantidad, entidades, prueba):
    nombres = sorted(OPERACIONES)
    ejemplos = []
    for indice in range(cantidad):
        operacion = nombres[indice % len(nombres)]  # reparto parejo entre operaciones
        cx = Contexto(rng, entidades, prueba)
        uml, pedido, esperado = OPERACIONES[operacion](cx)
        ejemplos.append({"op": operacion, "uml": uml, "pedido": pedido, "esperado": esperado})
    rng.shuffle(ejemplos)
    return ejemplos


def escribir_jsonl(ruta, filas):
    with open(ruta, "w", encoding="utf-8") as archivo:
        for fila in filas:
            archivo.write(json.dumps(fila, ensure_ascii=False) + "\n")


def sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--salida", default="ml/data/out")
    parser.add_argument("--train", type=int, default=1500)
    parser.add_argument("--valid", type=int, default=150)
    parser.add_argument("--test", type=int, default=200)
    parser.add_argument("--semilla", type=int, default=42)
    args = parser.parse_args()

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.semilla)

    conjuntos = {
        "train": generar(rng, args.train, ENTIDADES, prueba=False),
        "valid": generar(rng, args.valid, ENTIDADES, prueba=False),
        # La prueba mezcla entidades nuevas con las de entrenamiento, y solo usa redacciones reservadas.
        "test": generar(rng, args.test, {**ENTIDADES, **ENTIDADES_PRUEBA}, prueba=True),
    }

    # Sin fugas: ningún pedido (con su diagrama) de la prueba aparece en entrenamiento.
    vistos = {(json.dumps(e["uml"], sort_keys=True), e["pedido"]) for n in ("train", "valid") for e in conjuntos[n]}
    repetidos = [e for e in conjuntos["test"] if (json.dumps(e["uml"], sort_keys=True), e["pedido"]) in vistos]
    if repetidos:
        raise SystemExit(f"Fuga: {len(repetidos)} ejemplos de prueba aparecen en entrenamiento")

    for nombre, ejemplos in conjuntos.items():
        escribir_jsonl(salida / f"{nombre}.jsonl", [
            {"messages": conversacion(e["uml"], e["pedido"], e["esperado"])} for e in ejemplos
        ])
    escribir_jsonl(salida / "test_meta.jsonl", conjuntos["test"])

    manifiesto = {
        "semilla": args.semilla,
        "conteos": {nombre: len(ejemplos) for nombre, ejemplos in conjuntos.items()},
        "operaciones": {nombre: dict(Counter(e["op"] for e in ejemplos)) for nombre, ejemplos in conjuntos.items()},
        "entidades_entrenamiento": sorted(ENTIDADES),
        "entidades_solo_prueba": sorted(ENTIDADES_PRUEBA),
        "sin_fugas_train_valid_vs_test": True,
        "sha256": {p.name: sha256(p) for p in sorted(salida.glob("*.jsonl"))},
    }
    (salida / "MANIFEST.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifiesto["conteos"]), "->", salida)


if __name__ == "__main__":
    main()
