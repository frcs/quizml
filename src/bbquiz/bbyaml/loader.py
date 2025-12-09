"""BBYaml load file

This module provides the function for loading BBYaml files as a
list/dict structure.

BBYaml files are a form of YAML. To avoid issues like the "Norway
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

from ruamel.yaml import YAML
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.nodes import ScalarNode
from ruamel.yaml.scalarstring import PlainScalarString
from jsonschema import Draft7Validator, validators
from jsonschema.exceptions import ValidationError

from bbquiz.bbyaml.utils import filter_yaml
from bbquiz.exceptions import BBYamlSyntaxError
from ..cli.errorhandler import text_wrap, msg_context

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

def load_yaml(bbyaml_txt, validate=True, filename="<YAML string>", schema_path=None):
    yaml = YAML()
    yaml.Constructor = StringConstructor
    try:
        data = yaml.load(bbyaml_txt)
    except Exception as err:
        line = -1
        if hasattr(err, 'problem_mark'): line = err.problem_mark.line
        raise BBYamlSyntaxError(f"YAML parsing error in {filename} near line {line}:\n{err}")

    if validate:
        if schema_path is None:
            schema_dir = Path(__file__).parent
            schema_path = schema_dir / "schema.json"
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
        except FileNotFoundError:
            raise BBYamlSyntaxError(f"Schema file not found: {schema_path}")
        except json.JSONDecodeError as e:
            raise BBYamlSyntaxError(f"Invalid JSON in schema file {schema_path}: {e}")

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
            lines = bbyaml_txt.splitlines()
            msg = f"Schema validation error in {filename} at '{path}' (line ~{line_num})\n"
            if line_num != "unknown":
                msg += msg_context(lines, line_num) + "\n"
            msg += text_wrap(err.message)
            raise BBYamlSyntaxError(msg)
        
    return data

def _to_plain_python(data):
    if isinstance(data, dict):
        return {k: _to_plain_python(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_plain_python(v) for v in data]
    return data

def load(bbyaml_filename, validate=True, schema_path=None):
    try:
        bbyaml_txt = Path(bbyaml_filename).read_text()
    except FileNotFoundError:
        raise BBYamlSyntaxError(f"File not found: {bbyaml_filename}")

    yamldoc_pattern = re.compile(r"^---\s*$", re.MULTILINE)
    yamldocs = yamldoc_pattern.split(bbyaml_txt)
    yamldocs = list(filter(None, yamldocs))

    if len(yamldocs) > 2:
        raise BBYamlSyntaxError(
            ("YAML file cannot have more than 2 documents: "
             "one for the header and one for the questions."))

    doc = {'header': {}, 'questions': []}

    doc_starts_with_list = re.search(r"^\s*-", yamldocs[0], re.MULTILINE)
    # logic is that if 
    if doc_starts_with_list:
        questions_doc = yamldocs[0]
        header_doc = ""        
    elif len(yamldocs) == 2:
        questions_doc = yamldocs[1]
        header_doc = yamldocs[0]    
    else:
        header_doc = yamldocs[0]
        questions_doc = ""

    doc['header'] = load_yaml(
        header_doc,
        validate=False,
        filename=bbyaml_filename)

    doc['questions'] = load_yaml(
        questions_doc,
        validate,
        filename=bbyaml_filename,
        schema_path=schema_path)
       

    # if len(yamldocs) == 1:
    #     yamldoc_txt = yamldocs[0]
    #     if re.search(r"^\s*-", yamldoc_txt, re.MULTILINE):
    #         doc['questions'] = load_yaml(
    #             yamldoc_txt,
    #             validate,
    #             filename=bbyaml_filename,
    #             schema_path=schema_path)
    #     else:
    #         doc['header'] = load_yaml(
    #             yamldoc_txt,
    #             validate=False,
    #             filename=bbyaml_filename)
    # else:
    #     doc['header'] = load_yaml(
    #         yamldocs[0],
    #         validate=False,
    #         filename=bbyaml_filename)
    #     doc['questions'] = load_yaml(
    #         yamldocs[1], validate,
    #         filename=bbyaml_filename,
    #         schema_path=schema_path)

        
    f = lambda a: a.strip() if isinstance(a, str) else a
    doc = filter_yaml(doc, f)

    # I am commenting this out
    # no more hearder type
    
    # if doc['questions'] and doc['questions'][0].get('type') == 'header':
    #     h = doc['questions'].pop(0)
    #     del h['type']
    #     doc['header'].update(h)

    basename, _ = os.path.splitext(bbyaml_filename)
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
