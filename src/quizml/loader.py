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

import os
import re
import json
from pathlib import Path

import logging

from ruamel.yaml import YAML
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.nodes import ScalarNode
from ruamel.yaml.scalarstring import PlainScalarString
from jsonschema import Draft7Validator, validators
from jsonschema.exceptions import ValidationError

from quizml.utils import filter_yaml, text_wrap, msg_context
from quizml.exceptions import QuizMLYamlSyntaxError

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
    'tag:yaml.org,2002:bool', StringConstructor.construct_scalar)
StringConstructor.add_constructor(
    'tag:yaml.org,2002:int', StringConstructor.construct_scalar)
StringConstructor.add_constructor(
    'tag:yaml.org,2002:float', StringConstructor.construct_scalar)
StringConstructor.add_constructor(
    'tag:yaml.org,2002:null', StringConstructor.construct_scalar)


# --- Custom jsonschema Validator and Type Conversion ---

def is_string(checker, instance):
    return isinstance(instance, str)

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
    if isinstance(instance, bool): return False
    if isinstance(instance, int): return True
    if isinstance(instance, str):
        try:
            return str(int(instance)) == instance
        except (ValueError, TypeError):
            return False
    return False

def is_boolean(checker, instance):
    if isinstance(instance, bool): return True
    if isinstance(instance, str):
        return instance.lower() in ['true', 'false', 'yes', 'no', 'on', 'off']
    return False

CustomTypeChecker = Draft7Validator.TYPE_CHECKER.redefine_many({
    "number": is_number, "integer": is_integer, "boolean": is_boolean})

def coerce_value(value, schema):
    """
    Attempt to coerce the value to the types specified in schema.
    Prioritizes Boolean > Integer > Number to match most specific types first.
    """
    types = schema.get("type", [])
    if isinstance(types, str):
        types = [types]
        
    # Check boolean
    if "boolean" in types:
        if is_boolean(None, value):
            if isinstance(value, str):
                return value.lower() in ['true', 'yes', 'on']
            return value

    # Check integer
    if "integer" in types:
        if is_integer(None, value):
            if isinstance(value, str):
                return int(value)
            return value

    # Check number
    if "number" in types:
        if is_number(None, value):
            if isinstance(value, str):
                return float(value)
            return value
            
    return value

def extend_with_coercion(validator_class):
    """
    Extends the validator to coerce types based on schema before validation.
    """
    validate_properties = validator_class.VALIDATORS["properties"]
    validate_items = validator_class.VALIDATORS["items"]

    def coercing_properties(validator, properties, instance, schema):
        if isinstance(instance, dict):
            for prop, subschema in properties.items():
                if prop in instance:
                    instance[prop] = coerce_value(instance[prop], subschema)
        yield from validate_properties(validator, properties, instance, schema)

    def coercing_items(validator, items, instance, schema):
        if isinstance(instance, list):
            if isinstance(items, dict):
                for i in range(len(instance)):
                    instance[i] = coerce_value(instance[i], items)
            elif isinstance(items, list):
                for i, subschema in enumerate(items):
                    if i < len(instance):
                        instance[i] = coerce_value(instance[i], subschema)
        yield from validate_items(validator, items, instance, schema)

    return validators.extend(
        validator_class, 
        {"properties": coercing_properties, "items": coercing_items}
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

# Chain the validators: Defaults -> Coercion -> Validation
DefaultFillingValidator = extend_with_default(
    extend_with_coercion(
        validators.extend(Draft7Validator, type_checker=CustomTypeChecker)
    )
)



def _parse_yaml_fragment(text, validate=True, schema=None, filename="<string>"):
    """
    Parses a single YAML fragment.
    Optionally validates against a schema (dict).
    """
    yaml = YAML()
    yaml.Constructor = StringConstructor
    try:
        data = yaml.load(text)
    except Exception as err:
        line = -1
        if hasattr(err, 'problem_mark'): line = err.problem_mark.line
        raise QuizMLYamlSyntaxError(f"YAML parsing error in {filename} near line {line}:\n{err}")

    if validate and schema:
        validator = DefaultFillingValidator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            err = errors[0]
            path = " -> ".join(map(str, err.path))
            try:
                item = data
                for key in err.path: item = item[key]
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
    Identifies header and questions documents, parses them, and returns the data structure.
    """
    
    # Extracting the header and questions
    yamldoc_pattern = re.compile(r"^---\s*$", re.MULTILINE)
    yamldocs = yamldoc_pattern.split(quizmlyaml_txt)
    yamldocs = list(filter(None, yamldocs))

    if len(yamldocs) > 2:
        raise QuizMLYamlSyntaxError(
            ("YAML file cannot have more than 2 documents: "
             "one for the header and one for the questions."))

    doc = {'header': {}, 'questions': []}

    # Check if the first document starts with a list item indicator ('-')
    doc_starts_with_list = re.search(r"^\s*-", yamldocs[0], re.MULTILINE)
    
    # Assign header_doc and questions_doc simultaneously based on the conditions.
    if doc_starts_with_list:
        # this is a bit of a hack: if we only have one document and that
        # it contains a list, then we assume that it is a list of questions
        header_doc, questions_doc = None, yamldocs[0]
    elif len(yamldocs) == 2:
        # contains both a header and a list of questions
        header_doc, questions_doc = yamldocs[0], yamldocs[1]
    else:
        # just a header, no questions
        header_doc, questions_doc = yamldocs[0], None

    doc['header'] = _parse_yaml_fragment(
        header_doc,
        validate=False,
        filename=filename
    )  if header_doc else {}

    doc['questions'] = _parse_yaml_fragment(
        questions_doc,
        validate=validate,
        filename=filename,
        schema=schema
    ) if questions_doc else []

    # removing trailing white spaces in all string values
    f = lambda a: a.strip() if isinstance(a, str) else a
    doc = filter_yaml(doc, f)

    return _to_plain_python(doc)


def load(quizmlyaml_path, validate=True, schema_path=None):
    try:
        quizmlyaml_txt = Path(quizmlyaml_path).read_text()
    except FileNotFoundError:
        raise QuizMLYamlSyntaxError(f"Yaml file not found: {quizmlyaml_path}")

    schema = None
    if validate:
        if schema_path is None:
            from quizml.cli.filelocator import locate
            schema_path = locate.path("schema.json")
        try:
            schema_str = Path(schema_path).read_text()
            schema = json.loads(schema_str)
        except FileNotFoundError:
            raise QuizMLYamlSyntaxError(f"Schema file not found: {schema_path}")
        except json.JSONDecodeError as e:
            raise QuizMLYamlSyntaxError(f"Invalid JSON in schema: {e}")
        except TypeError:
            raise QuizMLYamlSyntaxError("Schema must be provided for validation when validate=True.")
    
    doc = loads(
        quizmlyaml_txt,
        validate=validate,
        schema=schema,
        filename=str(quizmlyaml_path)
    )

    # passing the input quiz file's basename to header
    basename, _ = os.path.splitext(quizmlyaml_path)
    doc['header']['inputbasename'] = basename

    return doc
