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

from quizml.utils import filter_yaml
from quizml.exceptions import QuizMLYamlSyntaxError
from quizml.cli.errorhandler import text_wrap, msg_context

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
    if not is_string(checker, instance): return False
    try:
        float(instance)
        return True
    except (ValueError, TypeError):
        return False

def is_integer(checker, instance):
    if not is_string(checker, instance): return False
    try:
        return str(int(instance)) == instance
    except (ValueError, TypeError):
        return False

def is_boolean(checker, instance):
    if not is_string(checker, instance): return False
    return instance.lower() in ['true', 'false', 'yes', 'no', 'on', 'off']

CustomTypeChecker = Draft7Validator.TYPE_CHECKER.redefine_many({
    "number": is_number, "integer": is_integer, "boolean": is_boolean})

def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]
    def set_defaults(validator, properties, instance, schema):
        if isinstance(instance, dict):
            for prop, subschema in properties.items():
                if "default" in subschema:
                    instance.setdefault(prop, subschema["default"])
        yield from validate_properties(validator, properties, instance, schema)
    return validators.extend(validator_class, {"properties": set_defaults})

DefaultFillingValidator = extend_with_default(
    validators.extend(Draft7Validator, type_checker=CustomTypeChecker))


# --- Main Loader Functions ---
def load_quizmlyaml(quizmlyaml_txt, validate=True, filename="<YAML string>", schema_str=None):
    yaml = YAML()
    yaml.Constructor = StringConstructor
    try:
        data = yaml.load(quizmlyaml_txt)
    except Exception as err:
        line = -1
        if hasattr(err, 'problem_mark'): line = err.problem_mark.line
        raise QuizMLYamlSyntaxError(f"YAML parsing error in {filename} near line {line}:\n{err}")

    if validate:
        if schema_str is None:
            raise QuizMLYamlSyntaxError("Schema must be provided for validation when validate=True.")
        try:
            schema = json.loads(schema_str)
        except json.JSONDecodeError as e:
            raise QuizMLYamlSyntaxError(f"Invalid JSON in schema: {e}")

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
            lines = quizmlyaml_txt.splitlines()
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

def load(quizmlyaml_path, validate=True, schema_path=None):
    try:
        quizmlyaml_txt = Path(quizmlyaml_path).read_text()
    except FileNotFoundError:
        raise QuizMLYamlSyntaxError(f"Yaml file not found: {quizmlyaml_path}")

    schema_str = None
    if validate:
        if schema_path is None:
            from quizml.cli.filelocator import locate
            schema_path = locate.path("schema.json")
        try:
            schema_str = Path(schema_path).read_text()
        except FileNotFoundError:
            raise QuizMLYamlSyntaxError(f"Schema file not found: {schema_path}")
        except TypeError:
            raise QuizMLYamlSyntaxError("Schema must be provided for validation when validate=True.")
    
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

    doc['header'] = load_quizmlyaml(
        header_doc,
        validate=False,
        filename=quizmlyaml_path
    )  if header_doc else {}

    doc['questions'] = load_quizmlyaml(
        questions_doc,
        validate,
        filename=quizmlyaml_path,
        schema_str=schema_str
    ) if questions_doc else []

    # removing trailing white spaces in all string values
    f = lambda a: a.strip() if isinstance(a, str) else a
    doc = filter_yaml(doc, f)

    # passing the input quiz file's basename to header
    basename, _ = os.path.splitext(quizmlyaml_path)
    doc['header']['inputbasename'] = basename

    # BRUTE FORCE CONVERSION
    for q in doc.get('questions', []):
        if 'marks' in q and isinstance(q['marks'], str):
            try: q['marks'] = float(q['marks'])
            except (ValueError, TypeError): pass
        if 'cols' in q and isinstance(q['cols'], str):
            try: q['cols'] = int(q['cols'])
            except (ValueError, TypeError): pass
        if 'answer' in q and isinstance(q['answer'], str):
            if q['answer'].lower() == 'true': q['answer'] = True
            elif q['answer'].lower() == 'false': q['answer'] = False

    return _to_plain_python(doc)
