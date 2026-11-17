from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree as ET

from .uml_kinds import VISIBILITY_FROM_XMI, VISIBILITY_TO_XMI, kind_of


XMI_NS = "http://schema.omg.org/spec/XMI/2.1"
UML_NS = "http://www.eclipse.org/uml2/5.0.0/UML"
CASE_LAYOUT_NS = "https://software1-case.local/xmi/layout/1.0"

# Tipo de relación del editor <-> valor de `aggregation` de UML/XMI.
EA_AGGREGATION_OF = {"aggregation": "shared", "composition": "composite"}
AGGREGATION_RELATIONS = {value: relation for relation, value in EA_AGGREGATION_OF.items()}

ET.register_namespace("xmi", XMI_NS)
ET.register_namespace("uml", UML_NS)
ET.register_namespace("case", CASE_LAYOUT_NS)


class XMIError(ValueError):
    """Controlled error raised when XMI cannot be processed safely."""


def _xmi_attr(name: str) -> str:
    return f"{{{XMI_NS}}}{name}"


def _local_name(value: str) -> str:
    if "}" in value:
        return value.rsplit("}", 1)[1]

    if ":" in value:
        return value.rsplit(":", 1)[1]

    return value


def _attribute_by_local_name(element: ET.Element, name: str, default=None):
    for key, value in element.attrib.items():
        if _local_name(key) == name:
            return value

    return default


def _xmi_id(element: ET.Element) -> str | None:
    return (
        element.attrib.get(_xmi_attr("id"))
        or _attribute_by_local_name(element, "id")
    )


def _xmi_type(element: ET.Element) -> str:
    value = element.attrib.get(_xmi_attr("type"))

    if value:
        return value

    for key, candidate in element.attrib.items():
        if _local_name(key) == "type" and candidate.startswith("uml:"):
            return candidate

    return ""


def _uml_type_name(element: ET.Element) -> str:
    value = _xmi_type(element)

    if ":" in value:
        return value.split(":", 1)[1]

    return value


def _new_id(seed: str) -> str:
    """
    Genera un identificador estable para una misma semilla.

    XMI export debe ser determinista: el mismo modelo de entrada
    debe producir exactamente los mismos identificadores auxiliares.
    """
    return f"generated-{uuid5(NAMESPACE_URL, seed)}"


def _normalize_xml_input(xml_data: Any) -> bytes:
    if hasattr(xml_data, "read"):
        xml_data = xml_data.read()

    if isinstance(xml_data, str):
        raw = xml_data.encode("utf-8")
    elif isinstance(xml_data, bytes):
        raw = xml_data
    else:
        raise XMIError("El contenido XMI debe ser texto, bytes o un archivo.")

    lowered = raw.lower()

    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise XMIError(
            "El XMI contiene DOCTYPE o ENTITY y fue rechazado por seguridad."
        )

    return raw


def _validate_model(uml_json: dict[str, Any]) -> None:
    if not isinstance(uml_json, dict):
        raise XMIError("El modelo UML debe ser un objeto JSON.")

    classes = uml_json.get("classes", [])
    relationships = uml_json.get("relationships", [])

    if not isinstance(classes, list):
        raise XMIError("'classes' debe ser una lista.")

    if not isinstance(relationships, list):
        raise XMIError("'relationships' debe ser una lista.")

    used_ids: set[str] = set()

    for index, uml_class in enumerate(classes):
        if not isinstance(uml_class, dict):
            raise XMIError(
                f"La clase en posición {index} debe ser un objeto JSON."
            )

        class_id = uml_class.get("id")

        if class_id:
            class_id = str(class_id)

            if class_id in used_ids:
                raise XMIError(
                    f"Identificador XMI duplicado: {class_id}"
                )

            used_ids.add(class_id)

        attributes = uml_class.get("attributes", [])

        if not isinstance(attributes, list):
            raise XMIError(
                f"'attributes' de la clase {index} debe ser una lista."
            )

        for attribute_index, attribute in enumerate(attributes):
            if not isinstance(attribute, dict):
                raise XMIError(
                    "El atributo "
                    f"{attribute_index} de la clase {index} "
                    "debe ser un objeto JSON."
                )

        methods = uml_class.get("methods", [])

        if not isinstance(methods, list):
            raise XMIError(
                f"'methods' de la clase {index} debe ser una lista."
            )

        for method_index, method in enumerate(methods):
            if not isinstance(method, dict):
                raise XMIError(
                    "El método "
                    f"{method_index} de la clase {index} "
                    "debe ser un objeto JSON."
                )

    for index, relationship in enumerate(relationships):
        if not isinstance(relationship, dict):
            raise XMIError(
                f"La relación en posición {index} debe ser un objeto JSON."
            )

        relationship_id = relationship.get("id")

        if relationship_id:
            relationship_id = str(relationship_id)

            if relationship_id in used_ids:
                raise XMIError(
                    f"Identificador XMI duplicado: {relationship_id}"
                )

            used_ids.add(relationship_id)

        labels = relationship.get("labels", [])

        if labels is not None and not isinstance(labels, list):
            raise XMIError(
                f"'labels' de la relación {index} debe ser una lista."
            )


UML_21_PRIMITIVE_HREF = "http://schema.omg.org/spec/UML/2.1/uml.xml#"

UML_PRIMITIVE_TYPES = {
    "string": "String",
    "str": "String",
    "int": "Integer",
    "integer": "Integer",
    "bool": "Boolean",
    "boolean": "Boolean",
    "float": "Real",
    "double": "Real",
    "real": "Real",
    "unlimitednatural": "UnlimitedNatural",
}


def _append_uml_type(element: ET.Element, type_name: str, class_ids: dict[str, str] | None = None) -> None:
    """Escribe el tipo de un atributo o parámetro.

    Los tipos primitivos van como `<type href=…#Real>` (Enterprise Architect los entiende así). Un tipo que es una clase del diagrama se
    referencia por el id de esa clase (así EA lo enlaza a la clase); cualquier otro se deja con su nombre. `void` no es un tipo de UML:
    un retorno sin tipo ya significa «no devuelve nada».
    """
    type_name = str(type_name or "").strip()

    if not type_name or type_name.lower() == "void":
        return

    primitive_name = UML_PRIMITIVE_TYPES.get(type_name.lower())

    if primitive_name:
        ET.SubElement(
            element,
            "type",
            {
                _xmi_attr("type"): "uml:PrimitiveType",
                "href": f"{UML_21_PRIMITIVE_HREF}{primitive_name}",
            },
        )
        return

    # Un tipo que es una clase del diagrama se referencia por su id; cualquier otro conserva su nombre.
    element.set("type", (class_ids or {}).get(type_name, type_name))


def _parse_parameters(parameters: str) -> list[tuple[str, str]]:
    if not parameters:
        return []

    parsed: list[tuple[str, str]] = []

    for raw_parameter in parameters.split(","):
        raw_parameter = raw_parameter.strip()

        if not raw_parameter:
            continue

        if ":" in raw_parameter:
            name, parameter_type = raw_parameter.split(":", 1)
            parsed.append((name.strip(), parameter_type.strip()))
        else:
            parsed.append((raw_parameter, ""))

    return parsed


def _append_multiplicity(end: ET.Element, label: str | None, id_seed: str) -> None:
    if label is None:
        return

    label = str(label).strip()

    if not label:
        return

    if ".." in label:
        lower, upper = label.split("..", 1)
        lower = lower.strip()
        upper = upper.strip()
    elif label == "*":
        lower = "0"
        upper = "*"
    else:
        lower = label
        upper = label

    ET.SubElement(
        end,
        "lowerValue",
        {
            _xmi_attr("type"): "uml:LiteralInteger",
            _xmi_attr("id"): _new_id(f"{id_seed}-lower"),
            "value": lower,
        },
    )

    upper_type = (
        "uml:LiteralUnlimitedNatural"
        if upper == "*"
        else "uml:LiteralInteger"
    )

    ET.SubElement(
        end,
        "upperValue",
        {
            _xmi_attr("type"): upper_type,
            _xmi_attr("id"): _new_id(f"{id_seed}-upper"),
            "value": upper,
        },
    )


def _read_multiplicity(end: ET.Element) -> str:
    direct_lower = end.attrib.get("lower")
    direct_upper = end.attrib.get("upper")

    lower = direct_lower
    upper = direct_upper

    for child in end:
        child_name = _local_name(child.tag)

        if child_name == "lowerValue":
            lower = child.attrib.get("value", lower)

        elif child_name == "upperValue":
            upper = child.attrib.get("value", upper)

    # Enterprise Architect serializes UnlimitedNatural "*" as -1.
    if upper == "-1":
        upper = "*"

    if lower is None and upper is None:
        return "1"

    if lower is None:
        if upper == "*":
            return "*"
        return str(upper)

    if upper is None:
        return str(lower)

    if str(lower) == str(upper):
        return str(lower)

    return f"{lower}..{upper}"


XMI_TYPE_OF_KIND = {
    "class": "uml:Class",
    "abstract": "uml:Class",
    "interface": "uml:Interface",
    "enumeration": "uml:Enumeration",
}


def _set_visibility(element: ET.Element, member: dict[str, Any]) -> None:
    """Escribe la visibilidad UML (`public`, `private`, `protected`, `package`) del atributo o método, si la tiene."""
    visibility = VISIBILITY_TO_XMI.get(member.get("visibility"))

    if visibility:
        element.set("visibility", visibility)


def _visibility_of(element: ET.Element, default: str | None = None) -> dict[str, str]:
    """La visibilidad de un atributo o método. Si el XMI no la dice, vale `default`: en un XMI de Enterprise Architect una visibilidad ausente es la pública."""
    sign = VISIBILITY_FROM_XMI.get(element.attrib.get("visibility", "")) or default

    return {"visibility": sign} if sign else {}


def export_uml_to_xmi(uml_json: dict[str, Any]) -> bytes:
    """
    Convert the internal CASE UML JSON format into UML/XMI 2.1 XML.
    """
    _validate_model(uml_json)

    root = ET.Element(
        f"{{{XMI_NS}}}XMI",
        {
            f"{{{XMI_NS}}}version": "2.1",
        },
    )

    model = ET.SubElement(
        root,
        f"{{{UML_NS}}}Model",
        {
            _xmi_attr("id"): _new_id("model"),
            "name": "CASE Model",
        },
    )

    class_elements: dict[str, ET.Element] = {}
    layout_entries: list[dict[str, Any]] = []
    relationship_ids: list[str] = []

    # Nombre de cada clase -> su id, para que un atributo o parámetro «de tipo Cliente» quede enlazado a la clase Cliente.
    class_ids_by_name: dict[str, str] = {}
    for class_index, uml_class in enumerate(uml_json.get("classes", [])):
        class_ids_by_name.setdefault(
            str(uml_class.get("name") or f"Class{class_index + 1}"),
            str(uml_class.get("id") or _new_id(f"class-{class_index}")),
        )

    for class_index, uml_class in enumerate(uml_json.get("classes", [])):
        class_id = str(
            uml_class.get("id")
            or _new_id(f"class-{class_index}")
        )

        kind = kind_of(uml_class)

        class_element = ET.SubElement(
            model,
            "packagedElement",
            {
                _xmi_attr("type"): XMI_TYPE_OF_KIND[kind],
                _xmi_attr("id"): class_id,
                "name": str(
                    uml_class.get("name")
                    or f"Class{class_index + 1}"
                ),
            },
        )

        if kind == "abstract":
            class_element.set("isAbstract", "true")

        class_elements[class_id] = class_element

        position = uml_class.get("position")
        size = uml_class.get("size")

        if isinstance(position, dict) or isinstance(size, dict):
            layout_entries.append(
                {
                    "class_id": class_id,
                    "position": position if isinstance(position, dict) else {},
                    "size": size if isinstance(size, dict) else {},
                }
            )

        for attribute_index, attribute in enumerate(
            uml_class.get("attributes", [])
        ):
            if kind == "enumeration":
                # Las literales de una enumeración no tienen tipo ni visibilidad.
                ET.SubElement(
                    class_element,
                    "ownedLiteral",
                    {
                        _xmi_attr("type"): "uml:EnumerationLiteral",
                        _xmi_attr("id"): _new_id(
                            f"{class_id}-literal-{attribute_index}"
                        ),
                        "name": str(attribute.get("name", "")),
                    },
                )
                continue

            attribute_element = ET.SubElement(
                class_element,
                "ownedAttribute",
                {
                    _xmi_attr("type"): "uml:Property",
                    _xmi_attr("id"): _new_id(
                        f"{class_id}-attribute-{attribute_index}"
                    ),
                    "name": str(attribute.get("name", "")),
                    # Sin esto EA, al no ver `isUnique`, dibuja cada atributo con «{bag}».
                    "isOrdered": "false",
                    "isUnique": "true",
                },
            )

            _set_visibility(attribute_element, attribute)

            _append_uml_type(
                attribute_element,
                str(attribute.get("type", "")),
                class_ids_by_name,
            )

        for method_index, method in enumerate(
            uml_class.get("methods", [])
        ):
            operation = ET.SubElement(
                class_element,
                "ownedOperation",
                {
                    _xmi_attr("type"): "uml:Operation",
                    _xmi_attr("id"): _new_id(
                        f"{class_id}-operation-{method_index}"
                    ),
                    "name": str(method.get("name", "")),
                },
            )

            _set_visibility(operation, method)

            for parameter_index, (
                parameter_name,
                parameter_type,
            ) in enumerate(
                _parse_parameters(
                    str(method.get("parameters", ""))
                )
            ):
                parameter_data = {
                    _xmi_attr("type"): "uml:Parameter",
                    _xmi_attr("id"): _new_id(
                        f"{class_id}-parameter-{method_index}-{parameter_index}"
                    ),
                    "name": parameter_name,
                    "direction": "in",
                }

                parameter_element = ET.SubElement(
                    operation,
                    "ownedParameter",
                    parameter_data,
                )
                _append_uml_type(parameter_element, parameter_type, class_ids_by_name)

            return_type = str(
                method.get("returnType", "")
                or ""
            ).strip()

            if return_type and return_type.lower() != "void":
                return_element = ET.SubElement(
                    operation,
                    "ownedParameter",
                    {
                        _xmi_attr("type"): "uml:Parameter",
                        _xmi_attr("id"): _new_id(
                            f"{class_id}-return-{method_index}"
                        ),
                        "name": "return",
                        "direction": "return",
                    },
                )
                _append_uml_type(return_element, return_type, class_ids_by_name)

    supported_relationships = {
        "association",
        "aggregation",
        "composition",
        "generalization",
        "dependency",
    }

    for relation_index, relationship in enumerate(
        uml_json.get("relationships", [])
    ):
        relation_type = str(
            relationship.get("type", "association")
        ).lower()

        if relation_type not in supported_relationships:
            raise XMIError(
                f"Tipo de relación UML no soportado: {relation_type}"
            )

        relation_id = str(
            relationship.get("id")
            or _new_id(f"relationship-{relation_index}")
        )
        relationship_ids.append(relation_id)

        source_id = str(
            relationship.get("sourceId", "")
        )
        target_id = str(
            relationship.get("targetId", "")
        )

        if source_id not in class_elements:
            raise XMIError(
                f"La relación {relation_id} referencia "
                f"sourceId inexistente: {source_id}"
            )

        if target_id not in class_elements:
            raise XMIError(
                f"La relación {relation_id} referencia "
                f"targetId inexistente: {target_id}"
            )

        labels = relationship.get("labels") or []

        if relation_type in {
            "association",
            "aggregation",
            "composition",
        }:
            association = ET.SubElement(
                model,
                "packagedElement",
                {
                    _xmi_attr("type"): "uml:Association",
                    _xmi_attr("id"): relation_id,
                },
            )

            source_end_id = _new_id(
                f"{relation_id}-source"
            )
            target_end_id = _new_id(
                f"{relation_id}-target"
            )

            source_end = ET.SubElement(
                association,
                "ownedEnd",
                {
                    _xmi_attr("type"): "uml:Property",
                    _xmi_attr("id"): source_end_id,
                    "type": source_id,
                },
            )

            # En UML (y en Enterprise Architect) `aggregation` va en el extremo cuyo tipo es la PARTE: el destino. El origen es el todo, el del rombo.
            target_end_data = {
                _xmi_attr("type"): "uml:Property",
                _xmi_attr("id"): target_end_id,
                "type": target_id,
            }

            if relation_type in EA_AGGREGATION_OF:
                target_end_data["aggregation"] = EA_AGGREGATION_OF[relation_type]

            target_end = ET.SubElement(
                association,
                "ownedEnd",
                target_end_data,
            )

            association.set(
                "memberEnd",
                f"{source_end_id} {target_end_id}",
            )

            _append_multiplicity(
                source_end,
                labels[0] if len(labels) > 0 else None,
                f"{relation_id}-source",
            )

            _append_multiplicity(
                target_end,
                labels[1] if len(labels) > 1 else None,
                f"{relation_id}-target",
            )

        elif relation_type == "generalization":
            ET.SubElement(
                class_elements[source_id],
                "generalization",
                {
                    _xmi_attr("type"): "uml:Generalization",
                    _xmi_attr("id"): relation_id,
                    "general": target_id,
                },
            )

        elif relation_type == "dependency":
            ET.SubElement(
                model,
                "packagedElement",
                {
                    _xmi_attr("type"): "uml:Dependency",
                    _xmi_attr("id"): relation_id,
                    "client": source_id,
                    "supplier": target_id,
                },
            )

    # El diagrama de EA va PRIMERO entre las extensiones: con otra extensión delante (la del CASE) EA importa las clases pero no dibuja el diagrama.
    if class_elements:
        _append_ea_diagram(root, model, uml_json, relationship_ids)

    # Información visual propia del CASE.
    # Herramientas UML externas pueden ignorar esta extensión sin afectar
    # las clases, atributos, operaciones ni relaciones UML estándar.
    if layout_entries:
        extension = ET.SubElement(
            root,
            f"{{{XMI_NS}}}Extension",
            {
                "extender": "software1-case",
            },
        )

        layout = ET.SubElement(
            extension,
            f"{{{CASE_LAYOUT_NS}}}layout",
        )

        for entry in layout_entries:
            attrs = {
                _xmi_attr("idref"): entry["class_id"],
            }

            position = entry["position"]
            size = entry["size"]

            if position.get("x") is not None:
                attrs["x"] = str(position["x"])

            if position.get("y") is not None:
                attrs["y"] = str(position["y"])

            if size.get("width") is not None:
                attrs["width"] = str(size["width"])

            if size.get("height") is not None:
                attrs["height"] = str(size["height"])

            ET.SubElement(
                layout,
                f"{{{CASE_LAYOUT_NS}}}element",
                attrs,
            )

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )


# Un diagrama de clases que Enterprise Architect dibuja al importar el archivo. EA lo lee de la extensión `xmi:Extension extender="Enterprise Architect"`
# (la misma que escribe al exportar): el XMI estándar solo lleva el modelo, no el dibujo. Cada clase va con la posición que tiene en el editor.
#
# Condición que EA exige y que se comprobó con EA 17.2 (ImportPackageXMI con diagramas): el archivo debe presentarse con
# `<xmi:Documentation exporter="Enterprise Architect">`. Sin esa línea EA importa las clases y deja la extensión sin leer (no dibuja nada); no importan ni los ids
# ni el espacio de nombres. El `exporterID` propio avisa de que el archivo lo escribió el CASE: al volver a leerlo no se trata como un export de EA.
EA_EXPORTER = "Enterprise Architect"
EA_EXPORTER_ID = "software1-case"
EA_DIAGRAM_STYLE = (
    "ShowPrivate=1;ShowProtected=1;ShowPublic=1;HideRelationships=0;Locked=0;Border=1;HighlightForeign=1;PackageContents=1;SequenceNotes=0;"
    "ScalePrintImage=0;PPgs.cx=0;PPgs.cy=0;DocSize.cx=800;DocSize.cy=1100;ShowDetails=0;Orientation=P;Zoom=100;ShowTags=0;OpParams=1;"
    "VisibleAttributeDetail=0;ShowOpRetType=1;ShowIcons=1;CollabNums=0;HideProps=0;ShowReqs=0;ShowCons=0;PaperSize=256;HideParents=0;UseAlias=0;"
    "HideAtts=0;HideOps=0;HideStereo=0;HideElemStereo=0;ShowTests=0;ShowMaint=0;ConnectorNotation=UML 2.1;ExplicitNavigability=0;ShowShape=1;"
    "AllDockable=0;AdvancedElementProps=1;AdvancedFeatureProps=1;AdvancedConnectorProps=1;m_bElementClassifier=1;SPT=1;ShowNotes=0;"
    "SuppressBrackets=0;SuppConnectorLabels=0;PrintPageHeadFoot=0;ShowAsList=0;"
)
EA_GRID_COLUMNS = 3
EA_MIN_WIDTH = 210
EA_MIN_HEIGHT = 100
EA_LINE_HEIGHT = 17


def _ea_box(uml_class: dict[str, Any], index: int) -> tuple[int, int, int, int]:
    """La caja de una clase en el diagrama de EA: la posición del editor, o una cuadrícula si la clase no la tiene. La altura alcanza para todas sus líneas."""
    members = len(uml_class.get("attributes") or []) + len(uml_class.get("methods") or [])
    size = uml_class.get("size") if isinstance(uml_class.get("size"), dict) else {}
    position = uml_class.get("position") if isinstance(uml_class.get("position"), dict) else {}
    width = max(EA_MIN_WIDTH, int(size.get("width") or 0))
    height = max(EA_MIN_HEIGHT, int(size.get("height") or 0), 64 + EA_LINE_HEIGHT * members)
    if position.get("x") is not None and position.get("y") is not None:
        left, top = int(position["x"]), int(position["y"])
    else:
        left = 40 + (index % EA_GRID_COLUMNS) * (EA_MIN_WIDTH + 90)
        top = 40 + (index // EA_GRID_COLUMNS) * (EA_MIN_HEIGHT + 130)
    left, top = max(left, 10), max(top, 10)
    return left, top, left + width, top + height


EA_SCOPE_OF = {"public": "Public", "private": "Private", "protected": "Protected", "package": "Package"}
EA_TYPE_NAME_OF = {"uml:Class": "Class", "uml:Interface": "Interface", "uml:Enumeration": "Enumeration"}


def _ea_type_name(holder: ET.Element, names: dict[str, str]) -> str:
    """El tipo de un parámetro o retorno como lo escribe EA en su extensión: `Real` para un primitivo, el nombre de la clase si el tipo es una clase."""
    child = next((c for c in holder if c.tag == "type"), None)
    if child is not None and child.attrib.get("href"):
        return child.attrib["href"].rsplit("#", 1)[-1]
    value = holder.attrib.get("type", "")
    return names.get(value, value)


def _append_ea_class_elements(parent: ET.Element, model: ET.Element, model_id: str, names: dict[str, str]) -> None:
    """Un `element` por clase, interfaz o enumeración, con lo que EA, al creerse el exportador, ya no deduce del cuerpo del XMI: el tipo del elemento y el tipo de retorno de cada operación."""
    for index, class_element in enumerate(c for c in model if c.tag == "packagedElement" and c.attrib.get(_xmi_attr("type")) in EA_TYPE_NAME_OF):
        xmi_type = class_element.attrib[_xmi_attr("type")]
        type_name = EA_TYPE_NAME_OF[xmi_type]
        is_abstract = class_element.attrib.get("isAbstract") == "true" or xmi_type == "uml:Interface"
        element = ET.SubElement(
            parent,
            "element",
            {_xmi_attr("idref"): class_element.attrib[_xmi_attr("id")], _xmi_attr("type"): xmi_type, "name": class_element.attrib.get("name", ""), "scope": "public"},
        )
        ET.SubElement(element, "model", {"package": model_id, "tpos": "0", "ea_eleType": "element"})
        ET.SubElement(
            element,
            "properties",
            {"isSpecification": "false", "sType": type_name, "nType": "0", "scope": "public", "isRoot": "false", "isLeaf": "false", "isAbstract": str(is_abstract).lower()},
        )
        operations = [o for o in class_element if o.tag == "ownedOperation"]
        if operations:
            operations_element = ET.SubElement(element, "operations")
            for operation in operations:
                scope = EA_SCOPE_OF.get(operation.attrib.get("visibility", "public"), "Public")
                operation_element = ET.SubElement(operations_element, "operation", {_xmi_attr("idref"): operation.attrib[_xmi_attr("id")], "name": operation.attrib.get("name", ""), "scope": scope})
                returned = next((p for p in operation if p.tag == "ownedParameter" and p.attrib.get("direction") == "return"), None)
                if returned is not None:
                    ET.SubElement(operation_element, "type", {"type": _ea_type_name(returned, names)})


def _append_ea_connectors(parent: ET.Element, uml_json: dict[str, Any], relationship_ids: list[str], names_by_class_id: dict[str, str]) -> None:
    """Un `connector` por asociación, agregación o composición: sin él EA, al leer el archivo como un export suyo, deja caer la relación (la herencia y la dependencia sí llegan)."""
    for relation_id, relationship in zip(relationship_ids, uml_json.get("relationships", [])):
        relation_type = str(relationship.get("type", "association")).lower()
        if relation_type not in ("association", "aggregation", "composition"):
            continue
        labels = relationship.get("labels") or []
        source_id, target_id = str(relationship.get("sourceId", "")), str(relationship.get("targetId", ""))
        connector = ET.SubElement(parent, "connector", {_xmi_attr("idref"): relation_id})
        for tag, class_id, label, aggregation in (
            ("source", source_id, labels[0] if len(labels) > 0 else "", EA_AGGREGATION_OF.get(relation_type, "none")),
            ("target", target_id, labels[1] if len(labels) > 1 else "", "none"),
        ):
            end = ET.SubElement(connector, tag, {_xmi_attr("idref"): class_id})
            ET.SubElement(end, "model", {"type": "Class", "name": names_by_class_id.get(class_id, "")})
            ET.SubElement(end, "role", {"visibility": "Public"})
            end_type = {"aggregation": aggregation}
            if label:
                end_type = {"multiplicity": str(label), **end_type}
            ET.SubElement(end, "type", end_type)
            ET.SubElement(end, "modifiers", {"isOrdered": "false", "isNavigable": "false"})
            ET.SubElement(end, "style", {"value": "Derived=0;Union=0;Owned=0;Navigable=Unspecified;"})
        ET.SubElement(connector, "properties", {"ea_type": "Association", "direction": "Unspecified"})
        ET.SubElement(connector, "appearance", {"linemode": "3", "linecolor": "0", "linewidth": "0", "seqno": "0", "headStyle": "0", "lineStyle": "0"})
        labels_attrs = {}
        if len(labels) > 0 and labels[0]:
            labels_attrs["lb"] = str(labels[0])
        if len(labels) > 1 and labels[1]:
            labels_attrs["rb"] = str(labels[1])
        ET.SubElement(connector, "labels", labels_attrs)


def _append_ea_diagram(root: ET.Element, model: ET.Element, uml_json: dict[str, Any], relationship_ids: list[str]) -> None:
    classes = uml_json.get("classes", [])
    documentation = ET.Element(
        f"{{{XMI_NS}}}Documentation",
        {"exporter": EA_EXPORTER, "exporterVersion": "6.5", "exporterID": EA_EXPORTER_ID},
    )
    root.insert(0, documentation)
    extension = ET.SubElement(root, f"{{{XMI_NS}}}Extension", {"extender": EA_EXPORTER, "extenderID": "6.5"})
    model_id = model.attrib.get(_xmi_attr("id"), "")
    names_by_class_id = {c.attrib[_xmi_attr("id")]: c.attrib.get("name", "") for c in model if c.tag == "packagedElement" and _xmi_attr("id") in c.attrib}
    _append_ea_class_elements(ET.SubElement(extension, "elements"), model, model_id, names_by_class_id)
    _append_ea_connectors(ET.SubElement(extension, "connectors"), uml_json, relationship_ids, names_by_class_id)
    diagrams = ET.SubElement(extension, "diagrams")
    diagram = ET.SubElement(diagrams, "diagram", {_xmi_attr("id"): _new_id("ea-diagram")})
    ET.SubElement(diagram, "model", {"package": model_id, "localID": "1", "owner": model_id, "tpos": "0"})
    ET.SubElement(diagram, "properties", {"name": "Diagrama de clases", "type": "Class"})
    ET.SubElement(diagram, "project", {"version": "1"})
    ET.SubElement(diagram, "style1", {"value": EA_DIAGRAM_STYLE})
    ET.SubElement(diagram, "style2")
    ET.SubElement(diagram, "extendedProperties")
    ET.SubElement(diagram, "xrefs")
    elements = ET.SubElement(diagram, "elements")
    for index, uml_class in enumerate(classes):
        left, top, right, bottom = _ea_box(uml_class, index)
        class_id = str(uml_class.get("id") or _new_id(f"class-{index}"))
        ET.SubElement(
            elements,
            "element",
            {
                "geometry": f"Left={left};Top={top};Right={right};Bottom={bottom};",
                "subject": class_id,
                "seqno": str(index + 1),
            },
        )
    for relation_id in relationship_ids:
        ET.SubElement(elements, "element", {"geometry": "SX=0;SY=0;EX=0;EY=0;Path=;", "subject": relation_id, "style": ";Hidden=0;"})


# Las clases (y los tipos) de un XMI cuelgan de `packagedElement` (UML 2.1 en adelante) o de `ownedMember` (el XMI 2.1 «UML 2.0» de Enterprise Architect).
# En ese mismo XMI 2.0 las dependencias cuelgan de `ownedElement`.
PACKAGED_TAGS = ("packagedElement", "ownedMember", "ownedElement")


class _ReadContext:
    """Lo que hace falta saber de todo el documento para leer bien un tipo o una visibilidad.

    * `names`: nombre de cada elemento por su id. Enterprise Architect enlaza los tipos por id (`type="EAnone_void"`, o el id de una clase): hay que
      volver al nombre.
    * `extension_types`: el nombre del tipo que EA guarda en su extensión (`properties type="double"`), porque en el cuerpo del XMI a veces deja
      un tipo genérico (`UnlimitedNatural`) en lugar del que el usuario eligió.
    * `default_visibility`: lo que significa una visibilidad ausente. En un XMI de EA es la pública (EA solo escribe las demás).
    """

    def __init__(self, root: ET.Element | None = None):
        self.names: dict[str, str] = {}
        self.extension_types: dict[str, str] = {}
        self.default_visibility: str | None = None

        if root is None:
            return

        for element in root.iter():
            local_name = _local_name(element.tag)

            if local_name in PACKAGED_TAGS:
                element_id, name = _xmi_id(element), element.attrib.get("name")
                if element_id and name:
                    self.names[element_id] = name

            elif local_name == "Documentation":
                is_ea = str(element.attrib.get("exporter", "")).strip().lower() == EA_EXPORTER.lower()
                if is_ea and element.attrib.get("exporterID") != EA_EXPORTER_ID:
                    self.default_visibility = "+"

            elif local_name in ("attribute", "parameter"):
                idref = element.attrib.get(_xmi_attr("idref"))
                properties = next((child for child in element if _local_name(child.tag) == "properties"), None)
                if idref and properties is not None and properties.attrib.get("type"):
                    self.extension_types[idref] = properties.attrib["type"]

            elif local_name == "operation":
                idref = element.attrib.get(_xmi_attr("idref"))
                returned = next((child for child in element if _local_name(child.tag) == "type"), None)
                if idref and returned is not None and returned.attrib.get("type"):
                    self.extension_types[idref] = returned.attrib["type"]

    def resolve(self, value: str) -> str:
        return self.names.get(value, value)


def _read_attribute_type(element: ET.Element, context: _ReadContext | None = None) -> str:
    context = context or _ReadContext()
    direct_type = element.attrib.get("type")

    if direct_type:
        return context.resolve(direct_type)

    for child in element:
        if _local_name(child.tag) != "type":
            continue

        href = child.attrib.get("href", "")

        if "#" in href:
            return context.resolve(href.rsplit("#", 1)[1])

        idref = (
            child.attrib.get(_xmi_attr("idref"))
            or child.attrib.get("idref")
        )

        if idref:
            return context.resolve(idref)

        child_id = _xmi_id(child)

        if child_id:
            return context.resolve(child_id)

    return ""


def _parse_class(
    class_element: ET.Element,
    fallback_seed: str = "0",
    context: _ReadContext | None = None,
) -> dict[str, Any]:
    context = context or _ReadContext()
    class_id = _xmi_id(class_element) or _new_id(
        f"import-class-{fallback_seed}-{class_element.attrib.get('name', '')}"
    )

    attributes = []
    methods = []

    for child in class_element:
        child_name = _local_name(child.tag)

        if child_name == "ownedLiteral":
            attributes.append(
                {
                    "name": child.attrib.get("name", ""),
                    "type": "",
                }
            )

        elif child_name == "ownedAttribute":
            if child.attrib.get("association"):
                continue

            attributes.append(
                {
                    "name": child.attrib.get("name", ""),
                    # El tipo que EA guarda en su extensión es el que el usuario eligió; el del cuerpo puede ser uno genérico.
                    "type": context.extension_types.get(_xmi_id(child) or "") or _read_attribute_type(child, context),
                    **_visibility_of(child, context.default_visibility),
                }
            )

        elif child_name == "ownedOperation":
            parameters = []
            return_type = ""

            for parameter in child:
                if _local_name(parameter.tag) != "ownedParameter":
                    continue

                direction = parameter.attrib.get(
                    "direction",
                    "in",
                )

                parameter_type = context.extension_types.get(
                    _xmi_id(parameter) or ""
                ) or _read_attribute_type(
                    parameter,
                    context,
                )

                if direction == "return":
                    return_type = parameter_type
                    continue

                parameter_name = parameter.attrib.get(
                    "name",
                    "",
                )

                if parameter_name and parameter_type:
                    parameters.append(
                        f"{parameter_name}: {parameter_type}"
                    )
                elif parameter_name:
                    parameters.append(parameter_name)
                elif parameter_type:
                    parameters.append(parameter_type)

            # Si el cuerpo no dice qué devuelve, la extensión de EA sí (`void`, `double`…).
            return_type = return_type or context.extension_types.get(_xmi_id(child) or "", "")

            methods.append(
                {
                    "name": child.attrib.get("name", ""),
                    "parameters": ", ".join(parameters),
                    "returnType": return_type,
                    **_visibility_of(child, context.default_visibility),
                }
            )

    kind = _read_kind(class_element)

    return {
        "id": class_id,
        "name": class_element.attrib.get("name", ""),
        **({"kind": kind} if kind != "class" else {}),
        "attributes": attributes,
        "methods": methods,
    }


def _read_kind(class_element: ET.Element) -> str:
    """El tipo de clase UML 2.5 de un elemento: clase, clase abstracta (`isAbstract`), interfaz o enumeración."""
    type_name = _uml_type_name(class_element) if _local_name(class_element.tag) in PACKAGED_TAGS else _local_name(class_element.tag)

    if type_name == "Interface":
        return "interface"

    if type_name == "Enumeration":
        return "enumeration"

    if class_element.attrib.get("isAbstract", "").lower() == "true":
        return "abstract"

    return "class"


CLASS_TYPE_NAMES = ("Class", "Interface", "Enumeration")


def _is_class_element(element: ET.Element) -> bool:
    local_name = _local_name(element.tag)

    if local_name in PACKAGED_TAGS:
        return _uml_type_name(element) in CLASS_TYPE_NAMES

    return local_name in CLASS_TYPE_NAMES


def _layout_number(value: str | None) -> int | float | None:
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number.is_integer():
        return int(number)

    return number


def _apply_case_layout(
    root: ET.Element,
    classes: list[dict[str, Any]],
) -> None:
    classes_by_id = {
        str(uml_class.get("id")): uml_class
        for uml_class in classes
        if uml_class.get("id") is not None
    }

    for element in root.iter(
        f"{{{CASE_LAYOUT_NS}}}element"
    ):
        class_id = (
            element.attrib.get(_xmi_attr("idref"))
            or element.attrib.get("idref")
        )

        if not class_id:
            continue

        uml_class = classes_by_id.get(class_id)

        if uml_class is None:
            continue

        x = _layout_number(element.attrib.get("x"))
        y = _layout_number(element.attrib.get("y"))
        width = _layout_number(element.attrib.get("width"))
        height = _layout_number(element.attrib.get("height"))

        if x is not None and y is not None:
            uml_class["position"] = {
                "x": x,
                "y": y,
            }

        if width is not None and height is not None:
            uml_class["size"] = {
                "width": width,
                "height": height,
            }


def import_xmi_to_uml(xml_data: Any) -> dict[str, Any]:
    """
    Convert UML/XMI XML into the internal CASE UML JSON structure.

    Namespace prefixes are intentionally ignored; matching is based on
    namespace-expanded/local names.
    """
    raw = _normalize_xml_input(xml_data)

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise XMIError(
            f"XMI/XML inválido: {exc}"
        ) from exc

    classes: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    class_elements: dict[str, ET.Element] = {}
    context = _ReadContext(root)

    for element_index, element in enumerate(root.iter()):
        if not _is_class_element(element):
            continue

        parsed_class = _parse_class(
            element,
            fallback_seed=str(element_index),
            context=context,
        )
        class_id = parsed_class["id"]

        if class_id in class_elements:
            continue

        class_elements[class_id] = element
        classes.append(parsed_class)

    for class_id, class_element in class_elements.items():
        for child in class_element:
            if _local_name(child.tag) != "generalization":
                continue

            target_id = child.attrib.get("general")

            if not target_id:
                continue

            relationships.append(
                {
                    "id": (
                        _xmi_id(child)
                        or _new_id(f"generalization-{class_id}-{target_id}-{len(relationships)}")
                    ),
                    "type": "generalization",
                    "sourceId": class_id,
                    "targetId": target_id,
                    "labels": [],
                }
            )

    for element in root.iter():
        if _local_name(element.tag) not in PACKAGED_TAGS:
            continue

        element_type = _uml_type_name(element)

        if element_type == "Association":
            owned_ends = [
                child
                for child in element
                if _local_name(child.tag) == "ownedEnd"
            ]

            if len(owned_ends) < 2:
                continue

            first_end = owned_ends[0]
            second_end = owned_ends[1]

            # Los extremos se enlazan por id de clase: aquí no se vuelve al nombre.
            first_type = _read_attribute_type(first_end)
            second_type = _read_attribute_type(second_end)

            if not first_type or not second_type:
                continue

            first_multiplicity = _read_multiplicity(
                first_end
            )
            second_multiplicity = _read_multiplicity(
                second_end
            )

            first_aggregation = first_end.attrib.get(
                "aggregation",
                "none",
            )
            second_aggregation = second_end.attrib.get(
                "aggregation",
                "none",
            )

            relation_type = "association"
            source_id = first_type
            target_id = second_type

            labels = [
                first_multiplicity,
                second_multiplicity,
            ]

            # El extremo marcado es la PARTE (UML y EA lo escriben así): el todo, el del rombo, es el otro y pasa a ser el origen.
            if first_aggregation in AGGREGATION_RELATIONS:
                relation_type = AGGREGATION_RELATIONS[first_aggregation]
                source_id, target_id = (
                    second_type,
                    first_type,
                )
                labels.reverse()

            elif second_aggregation in AGGREGATION_RELATIONS:
                relation_type = AGGREGATION_RELATIONS[second_aggregation]

            relationships.append(
                {
                    "id": (
                        _xmi_id(element)
                        or _new_id(f"association-{source_id}-{target_id}-{len(relationships)}")
                    ),
                    "type": relation_type,
                    "sourceId": source_id,
                    "targetId": target_id,
                    "labels": labels,
                }
            )

        elif element_type == "Dependency":
            client = (
                element.attrib.get("client", "")
                .split()
            )
            supplier = (
                element.attrib.get("supplier", "")
                .split()
            )

            if not client or not supplier:
                continue

            relationships.append(
                {
                    "id": (
                        _xmi_id(element)
                        or _new_id(f"dependency-{client[0]}-{supplier[0]}-{len(relationships)}")
                    ),
                    "type": "dependency",
                    "sourceId": client[0],
                    "targetId": supplier[0],
                    "labels": [],
                }
            )

    _apply_case_layout(root, classes)

    return {
        "classes": classes,
        "relationships": relationships,
    }
