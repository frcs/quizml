"""Schema validation, defaults filling, and data coercion for QuizML."""

import os
import textwrap

from jsonschema import Draft7Validator, validators

from quizml.exceptions import QuizMLYamlSyntaxError


class MarkdownString(str):
    """A string subclass to tag values that should be treated as Markdown."""

    pass


# --- Custom jsonschema Validator and Type Conversion ---


def is_number(checker, instance):
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        return True
    if isinstance(instance, str):
        try:
            float(instance)
            return True
        except (ValueError, TypeError):
            return False
    return False


def is_integer(checker, instance):
    if isinstance(instance, bool):
        return False
    if isinstance(instance, int):
        return True
    if isinstance(instance, str):
        try:
            return str(int(instance)) == instance
        except (ValueError, TypeError):
            return False
    return False


def is_boolean(checker, instance):
    if isinstance(instance, bool):
        return True
    if isinstance(instance, str):
        return instance.lower() in ["true", "false", "yes", "no", "on", "off"]
    return False


CustomTypeChecker = Draft7Validator.TYPE_CHECKER.redefine_many(
    {"number": is_number, "integer": is_integer, "boolean": is_boolean}
)


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        if isinstance(instance, dict):
            for prop, subschema in properties.items():
                if "default" in subschema:
                    instance.setdefault(prop, subschema["default"])
        yield from validate_properties(validator, properties, instance, schema)

    return validators.extend(validator_class, {"properties": set_defaults})


# Chain the validators: Defaults -> Validation
DefaultFillingValidator = extend_with_default(
    validators.extend(Draft7Validator, type_checker=CustomTypeChecker)
)


# --- Error Formatting Helpers ---


def _text_wrap(msg: str) -> str:
    try:
        w, _ = os.get_terminal_size(0)
    except OSError:
        w = 80
    return textwrap.fill(msg, max(20, w - 5))


def _msg_context_line(lines: list[str], lineo: int, highlight: bool = False) -> str:
    if lineo < 1 or lineo > len(lines):
        return ""
    if highlight:
        return f"❱ {lineo:>4} │  {lines[lineo - 1]}\n"
    return f"  {lineo:>4} │ {lines[lineo - 1]}\n"


def _msg_context(lines: list[str], lineo: int) -> str:
    msg = _msg_context_line(lines, lineo - 1, highlight=False)
    msg += _msg_context_line(lines, lineo, highlight=True)
    msg += _msg_context_line(lines, lineo + 1, highlight=False)
    return msg


def validate_questions(
    quizmlyaml_txt: str, questions_data: list, schema: dict, filename: str = "<string>"
) -> None:
    """Validates questions_data against the schema and fills in defaults."""
    validator = DefaultFillingValidator(schema)
    errors = sorted(validator.iter_errors(questions_data), key=lambda e: e.path)
    if errors:
        err = errors[0]
        path = " -> ".join(map(str, err.path))
        try:
            item = questions_data
            for key in err.path:
                item = item[key]
            line_num = item.lc.line + 1
        except (KeyError, IndexError, AttributeError):
            line_num = "unknown"
        lines = quizmlyaml_txt.splitlines()
        msg = f"Schema validation error in {filename} at '{path}' (line ~{line_num})\n"
        if line_num != "unknown":
            msg += _msg_context(lines, line_num) + "\n"
        msg += _text_wrap(err.message)
        raise QuizMLYamlSyntaxError(msg)


# --- Schema Helpers & Coercion Logic ---


def apply_conditions(data, current_schema):
    """Applies conditional logic (if/then/else) from JSON schema."""

    def check_condition(cond_schema):
        if "properties" in cond_schema:
            for prop, value in cond_schema["properties"].items():
                if "const" in value and data.get(prop) != value["const"]:
                    return False
        return True

    if "if" in current_schema:
        if check_condition(current_schema["if"]):
            return current_schema.get("then", {})
        return current_schema.get("else", {})

    for key in ["allOf", "anyOf", "oneOf"]:
        if key in current_schema:
            for sub_schema in current_schema[key]:
                if "if" in sub_schema and check_condition(sub_schema["if"]):
                    return sub_schema.get("then", {})

    return current_schema


def is_format_markdown(schema_node):
    if not schema_node or not isinstance(schema_node, dict):
        return False
    if "$ref" in schema_node:
        if schema_node["$ref"] == "#/definitions/markdown":
            return True
        return False
    return schema_node.get("format") == "markdown"


def coerce_value(value, schema):
    """Coerce a single scalar value based on the schema type."""
    if is_format_markdown(schema):
        if isinstance(value, str):
            return MarkdownString(value)
        return value

    types = schema.get("type", [])
    if isinstance(types, str):
        types = [types]

    if "boolean" in types and isinstance(value, str):
        if value.lower() in ["true", "yes", "on"]:
            return True
        if value.lower() in ["false", "no", "off"]:
            return False

    if "integer" in types and isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass

    if "number" in types and isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            pass

    return value


def coerce_data(yaml_data, schema):
    """Traverses the questions in yaml_data and coerces types

    (int, float, bool, MarkdownString) based on the schema.
    """

    def coerce_recursive(data, current_schema):
        if not current_schema:
            return data

        if isinstance(data, dict):
            refined_schema = apply_conditions(data, current_schema)
            new_dict = {}
            properties = refined_schema.get("properties", {})
            for key, value in data.items():
                if key in properties:
                    new_dict[key] = coerce_recursive(value, properties[key])
                else:
                    new_dict[key] = value
            return new_dict

        elif isinstance(data, list):
            new_list = []
            items_schema = current_schema.get("items", {})
            for item in data:
                new_list.append(coerce_recursive(item, items_schema))
            return new_list

        else:
            return coerce_value(data, current_schema)

    if isinstance(yaml_data, dict) and "questions" in yaml_data and schema:
        yaml_data["questions"] = coerce_recursive(yaml_data["questions"], schema)

    return yaml_data
