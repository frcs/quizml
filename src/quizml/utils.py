"a few utility functions to deal with QuizMLYaml objects."

import os
import re
import textwrap

from jsonschema import Draft7Validator, validators


def iter_nodes(data, key_filter=None):
    """
    Generator that yields all leaf nodes in the data structure.
    Recurses into lists and dicts.

    :param data: The structure to traverse (list, dict, or value).
    :param key_filter: Optional function(key) -> bool.
                       If True (or None), recurses into the dict value.
                       If False, skips the key (value is ignored).
    """
    if isinstance(data, list):
        for item in data:
            yield from iter_nodes(item, key_filter)
    elif isinstance(data, dict):
        for k, v in data.items():
            if key_filter and not key_filter(k):
                continue
            yield from iter_nodes(v, key_filter)
    else:
        yield data


def map_nodes(data, fn, key_filter=None):
    """
    Recursively applies fn to all leaf nodes in the data structure.
    Returns a new structure with transformed values.

    :param data: The structure to traverse.
    :param fn: Function(node) -> new_node. Applied to leaves.
    :param key_filter: Optional function(key) -> bool.
                       If True (or None), recurses into the dict value.
                       If False, preserves the value as-is without recursion/transformation.
    """
    if isinstance(data, list):
        return [map_nodes(item, fn, key_filter) for item in data]
    elif isinstance(data, dict):
        new_dict = type(data)()
        for k, v in data.items():
            if key_filter and not key_filter(k):
                new_dict[k] = v
            else:
                new_dict[k] = map_nodes(v, fn, key_filter)
        return new_dict
    else:
        return fn(data)


class MarkdownString(str):
    """
    A string subclass to tag values that should be treated as Markdown.
    """

    pass


# --- Schema Helpers ---


def _resolve_local_ref(ref, root_schema):
    """Resolve a JSON Pointer reference into the root schema."""
    if ref == "#":
        return root_schema
    if not ref.startswith("#/"):
        raise ValueError(f"Only local JSON Schema references are supported: {ref}")

    target = root_schema
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        try:
            target = target[part] if isinstance(target, dict) else target[int(part)]
        except (KeyError, IndexError, ValueError, TypeError) as err:
            raise ValueError(f"Unresolvable JSON Schema reference: {ref}") from err
    return target


def _resolve_schema_refs(schema, root_schema, ref_stack=()):
    """Expand local references for schema validation (for example, anyOf)."""
    if isinstance(schema, list):
        return [_resolve_schema_refs(item, root_schema, ref_stack) for item in schema]
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in ref_stack:
            raise ValueError(f"Recursive JSON Schema reference is unsupported: {ref}")
        # In Draft 7, sibling keywords beside $ref are ignored.
        return _resolve_schema_refs(
            _resolve_local_ref(ref, root_schema), root_schema, ref_stack + (ref,)
        )
    return {
        key: _resolve_schema_refs(value, root_schema, ref_stack)
        for key, value in schema.items()
    }


def _numeric_string(checker, instance):
    if isinstance(instance, bool):
        return False
    if isinstance(instance, (int, float)):
        return True
    if isinstance(instance, str):
        try:
            float(instance)
            return True
        except ValueError:
            return False
    return False


def _integer_string(checker, instance):
    if isinstance(instance, bool):
        return False
    if isinstance(instance, int):
        return True
    if isinstance(instance, str):
        try:
            return str(int(instance)) == instance
        except ValueError:
            return False
    return False


def _boolean_string(checker, instance):
    return (
        isinstance(instance, str)
        and instance.lower() in {"true", "false", "yes", "no", "on", "off"}
        or isinstance(instance, bool)
    )


_CoercionValidator = validators.extend(
    Draft7Validator,
    type_checker=Draft7Validator.TYPE_CHECKER.redefine_many(
        {
            "number": _numeric_string,
            "integer": _integer_string,
            "boolean": _boolean_string,
        }
    ),
)


def _applicable_schemas(data, schema, root_schema, ref_stack=()):
    """Return schema fragments that apply to this value for coercion."""
    if isinstance(schema, list):
        return [
            active
            for sub_schema in schema
            for active in _applicable_schemas(data, sub_schema, root_schema, ref_stack)
        ]
    if not isinstance(schema, dict):
        return []
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in ref_stack:
            raise ValueError(f"Recursive JSON Schema reference is unsupported: {ref}")
        return _applicable_schemas(
            data,
            _resolve_local_ref(ref, root_schema),
            root_schema,
            ref_stack + (ref,),
        )

    applicable = [schema]
    if "if" in schema:
        condition = _resolve_schema_refs(schema["if"], root_schema)
        branch = "then" if _CoercionValidator(condition).is_valid(data) else "else"
        if branch in schema:
            applicable.extend(
                _applicable_schemas(data, schema[branch], root_schema, ref_stack)
            )

    for sub_schema in schema.get("allOf", []):
        applicable.extend(_applicable_schemas(data, sub_schema, root_schema, ref_stack))

    for keyword in ("anyOf", "oneOf"):
        if keyword not in schema:
            continue
        matching = [
            sub_schema
            for sub_schema in schema[keyword]
            if _CoercionValidator(
                _resolve_schema_refs(sub_schema, root_schema)
            ).is_valid(data)
        ]
        if keyword == "oneOf" and len(matching) != 1:
            continue
        for sub_schema in matching:
            applicable.extend(
                _applicable_schemas(data, sub_schema, root_schema, ref_stack)
            )
    return applicable


def is_format_markdown(schema_node):
    if not schema_node or not isinstance(schema_node, dict):
        return False
    return schema_node.get("format") == "markdown"


# --- Coercion Logic ---


def coerce_value(value, schemas):
    """
    Coerce a single value based on the schema type.
    """
    for schema in schemas:
        if is_format_markdown(schema) and isinstance(value, str):
            return MarkdownString(value)
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
                value = int(value)
            except ValueError:
                pass
        if "number" in types and isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                pass
    return value


def coerce_data(yaml_data, schema):
    """
    Traverses the yaml_data (specifically questions) and coerces types
    (int, float, bool, MarkdownString) based on the provided schema.
    """

    def coerce_recursive(data, current_schema):
        if not current_schema:
            return data

        active_schemas = _applicable_schemas(data, current_schema, schema)
        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                child_schemas = []
                for active in active_schemas:
                    properties = active.get("properties", {})
                    if key in properties:
                        child_schemas.append(properties[key])
                    matching_patterns = [
                        subschema
                        for pattern, subschema in active.get(
                            "patternProperties", {}
                        ).items()
                        if re.search(pattern, key)
                    ]
                    child_schemas.extend(matching_patterns)
                    if (
                        key not in properties
                        and not matching_patterns
                        and "additionalProperties" in active
                        and isinstance(active["additionalProperties"], dict)
                    ):
                        child_schemas.append(active["additionalProperties"])
                new_dict[key] = coerce_recursive(value, child_schemas)
            return new_dict

        if isinstance(data, list):
            new_list = []
            for index, item in enumerate(data):
                child_schemas = []
                for active in active_schemas:
                    items = active.get("items", {})
                    if isinstance(items, list):
                        if index < len(items):
                            child_schemas.append(items[index])
                    elif items:
                        child_schemas.append(items)
                new_list.append(coerce_recursive(item, child_schemas))
            return new_list

        return coerce_value(data, active_schemas)

    if isinstance(yaml_data, dict) and schema:
        if "questions" in yaml_data:
            yaml_data["questions"] = coerce_recursive(yaml_data["questions"], schema)
        header_schema = schema.get("definitions", {}).get("header")
        if "header" in yaml_data and header_schema:
            yaml_data["header"] = coerce_recursive(yaml_data["header"], header_schema)

    return yaml_data


# --- Markdown Processing ---


def get_md_list_from_yaml(yaml_data):
    """
    List all Markdown entries in the yaml file.
    Uses MarkdownString type for questions, and legacy logic for headers.
    """
    md_list = []

    def header_key_filter(key):
        non_md_keys = ["type", "inputbasename"]
        return (key not in non_md_keys) and not key.startswith("_")

    if isinstance(yaml_data, dict) and (
        "header" in yaml_data or "questions" in yaml_data
    ):
        if "header" in yaml_data:
            for node in iter_nodes(yaml_data["header"], header_key_filter):
                if isinstance(node, str):
                    md_list.append(str(node))

        if "questions" in yaml_data:
            for node in iter_nodes(yaml_data["questions"]):
                if isinstance(node, MarkdownString):
                    md_list.append(str(node))
    else:
        # Fallback
        for node in iter_nodes(yaml_data, header_key_filter):
            if isinstance(node, str):
                md_list.append(str(node))

    return md_list


def transcode_md_in_yaml(yaml_data, md_dict):
    """
    translate all strings in md_dict into their transcribed text
    """

    def transform_questions(node):
        if isinstance(node, MarkdownString) and node in md_dict:
            return md_dict[node]
        return node

    def transform_header(node):
        if isinstance(node, str) and node in md_dict:
            return md_dict[node]
        return node

    def header_key_filter(key):
        return key != "inputbasename" and not key.startswith("_")

    if isinstance(yaml_data, dict) and (
        "header" in yaml_data or "questions" in yaml_data
    ):
        new_doc = {}
        for k, v in yaml_data.items():
            if k == "header":
                new_doc[k] = map_nodes(v, transform_header, header_key_filter)
            elif k == "questions":
                new_doc[k] = map_nodes(v, transform_questions)
            else:
                new_doc[k] = v
        return new_doc
    else:
        return map_nodes(yaml_data, transform_header, header_key_filter)


def text_wrap(msg):
    try:
        w, _ = os.get_terminal_size(0)
    except OSError:
        w = 80  # Default width if terminal size can't be determined
    return textwrap.fill(msg, w - 5)


def msg_context_line(lines, lineo, charno=None, highlight=False):
    if lineo < 1 or lineo > len(lines):
        return ""
    if highlight:
        # Using simple formatting for now to avoid dependency on rich here
        # This can be enhanced later if needed.
        return f"❱ {lineo:>4} │  {lines[lineo - 1]}\n"
    else:
        return f"  {lineo:>4} │ {lines[lineo - 1]}\n"


def msg_context(lines, lineo, charno=None):
    msg = msg_context_line(lines, lineo - 1, charno, highlight=False)
    msg += msg_context_line(lines, lineo, charno, highlight=True)
    msg += msg_context_line(lines, lineo + 1, charno, highlight=False)
    return msg
