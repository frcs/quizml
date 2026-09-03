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


def _parse_yaml_fragment(text, validate=True, schema=None, filename="<string>"):
    """
    Parses a single YAML fragment.
    Optionally validates against a schema (dict).
    """

    # loading all scalars as strings
    yaml = YAML()
    yaml.Constructor = StringConstructor
    try:
        data = yaml.load(text)
    except Exception as err:
        line = -1
        if hasattr(err, "problem_mark"):
            line = err.problem_mark.line
        raise QuizMLYamlSyntaxError(
            f"YAML parsing error in {filename} near line {line}:\n{err}"
        ) from err

    # validating against the schema
    if validate and schema:
        validator = DefaultFillingValidator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            err = errors[0]
            path = " -> ".join(map(str, err.path))
            try:
                item = data
                for key in err.path:
                    item = item[key]
                line_num = item.lc.line + 1
            except (KeyError, IndexError, AttributeError):
                line_num = "unknown"
            lines = text.splitlines()
            msg = f"Schema validation error in {filename} at '{path}' (line ~{line_num})\n"
            if line_num != "unknown":
                msg += msg_context(lines, line_num) + "\n"
            msg += text_wrap(err.message)
            raise QuizMLYamlSyntaxError(msg)

    return data


def _to_plain_python(data):
    if isinstance(data, dict):
        return {k: _to_plain_python(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_plain_python(v) for v in data]
    return data


def loads(quizmlyaml_txt, validate=True, schema=None, filename="<string>"):
    """
    Parses a QuizML string.
    Identifies header and questions documents using native YAML multi-doc parsing,
    validates questions against the schema, and returns the data structure.
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
        quizmlyaml_txt = Path(quizmlyaml_path).read_text()
    except FileNotFoundError as err:
        raise QuizMLYamlSyntaxError(f"Yaml file not found: {quizmlyaml_path}") from err

    schema = None
    if validate:
        if schema_path is None:
            from quizml.cli.filelocator import locate

            schema_path = locate.path("schema.json")
        try:
            schema_str = Path(schema_path).read_text()
            schema = json.loads(schema_str)
        except FileNotFoundError as err:
            raise QuizMLYamlSyntaxError(f"Schema file not found: {schema_path}") from err
        except json.JSONDecodeError as err:
            raise QuizMLYamlSyntaxError(f"Invalid JSON in schema: {err}") from err
        except TypeError as err:
            raise QuizMLYamlSyntaxError(
                "Schema must be provided for validation when validate=True."
            ) from err

    doc, _ = loads(
        quizmlyaml_txt, validate=validate, schema=schema, filename=str(quizmlyaml_path)
    )

    # passing the input quiz file's basename to header
    basename, _ = os.path.splitext(quizmlyaml_path)
    doc["header"]["inputbasename"] = basename

    return doc, schema