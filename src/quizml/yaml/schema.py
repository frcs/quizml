"""JSON Schema loading, extension merging, validation, and type coercion for QuizML."""

import copy
import json
import re
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft7Validator, validators
from jsonschema.exceptions import best_match
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from quizml.exceptions import QuizMLYamlSyntaxError, msg_context, text_wrap


class MarkdownString(str):
    """A string subclass tagging values that should be transcoded as Markdown."""

    pass


# --- Custom jsonschema Type Checker & Validator ---


def is_number(checker, instance):
    if isinstance(instance, bool):
        return False
    if isinstance(instance, (int, float)):
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
        return instance.lower() in {"true", "false", "yes", "no", "on", "off"}
    return False


CustomTypeChecker = Draft7Validator.TYPE_CHECKER.redefine_many(
    {"number": is_number, "integer": is_integer, "boolean": is_boolean}
)

ScalarValidator = validators.extend(Draft7Validator, type_checker=CustomTypeChecker)


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        if isinstance(instance, dict):
            for prop, subschema in properties.items():
                if "default" in subschema:
                    instance.setdefault(prop, subschema["default"])
        yield from validate_properties(validator, properties, instance, schema)

    return validators.extend(validator_class, {"properties": set_defaults})


DefaultFillingValidator = extend_with_default(ScalarValidator)


# --- Schema Reference Resolution & Type Coercion ---


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
        return _resolve_schema_refs(
            _resolve_local_ref(ref, root_schema), root_schema, ref_stack + (ref,)
        )
    return {
        key: _resolve_schema_refs(value, root_schema, ref_stack)
        for key, value in schema.items()
    }


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
        branch = "then" if ScalarValidator(condition).is_valid(data) else "else"
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
            if ScalarValidator(
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


def coerce_value(value, schemas):
    """Coerce a single value based on the applicable schema types."""
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
    """Traverse yaml_data (questions and header) and coerce types according to schema."""

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


# --- Schema Loading, Extensions & Validation Diagnostics ---


def apply_schema_extensions(schema, extensions):
    """Return a deep copy of schema extended with header_properties, question_properties, and question_types."""
    if not schema or not extensions:
        return schema
    if not isinstance(extensions, dict):
        raise QuizMLYamlSyntaxError("'schema_extensions' must be a mapping.")

    schema = copy.deepcopy(schema)
    header_props = extensions.get("header_properties")
    if header_props is not None:
        if not isinstance(header_props, dict):
            raise QuizMLYamlSyntaxError(
                "'schema_extensions.header_properties' must be a mapping."
            )
        defs = schema.setdefault("definitions", {})
        hdr = defs.setdefault(
            "header", {"type": "object", "additionalProperties": True}
        )
        hdr.setdefault("properties", {}).update(header_props)

    question_props = extensions.get("question_properties")
    if question_props is not None:
        if not isinstance(question_props, dict):
            raise QuizMLYamlSyntaxError(
                "'schema_extensions.question_properties' must be a mapping."
            )
        items = schema.setdefault("items", {"type": "object"})
        items.setdefault("properties", {}).update(question_props)
        for branch in items.get("allOf", []):
            then_block = branch.get("then")
            if isinstance(then_block, dict) and isinstance(
                then_block.get("properties"), dict
            ):
                then_block["properties"].update(question_props)

    question_types = extensions.get("question_types")
    if question_types is not None:
        if not isinstance(question_types, dict):
            raise QuizMLYamlSyntaxError(
                "'schema_extensions.question_types' must be a mapping."
            )
        items = schema.setdefault("items", {"type": "object"})
        type_prop = items.setdefault("properties", {}).setdefault(
            "type", {"type": "string", "enum": []}
        )
        enum_list = type_prop.setdefault("enum", [])
        all_of = items.setdefault("allOf", [])
        base_q_props = {
            "type": {"type": "string"},
            "id": {"type": "string"},
            "title": {"type": "string"},
            "marks": {"type": "number", "default": "2.5"},
            "comments": {"$ref": "#/definitions/markdown"},
            "feedback": {"$ref": "#/definitions/markdown"},
            "question": {"$ref": "#/definitions/markdown"},
            "figure": {"$ref": "#/definitions/markdown"},
            "figure-split": {"type": "number"},
        }
        if isinstance(question_props, dict):
            base_q_props.update(question_props)

        for q_type, spec in question_types.items():
            if not isinstance(spec, dict):
                raise QuizMLYamlSyntaxError(
                    f"Schema extension for question type '{q_type}' must be a mapping."
                )
            if q_type not in enum_list:
                enum_list.append(q_type)
            merged_props = copy.deepcopy(base_q_props)
            if isinstance(spec.get("properties"), dict):
                merged_props.update(spec["properties"])
            then_schema = {
                "properties": merged_props,
                "required": spec.get("required", ["question"]),
                "additionalProperties": spec.get("additionalProperties", False),
            }
            all_of.append(
                {
                    "if": {"properties": {"type": {"const": q_type}}},
                    "then": then_schema,
                }
            )
    return schema


def load_schema(schema_path=None, schema_extensions=None):
    """Load the bundled or custom JSON/YAML schema and apply optional extensions."""
    try:
        if schema_path is None:
            schema_resource = files("quizml").joinpath("templates", "schema.json")
            schema_str = schema_resource.read_text(encoding="utf-8")
            schema = json.loads(schema_str)
        else:
            schema_file = Path(schema_path)
            schema_str = schema_file.read_text(encoding="utf-8")
            if schema_file.suffix.lower() in (".yaml", ".yml"):
                yaml_parser = YAML(typ="safe")
                schema = yaml_parser.load(schema_str)
            else:
                schema = json.loads(schema_str)
        if schema_extensions:
            schema = apply_schema_extensions(schema, schema_extensions)
        return schema
    except FileNotFoundError as err:
        schema_name = schema_path or "packaged schema.json"
        raise QuizMLYamlSyntaxError(f"Schema file not found: {schema_name}") from err
    except (json.JSONDecodeError, YAMLError) as err:
        raise QuizMLYamlSyntaxError(f"Invalid schema syntax: {err}") from err
    except TypeError as err:
        raise QuizMLYamlSyntaxError(
            "Schema must be provided for validation when validate=True."
        ) from err


def validate_header(header, schema, source_text="", source_path="<string>"):
    """Validate the optional header definition when a schema provides one."""
    if not schema:
        return
    header_schema = schema.get("definitions", {}).get("header")
    if not header_schema:
        return

    err = best_match(DefaultFillingValidator(header_schema).iter_errors(header))
    if err:
        path = " -> ".join(map(str, err.path))
        line_num = "unknown"
        if err.path:
            key = next(iter(err.path))
            try:
                line_num = header.lc.data[key][0] + 1
            except (AttributeError, KeyError, TypeError, IndexError):
                pass
        lines = source_text.splitlines()
        msg = f"Header schema validation error in {source_path} at '{path}' (line ~{line_num})\n"
        if line_num != "unknown":
            msg += msg_context(lines, line_num) + "\n"
        msg += text_wrap(err.message)
        raise QuizMLYamlSyntaxError(msg)


def _line_for_node_path(root, path, initial_line=None):
    """Return the YAML source line for a node path when ruamel has one."""
    line = initial_line
    node = root
    for key in path:
        try:
            if isinstance(node, list):
                location = node.lc.item(key)
            elif isinstance(node, dict):
                location = node.lc.value(key)
            else:
                break
            if location is not None:
                line = location[0] + 1
            node = node[key]
        except (AttributeError, IndexError, KeyError, TypeError):
            break
    return line


def validate_source_questions(questions, schema, *, source_text, source_path):
    """Validate each source file's actual questions before include flattening."""
    if not schema or not isinstance(questions, list) or "items" not in schema:
        return

    item_schema = dict(schema["items"])
    if "definitions" in schema:
        item_schema.setdefault("definitions", schema["definitions"])
    validator = DefaultFillingValidator(item_schema)
    lines = source_text.splitlines()
    for index, question in enumerate(questions):
        if isinstance(question, dict) and "_include" in question:
            continue
        error = best_match(validator.iter_errors(question))
        if error is None:
            continue

        try:
            initial_line = questions.lc.item(index)[0] + 1
        except (AttributeError, IndexError, TypeError):
            initial_line = None
        line_num = _line_for_node_path(
            question,
            error.path,
            initial_line=initial_line,
        )
        path = " -> ".join([str(index), *map(str, error.path)])
        message = f"Schema validation error in {source_path} at '{path}'"
        if line_num is not None:
            message += f" (line ~{line_num})\n"
            message += msg_context(lines, line_num) + "\n"
        else:
            message += "\n"
        message += text_wrap(error.message)
        raise QuizMLYamlSyntaxError(message)


def validate_questions_list(questions_data, schema, *, source_text, filename):
    """Validate the flattened question list against the full root schema."""
    if not schema or not questions_data:
        return
    validator = DefaultFillingValidator(schema)
    err = best_match(validator.iter_errors(questions_data))
    if err:
        path = " -> ".join(map(str, err.path))
        try:
            item = questions_data
            for key in err.path:
                item = item[key]
            line_num = item.lc.line + 1
        except (KeyError, IndexError, AttributeError):
            line_num = "unknown"
        lines = source_text.splitlines()
        msg = f"Schema validation error in {filename} at '{path}' (line ~{line_num})\n"
        if line_num != "unknown":
            msg += msg_context(lines, line_num) + "\n"
        msg += text_wrap(err.message)
        raise QuizMLYamlSyntaxError(msg)
