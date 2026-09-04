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
import random
from pathlib import Path

from jsonschema import Draft7Validator, validators
from ruamel.yaml import YAML
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.nodes import ScalarNode
from ruamel.yaml.scalarstring import PlainScalarString

from quizml.exceptions import QuizMLYamlSyntaxError
from quizml.utils import coerce_data, msg_context, text_wrap

# --- Custom ruamel.yaml Constructor ---


class StringConstructor(RoundTripConstructor):
    """
    A custom constructor for ruamel.yaml that treats all scalar values
    as strings, preserving the original text and line/column info.
    """

    def construct_scalar(self, node: ScalarNode):
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
        return {k: _to_plain_python(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_plain_python(v) for v in data]
    return data


def count_included_questions(
    item: dict, base_dir: Path, visited: set[Path] | None = None
) -> int:
    """Calculates the number of questions contributed by an _include item.

    Accounts for 'count' sampling and recursively counts nested _include items.
    Falls back gracefully if the file cannot be accessed.
    """
    if visited is None:
        visited = set()

    inc_file = str(item.get("_include", "")).strip()
    if not inc_file:
        return 0

    inc_path = (
        Path(inc_file).resolve()
        if os.path.isabs(inc_file)
        else (base_dir / inc_file).resolve()
    )

    if not inc_path.is_file() or inc_path in visited:
        if "count" in item:
            try:
                return max(0, int(item["count"]))
            except (ValueError, TypeError):
                pass
        return 1

    try:
        inc_text = inc_path.read_text(encoding="utf-8")
        inc_yaml = YAML()
        raw_docs = list(inc_yaml.load_all(inc_text))
    except Exception:
        if "count" in item:
            try:
                return max(0, int(item["count"]))
            except (ValueError, TypeError):
                pass
        return 1

    sub_docs = [
        d
        for d in raw_docs
        if d is not None and not (isinstance(d, str) and not d.strip())
    ]
    if not sub_docs:
        return 0

    if len(sub_docs) == 1:
        sub_questions = sub_docs[0] if isinstance(sub_docs[0], list) else []
    else:
        sub_questions = sub_docs[1] if isinstance(sub_docs[1], list) else []

    if not isinstance(sub_questions, list):
        return 0

    new_visited = visited | {inc_path}
    total = 0
    for q in sub_questions:
        if isinstance(q, dict) and "_include" in q:
            total += count_included_questions(q, inc_path.parent, new_visited)
        else:
            total += 1

    if "count" in item:
        try:
            sample_count = max(0, int(item["count"]))
            return min(sample_count, total)
        except (ValueError, TypeError):
            pass

    return total


def _resolve_includes(
    questions_data: list,
    base_dir: Path,
    root_dir: Path,
    visited: set[Path] | None = None,
    accumulated_figure_dirs: list[str] | None = None,
) -> list:
    """Recursively resolves '- _include: filename.yaml' directives in the questions list.

    Supports optional 'count' (for sampling) and 'seed' (for reproducible sampling).
    Detects circular includes using the visited set.
    Accumulates figure search directories relative to root_dir.
    """
    if visited is None:
        visited = set()
    if accumulated_figure_dirs is None:
        accumulated_figure_dirs = []

    resolved = []
    for item in questions_data:
        if isinstance(item, dict) and "include" in item and "_include" not in item:
            raise QuizMLYamlSyntaxError(
                "Unknown directive 'include'. Did you mean '_include'?"
            )
        if isinstance(item, dict) and "_include" in item:
            inc_file = str(item["_include"]).strip()
            inc_path = (
                Path(inc_file).resolve()
                if os.path.isabs(inc_file)
                else (base_dir / inc_file).resolve()
            )

            if not inc_path.is_file():
                raise QuizMLYamlSyntaxError(
                    f"Included YAML file not found: '{inc_file}' (resolved to '{inc_path}')"
                )

            if inc_path in visited:
                raise QuizMLYamlSyntaxError(
                    f"Circular include detected: '{inc_path}' is already in the inclusion chain."
                )

            try:
                inc_text = inc_path.read_text(encoding="utf-8")
            except Exception as err:
                raise QuizMLYamlSyntaxError(
                    f"Error reading included file '{inc_path}': {err}"
                ) from err

            inc_yaml = YAML()
            inc_yaml.Constructor = StringConstructor
            try:
                raw_docs = list(inc_yaml.load_all(inc_text))
            except Exception as err:
                raise QuizMLYamlSyntaxError(
                    f"YAML parsing error in included file {inc_path}: {err}"
                ) from err

            sub_docs = [
                d
                for d in raw_docs
                if d is not None and not (isinstance(d, str) and not d.strip())
            ]

            if not sub_docs:
                sub_questions = []
            elif len(sub_docs) == 1:
                sub_questions = sub_docs[0] if isinstance(sub_docs[0], list) else []
            elif len(sub_docs) == 2:
                sub_questions = sub_docs[1] if isinstance(sub_docs[1], list) else []
            else:
                raise QuizMLYamlSyntaxError(
                    f"Included file {inc_path} cannot have more than 2 documents."
                )

            if not isinstance(sub_questions, list):
                raise QuizMLYamlSyntaxError(
                    f"Questions in included file {inc_path} must be a YAML list."
                )

            # Accumulate figure paths from sub-file
            if len(sub_docs) == 2 and isinstance(sub_docs[0], dict):
                sub_figures = sub_docs[0].get("_figures_path", [])
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
            )

            # Optional sampling
            if "count" in item:
                try:
                    count = int(item["count"])
                except (ValueError, TypeError) as err:
                    raise QuizMLYamlSyntaxError(
                        f"Include 'count' must be an integer, got '{item['count']}'"
                    ) from err

                if count < 0:
                    raise QuizMLYamlSyntaxError(
                        f"Include 'count' cannot be negative, got {count}"
                    )

                seed = item.get("seed")
                rng = random.Random(seed) if seed is not None else random.Random()
                if count < len(sub_questions):
                    sub_questions = rng.sample(sub_questions, count)

            resolved.extend(sub_questions)
        else:
            resolved.append(item)

    return resolved


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
    except Exception as err:
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

    if len(yamldocs) > 2:
        raise QuizMLYamlSyntaxError(
            "YAML file cannot have more than 2 documents: "
            "one for the header and one for the questions."
        )

    if not yamldocs:
        return {"header": {}, "questions": []}, schema

    if len(yamldocs) == 1:
        if isinstance(yamldocs[0], list):
            header_data, questions_data = {}, yamldocs[0]
        else:
            header_data, questions_data = yamldocs[0], []
    else:
        header_data, questions_data = yamldocs[0], yamldocs[1]

    if base_dir is None:
        if filename and filename != "<string>":
            base_dir = Path(filename).parent.resolve()
        else:
            base_dir = Path.cwd()

    if questions_data and isinstance(questions_data, list):
        accumulated_figure_dirs = []
        questions_data = _resolve_includes(
            questions_data,
            base_dir=base_dir,
            root_dir=base_dir,
            accumulated_figure_dirs=accumulated_figure_dirs,
        )
        if accumulated_figure_dirs:
            if not isinstance(header_data, dict):
                header_data = {}
            existing_figs = header_data.get("_figures_path", [])
            if isinstance(existing_figs, str):
                existing_figs = [existing_figs]
            elif not isinstance(existing_figs, list):
                existing_figs = []
            combined = list(
                dict.fromkeys(list(existing_figs) + accumulated_figure_dirs)
            )
            header_data["_figures_path"] = combined

    # Validating questions against the schema
    if validate and schema and questions_data:
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
                msg += msg_context(lines, line_num) + "\n"
            msg += text_wrap(err.message)
            raise QuizMLYamlSyntaxError(msg)

    doc = {
        "header": _to_plain_python(header_data) if header_data else {},
        "questions": _to_plain_python(questions_data) if questions_data else [],
    }
    doc = coerce_data(doc, schema)

    return doc, schema


def load(quizmlyaml_path, validate=True, schema_path=None):
    try:
        quizmlyaml_txt = Path(quizmlyaml_path).read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise QuizMLYamlSyntaxError(f"Yaml file not found: {quizmlyaml_path}") from err

    schema = None
    if validate:
        if schema_path is None:
            from quizml.cli.filelocator import locate

            schema_path = locate.path("schema.json")
        try:
            schema_str = Path(schema_path).read_text(encoding="utf-8")
            schema = json.loads(schema_str)
        except FileNotFoundError as err:
            raise QuizMLYamlSyntaxError(
                f"Schema file not found: {schema_path}"
            ) from err
        except json.JSONDecodeError as err:
            raise QuizMLYamlSyntaxError(f"Invalid JSON in schema: {err}") from err
        except TypeError as err:
            raise QuizMLYamlSyntaxError(
                "Schema must be provided for validation when validate=True."
            ) from err

    doc, _ = loads(
        quizmlyaml_txt,
        validate=validate,
        schema=schema,
        filename=str(quizmlyaml_path),
        base_dir=Path(quizmlyaml_path).parent.resolve(),
    )

    # passing the input quiz file's basename to header
    basename, _ = os.path.splitext(quizmlyaml_path)
    doc["header"]["inputbasename"] = basename

    return doc, schema
