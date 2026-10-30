"""YAML parsing primitives for QuizML multi-document files."""

from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import ScalarNode
from ruamel.yaml.scalarstring import PlainScalarString

from quizml.exceptions import QuizMLError, QuizMLYamlSyntaxError


class StringConstructor(RoundTripConstructor):
    """Custom constructor for ruamel.yaml that treats all non-null scalars as strings,
    preserving original text and line/column info.
    """

    def construct_scalar(self, node: ScalarNode):
        if node.tag == "tag:yaml.org,2002:null":
            return None
        return PlainScalarString(node.value, anchor=node.anchor)


for _tag in (
    "tag:yaml.org,2002:bool",
    "tag:yaml.org,2002:int",
    "tag:yaml.org,2002:float",
    "tag:yaml.org,2002:null",
):
    StringConstructor.add_constructor(_tag, StringConstructor.construct_scalar)


def to_plain_python(data):
    """Convert ruamel.yaml comment/scalar wrapper objects into plain Python structures."""
    if isinstance(data, dict):
        return {str(k): to_plain_python(v) for k, v in data.items()}
    if isinstance(data, list):
        return [to_plain_python(v) for v in data]
    if isinstance(data, str):
        return str(data)
    return data


def peek_yaml_header(yaml_filename) -> dict:
    """Best-effort peek at the first YAML document if it is a mapping header."""
    if not yaml_filename or yaml_filename == "-":
        return {}
    try:
        path = Path(yaml_filename).expanduser()
        if not path.is_file():
            return {}
        with path.open(encoding="utf-8") as f:
            yaml = YAML(typ="safe")
            first_doc = next(yaml.load_all(f), None)
            if isinstance(first_doc, dict):
                return first_doc
    except (OSError, YAMLError):
        return {}
    return {}


def extract_figure_paths(header, base_dir: Path) -> list[Path]:
    """Return resolved figure search paths declared in header['_figures_path']."""
    if not isinstance(header, dict):
        return []
    paths = header.get("_figures_path", [])
    if isinstance(paths, str):
        paths = [paths]
    if not isinstance(paths, list):
        return []
    result = []
    for p in paths:
        p_str = str(p).strip()
        if not p_str:
            continue
        p_obj = Path(p_str).expanduser()
        result.append(
            p_obj.resolve() if p_obj.is_absolute() else (base_dir / p_obj).resolve()
        )
    return result


def read_question_file(path: Path):
    """Read one QuizML YAML file using StringConstructor and return (header, questions, text)."""
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


def parse_roundtrip_yaml_text(text: str, label="<string>"):
    """Parse multi-document QuizML YAML preserving comments for round-trip tools (sample, pin)."""
    yaml = YAML()
    try:
        docs = [doc for doc in yaml.load_all(text) if doc is not None]
    except YAMLError as err:
        raise QuizMLYamlSyntaxError(f"YAML parsing error in {label}: {err}") from err
    if len(docs) > 2:
        raise QuizMLYamlSyntaxError(
            f"YAML file {label} cannot have more than 2 documents"
        )
    if not docs:
        return yaml, [], None
    if len(docs) == 1:
        if isinstance(docs[0], list):
            return yaml, docs, 0
        return yaml, [docs[0], []], 1
    if not isinstance(docs[1], list):
        raise QuizMLYamlSyntaxError(f"Questions in {label} must be a YAML list")
    return yaml, docs, 1


def read_roundtrip_yaml(path: Path):
    """Read a YAML file preserving comments for round-trip tools."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise QuizMLError(f"Could not read YAML file {path}: {err}") from err
    return parse_roundtrip_yaml_text(text, path)
