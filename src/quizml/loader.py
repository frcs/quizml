"""QuizMLYaml load file

This module provides the function for loading QuizMLYaml files as a
list/dict structure.

QuizMLYaml files are a form of YAML. To avoid issues like the "Norway
problem" (where `country: No` is read as `country: False`), this loader
ensures that all values are loaded as strings by default, unless the
schema specifies a different type.

Validation is performed by `jsonschema` against a user-definable
schema, allowing for flexible and robust parsing. Line numbers are
preserved for accurate error reporting.

Typical usage example:

    yaml_data = load("quiz.yaml")

"""

import json
import os
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft7Validator, validators
from jsonschema.exceptions import best_match
from ruamel.yaml import YAML
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import ScalarNode
from ruamel.yaml.scalarstring import PlainScalarString

from quizml.exceptions import QuizMLYamlSyntaxError
from quizml.paths import find_path
from quizml.utils import coerce_data, msg_context, text_wrap

# --- Custom ruamel.yaml Constructor ---


class StringConstructor(RoundTripConstructor):
    """
    A custom constructor for ruamel.yaml that treats all scalar values
    as strings, preserving the original text and line/column info.
    """

    def construct_scalar(self, node: ScalarNode):
        if node.tag == "tag:yaml.org,2002:null":
            return None
        s = PlainScalarString(node.value, anchor=node.anchor)
        return s


StringConstructor.add_constructor(
    "tag:yaml.org,2002:bool", StringConstructor.construct_scalar
)
StringConstructor.add_constructor(
    "tag:yaml.org,2002:int", StringConstructor.construct_scalar
)
StringConstructor.add_constructor(
    "tag:yaml.org,2002:float", StringConstructor.construct_scalar
)
StringConstructor.add_constructor(
    "tag:yaml.org,2002:null", StringConstructor.construct_scalar
)


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


def _to_plain_python(data):
    if isinstance(data, dict):
        return {str(k): _to_plain_python(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_plain_python(v) for v in data]
    if isinstance(data, str):
        return str(data)
    return data


def _validate_header(header, schema, source_text="", source_path="<string>"):
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


def _read_question_file(path: Path):
    """Read one QuizML YAML file and return its header and question list."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise QuizMLYamlSyntaxError(
            f"Error reading included file '{path}': {err}"
        ) from err

    yaml = YAML()
    yaml.Constructor = StringConstructor
    try:
        raw_docs = list(yaml.load_all(text))
    except YAMLError as err:
        raise QuizMLYamlSyntaxError(
            f"YAML parsing error in included file {path}: {err}"
        ) from err

    docs = [
        doc
        for doc in raw_docs
        if doc is not None and not (isinstance(doc, str) and not doc.strip())
    ]
    if len(docs) > 2:
        raise QuizMLYamlSyntaxError(
            f"Included file {path} cannot have more than 2 documents."
        )

    if not docs:
        header, questions = {}, []
    elif len(docs) == 1:
        if isinstance(docs[0], list):
            header, questions = {}, docs[0]
        else:
            header, questions = docs[0], []
    else:
        header, questions = docs

    if not isinstance(questions, list):
        raise QuizMLYamlSyntaxError(
            f"Questions in included file {path} must be a YAML list."
        )
    return header, questions, text


def _include_path(filename, base_dir):
    found = find_path(filename, [base_dir])
    if found:
        return found[0]
    requested = Path(filename).expanduser()
    if not requested.is_absolute():
        requested = Path(base_dir) / requested
    return Path(os.path.realpath(requested))


def count_included_questions(
    item: dict, base_dir: Path, visited: set[Path] | None = None
) -> int:
    """Count the questions contributed by an include, recursively."""
    if visited is None:
        visited = set()

    inc_file = str(item.get("_include", "")).strip()
    if not inc_file:
        return 0

    inc_path = _include_path(inc_file, base_dir)

    if not inc_path.is_file() or inc_path in visited:
        return 1

    try:
        _, sub_questions, _ = _read_question_file(inc_path)
    except QuizMLYamlSyntaxError:
        return 1

    new_visited = visited | {inc_path}
    total = 0
    for q in sub_questions:
        if isinstance(q, dict) and "_include" in q:
            total += count_included_questions(q, inc_path.parent, new_visited)
        else:
            total += 1

    if "select" in item:
        try:
            selectors = _normalize_select_list(item["select"])
            return min(len(selectors), total)
        except QuizMLYamlSyntaxError:
            return total
    if "count" in item:
        try:
            requested = int(item["count"])
        except (TypeError, ValueError):
            return total
        return min(max(requested, 0), total)
    return total


def _normalize_select_list(select_spec):
    if isinstance(select_spec, list):
        return [str(x).strip() for x in select_spec if str(x).strip()]
    if isinstance(select_spec, (str, int)):
        return [s.strip() for s in str(select_spec).split(",") if s.strip()]
    raise QuizMLYamlSyntaxError(
        "Include 'select' must be a list or comma-separated string of question IDs or 1-based indices."
    )


def _select_questions(questions, select_spec, source_label):
    selectors = _normalize_select_list(select_spec)
    by_id = {}
    for idx, q in enumerate(questions):
        if isinstance(q, dict) and q.get("id"):
            by_id[str(q["id"]).strip()] = idx

    selected = []
    for sel in selectors:
        if sel in by_id:
            selected.append(questions[by_id[sel]])
        elif sel.isdigit():
            pos = int(sel)
            if 1 <= pos <= len(questions):
                selected.append(questions[pos - 1])
            else:
                raise QuizMLYamlSyntaxError(
                    f"Include 'select' index {pos} is out of range (1..{len(questions)}) in '{source_label}'."
                )
        else:
            raise QuizMLYamlSyntaxError(
                f"Include 'select' ID '{sel}' not found in '{source_label}'."
            )
    return selected


def _reject_include_sampling(item):
    """Require random sampling directives to be materialized with ``quizml sample``."""
    unknown = sorted(set(item) - {"_include", "count", "seed", "select"})
    if unknown:
        options = ", ".join(f"'{option}'" for option in unknown)
        raise QuizMLYamlSyntaxError(
            f"Unknown directive(s) in _include mapping: {options}."
        )
    if "select" in item and ("count" in item or "seed" in item):
        raise QuizMLYamlSyntaxError(
            "Cannot combine 'select' with 'count' or 'seed' in _include."
        )
    unsupported = sorted({"count", "seed"}.intersection(item))
    if unsupported:
        options = ", ".join(f"'{option}'" for option in unsupported)
        raise QuizMLYamlSyntaxError(
            f"Include sampling options {options} cannot be used while compiling. "
            "Run 'quizml sample' to create a static quiz file first."
        )


def _resolve_includes(
    questions_data: list,
    base_dir: Path,
    root_dir: Path,
    visited: set[Path] | None = None,
    accumulated_figure_dirs: list[str] | None = None,
    schema=None,
    source_text="",
    source_path="<string>",
) -> list:
    """Recursively resolves '- _include: filename.yaml' directives in the questions list.

    Includes every question in source order (or the subset specified by 'select')
    and detects circular includes using the visited set.
    Accumulates figure search directories relative to root_dir.
    """
    if visited is None:
        visited = set()
    if accumulated_figure_dirs is None:
        accumulated_figure_dirs = []

    _validate_source_questions(
        questions_data, schema, source_text=source_text, source_path=source_path
    )

    resolved = []
    for item in questions_data:
        if isinstance(item, dict) and "include" in item and "_include" not in item:
            raise QuizMLYamlSyntaxError(
                "Unknown directive 'include'. Did you mean '_include'?"
            )
        if isinstance(item, dict) and "_include" in item:
            _reject_include_sampling(item)
            inc_file = str(item["_include"]).strip()
            inc_path = _include_path(inc_file, base_dir)

            if not inc_path.is_file():
                raise QuizMLYamlSyntaxError(
                    f"Included YAML file not found: '{inc_file}' (resolved to '{inc_path}')"
                )

            if inc_path in visited:
                raise QuizMLYamlSyntaxError(
                    f"Circular include detected: '{inc_path}' is already in the inclusion chain."
                )

            sub_header, sub_questions, inc_text = _read_question_file(inc_path)
            _validate_header(sub_header, schema, inc_text, str(inc_path))

            # Accumulate figure paths from sub-file
            if isinstance(sub_header, dict):
                sub_figures = sub_header.get("_figures_path", [])
                if isinstance(sub_figures, str):
                    sub_figures = [sub_figures]
                elif not isinstance(sub_figures, list):
                    sub_figures = []
                for p in sub_figures:
                    p_str = str(p).strip()
                    sub_fig_path = (
                        Path(p_str).resolve()
                        if os.path.isabs(p_str)
                        else (inc_path.parent / p_str).resolve()
                    )
                    rel_fig_dir = os.path.relpath(sub_fig_path, root_dir)
                    if rel_fig_dir not in accumulated_figure_dirs:
                        accumulated_figure_dirs.append(rel_fig_dir)

            if inc_path.parent != root_dir:
                rel_inc_dir = os.path.relpath(inc_path.parent, root_dir)
                if rel_inc_dir not in accumulated_figure_dirs:
                    accumulated_figure_dirs.append(rel_inc_dir)

            # Recursively resolve nested includes
            new_visited = visited | {inc_path}
            sub_questions = _resolve_includes(
                sub_questions,
                inc_path.parent,
                root_dir,
                new_visited,
                accumulated_figure_dirs,
                schema,
                inc_text,
                str(inc_path),
            )
            if "select" in item:
                sub_questions = _select_questions(
                    sub_questions, item["select"], inc_file
                )

            resolved.extend(sub_questions)
        else:
            resolved.append(item)

    return resolved


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


def _validate_source_questions(questions, schema, *, source_text, source_path):
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


def loads(
    quizmlyaml_txt,
    validate=True,
    schema=None,
    filename="<string>",
    base_dir=None,
):
    """Parses a QuizML string.

    Identifies header and questions documents using native YAML multi-doc parsing,
    resolves any '- include: file.yaml' directives, validates questions against
    the schema, and returns the data structure.
    """
    yaml = YAML()
    yaml.Constructor = StringConstructor
    try:
        raw_docs = list(yaml.load_all(quizmlyaml_txt))
    except YAMLError as err:
        line = -1
        if hasattr(err, "problem_mark"):
            line = err.problem_mark.line
        raise QuizMLYamlSyntaxError(
            f"YAML parsing error in {filename} near line {line}:\n{err}"
        ) from err

    # Filter out empty/None documents (e.g. from leading/trailing ---)
    yamldocs = [
        d
        for d in raw_docs
        if d is not None and not (isinstance(d, str) and not d.strip())
    ]

    if base_dir is None:
        if filename and filename != "<string>":
            base_dir = Path(filename).parent.resolve()
        else:
            base_dir = Path.cwd()

    if len(yamldocs) > 2:
        raise QuizMLYamlSyntaxError(
            "YAML file cannot have more than 2 documents: "
            "one for the header and one for the questions."
        )

    if not yamldocs:
        return {
            "header": {},
            "questions": [],
            "paths": {"input_dir": str(base_dir), "figure_dirs": []},
        }, schema

    if len(yamldocs) == 1:
        if isinstance(yamldocs[0], list):
            header_data, questions_data = {}, yamldocs[0]
        else:
            header_data, questions_data = yamldocs[0], []
    else:
        header_data, questions_data = yamldocs[0], yamldocs[1]

    if validate:
        _validate_header(header_data, schema, quizmlyaml_txt, filename)

    root_figure_dirs = []
    if isinstance(header_data, dict):
        root_figure_dirs = header_data.pop("_figures_path", [])
    if isinstance(root_figure_dirs, str):
        root_figure_dirs = [root_figure_dirs]
    elif not isinstance(root_figure_dirs, list):
        root_figure_dirs = []

    accumulated_figure_dirs = []

    if questions_data and isinstance(questions_data, list):
        questions_data = _resolve_includes(
            questions_data,
            base_dir=base_dir,
            root_dir=base_dir,
            accumulated_figure_dirs=accumulated_figure_dirs,
            schema=schema if validate else None,
            source_text=quizmlyaml_txt,
            source_path=filename,
        )
        seen_ids = set()
        for q in questions_data:
            if isinstance(q, dict) and q.get("id"):
                qid = str(q["id"]).strip()
                if qid in seen_ids:
                    raise QuizMLYamlSyntaxError(
                        f"Duplicate question id '{qid}' in {filename}"
                    )
                seen_ids.add(qid)
    figure_dirs = list(dict.fromkeys(root_figure_dirs + accumulated_figure_dirs))

    # Validating questions against the schema
    if validate and schema and questions_data:
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
            lines = quizmlyaml_txt.splitlines()
            msg = f"Schema validation error in {filename} at '{path}' (line ~{line_num})\n"
            if line_num != "unknown":
                msg += msg_context(lines, line_num) + "\n"
            msg += text_wrap(err.message)
            raise QuizMLYamlSyntaxError(msg)

    doc = {
        "header": _to_plain_python(header_data) if header_data else {},
        "questions": _to_plain_python(questions_data) if questions_data else [],
        "paths": {"input_dir": str(base_dir), "figure_dirs": figure_dirs},
    }
    doc = coerce_data(doc, schema)

    return doc, schema


def apply_schema_extensions(schema, extensions):
    """Return a deep copy of schema extended with header_properties, question_properties, and question_types."""
    import copy

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


def load(quizmlyaml_path, validate=True, schema_path=None, schema_extensions=None):
    import sys

    if quizmlyaml_path == "-":
        quizmlyaml_txt = sys.stdin.read()
        base_dir = Path.cwd().resolve()
        filename = "<stdin>"
        stem = "stdin"
    else:
        try:
            quizmlyaml_txt = Path(quizmlyaml_path).read_text(encoding="utf-8")
        except FileNotFoundError as err:
            raise QuizMLYamlSyntaxError(
                f"Yaml file not found: {quizmlyaml_path}"
            ) from err
        base_dir = Path(quizmlyaml_path).parent.resolve()
        filename = str(quizmlyaml_path)
        stem = Path(quizmlyaml_path).stem

    schema = None
    if validate:
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
        except FileNotFoundError as err:
            schema_name = schema_path or "packaged schema.json"
            raise QuizMLYamlSyntaxError(
                f"Schema file not found: {schema_name}"
            ) from err
        except (json.JSONDecodeError, YAMLError) as err:
            raise QuizMLYamlSyntaxError(f"Invalid schema syntax: {err}") from err
        except TypeError as err:
            raise QuizMLYamlSyntaxError(
                "Schema must be provided for validation when validate=True."
            ) from err

    doc, _ = loads(
        quizmlyaml_txt,
        validate=validate,
        schema=schema,
        filename=filename,
        base_dir=base_dir,
    )

    # passing the input quiz file's basename to header
    doc["header"]["inputbasename"] = stem

    return doc, schema

