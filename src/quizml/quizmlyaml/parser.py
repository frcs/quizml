"""YAML parsing using ruamel.yaml with string-safe scalar loading."""

from ruamel.yaml import YAML
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.nodes import ScalarNode
from ruamel.yaml.scalarstring import PlainScalarString

from quizml.exceptions import QuizMLYamlSyntaxError


class StringConstructor(RoundTripConstructor):
    """A custom constructor for ruamel.yaml that treats all scalar values

    as strings, preserving the original text and line/column info.
    Prevents the YAML 'Norway problem' (e.g. 'NO' becoming False).
    """

    def construct_scalar(self, node: ScalarNode):
        return PlainScalarString(node.value, anchor=node.anchor)


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


def _to_plain_python(data):
    """Recursively converts ruamel data structures to plain Python dicts/lists."""
    if isinstance(data, dict):
        return {k: _to_plain_python(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_plain_python(v) for v in data]
    return data


def parse_yaml_docs(
    yaml_text: str, filename: str = "<string>"
) -> tuple[dict, list]:
    """Parses QuizML YAML text into a (header_dict, questions_list) tuple.

    Uses StringConstructor so scalar values are loaded as strings for jsonschema.
    Filters empty/blank documents and validates that there are at most 2 documents
    (header + questions).
    """
    yaml = YAML()
    yaml.Constructor = StringConstructor
    try:
        raw_docs = list(yaml.load_all(yaml_text))
    except Exception as err:
        line = -1
        if hasattr(err, "problem_mark"):
            line = err.problem_mark.line
        raise QuizMLYamlSyntaxError(
            f"YAML parsing error in {filename} near line {line}:\n{err}"
        ) from err

    docs = [
        d
        for d in raw_docs
        if d is not None and not (isinstance(d, str) and not d.strip())
    ]

    if len(docs) > 2:
        raise QuizMLYamlSyntaxError(
            f"YAML file {filename} cannot have more than 2 documents: "
            "one for the header and one for the questions."
            if filename != "<string>"
            else "YAML file cannot have more than 2 documents: "
            "one for the header and one for the questions."
        )

    if not docs:
        return {}, []

    if len(docs) == 1:
        if isinstance(docs[0], list):
            return {}, docs[0]
        elif isinstance(docs[0], dict):
            return docs[0], []
        else:
            return {}, []

    header, questions = docs[0], docs[1]
    if not isinstance(questions, list):
        raise QuizMLYamlSyntaxError(
            f"Questions in {filename} must be a YAML list."
            if filename != "<string>"
            else "Questions must be a YAML list."
        )
    return header if isinstance(header, dict) else {}, questions
