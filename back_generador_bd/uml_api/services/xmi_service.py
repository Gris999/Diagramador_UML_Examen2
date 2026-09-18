from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree as ET


XMI_NS = "http://schema.omg.org/spec/XMI/2.1"
UML_NS = "http://www.eclipse.org/uml2/5.0.0/UML"

ET.register_namespace("xmi", XMI_NS)
ET.register_namespace("uml", UML_NS)


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

    for class_index, uml_class in enumerate(uml_json.get("classes", [])):
        class_id = str(
            uml_class.get("id")
            or _new_id(f"class-{class_index}")
        )

        class_element = ET.SubElement(
            model,
            "packagedElement",
            {
                _xmi_attr("type"): "uml:Class",
                _xmi_attr("id"): class_id,
                "name": str(
                    uml_class.get("name")
                    or f"Class{class_index + 1}"
                ),
            },
        )

        class_elements[class_id] = class_element

        for attribute_index, attribute in enumerate(
            uml_class.get("attributes", [])
        ):
            ET.SubElement(
                class_element,
                "ownedAttribute",
                {
                    _xmi_attr("type"): "uml:Property",
                    _xmi_attr("id"): _new_id(
                        f"{class_id}-attribute-{attribute_index}"
                    ),
                    "name": str(attribute.get("name", "")),
                    "type": str(attribute.get("type", "")),
                },
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

                if parameter_type:
                    parameter_data["type"] = parameter_type

                ET.SubElement(
                    operation,
                    "ownedParameter",
                    parameter_data,
                )

            return_type = str(
                method.get("returnType", "")
                or ""
            ).strip()

            if return_type:
                ET.SubElement(
                    operation,
                    "ownedParameter",
                    {
                        _xmi_attr("type"): "uml:Parameter",
                        _xmi_attr("id"): _new_id(
                            f"{class_id}-return-{method_index}"
                        ),
                        "name": "return",
                        "direction": "return",
                        "type": return_type,
                    },
                )

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

            source_end_data = {
                _xmi_attr("type"): "uml:Property",
                _xmi_attr("id"): source_end_id,
                "type": source_id,
            }

            if relation_type == "aggregation":
                source_end_data["aggregation"] = "shared"

            elif relation_type == "composition":
                source_end_data["aggregation"] = "composite"

            source_end = ET.SubElement(
                association,
                "ownedEnd",
                source_end_data,
            )

            target_end = ET.SubElement(
                association,
                "ownedEnd",
                {
                    _xmi_attr("type"): "uml:Property",
                    _xmi_attr("id"): target_end_id,
                    "type": target_id,
                },
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

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )


def _read_attribute_type(element: ET.Element) -> str:
    direct_type = element.attrib.get("type")

    if direct_type:
        return direct_type

    for child in element:
        if _local_name(child.tag) != "type":
            continue

        href = child.attrib.get("href", "")

        if "#" in href:
            return href.rsplit("#", 1)[1]

        child_id = _xmi_id(child)

        if child_id:
            return child_id

    return ""


def _parse_class(
    class_element: ET.Element,
    fallback_seed: str = "0",
) -> dict[str, Any]:
    class_id = _xmi_id(class_element) or _new_id(
        f"import-class-{fallback_seed}-{class_element.attrib.get('name', '')}"
    )

    attributes = []
    methods = []

    for child in class_element:
        child_name = _local_name(child.tag)

        if child_name == "ownedAttribute":
            if child.attrib.get("association"):
                continue

            attributes.append(
                {
                    "name": child.attrib.get("name", ""),
                    "type": _read_attribute_type(child),
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

                parameter_type = _read_attribute_type(
                    parameter
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

            methods.append(
                {
                    "name": child.attrib.get("name", ""),
                    "parameters": ", ".join(parameters),
                    "returnType": return_type,
                }
            )

    return {
        "id": class_id,
        "name": class_element.attrib.get("name", ""),
        "attributes": attributes,
        "methods": methods,
    }


def _is_class_element(element: ET.Element) -> bool:
    local_name = _local_name(element.tag)

    if local_name == "packagedElement":
        return _uml_type_name(element) == "Class"

    return local_name == "Class"


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

    for element_index, element in enumerate(root.iter()):
        if not _is_class_element(element):
            continue

        parsed_class = _parse_class(
            element,
            fallback_seed=str(element_index),
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
        if _local_name(element.tag) != "packagedElement":
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

            first_type = first_end.attrib.get("type")
            second_type = second_end.attrib.get("type")

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

            if first_aggregation == "shared":
                relation_type = "aggregation"

            elif first_aggregation == "composite":
                relation_type = "composition"

            elif second_aggregation == "shared":
                relation_type = "aggregation"
                source_id, target_id = (
                    second_type,
                    first_type,
                )
                labels.reverse()

            elif second_aggregation == "composite":
                relation_type = "composition"
                source_id, target_id = (
                    second_type,
                    first_type,
                )
                labels.reverse()

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

    return {
        "classes": classes,
        "relationships": relationships,
    }
