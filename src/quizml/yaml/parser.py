"""YAML parsing primitives for QuizML multi-document files."""

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.error import YAMLError
from ruamel.yaml.nodes import ScalarNode
from ruamel.yaml.scalarstring import PlainScalarString

from quizml.exceptions import QuizMLError, QuizMLYamlSyntaxError


class StringConstructor(RoundTripConstructor):
    """Custom ruamel.yaml constructor that loads all non-null scalars as strings.

    Loading scalars as ``PlainScalarString`` accomplishes two goals:
    1. It preserves ``.lc`` line and column metadata on every node for
       accurate JSON Schema validation diagnostics.
    2. It avoids YAML 1.1/1.2 implicit typing surprises (such as unquoted
       ``yes``/``no``/``on``/``off`` or octal numbers) before explicit
       schema-driven validation and type coercion in ``schema.py``.
    """

    def construct_scalar(self, node: ScalarNode) -> PlainScalarString | None:
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


def to_plain_python(data: Any) -> Any:
    """Convert ruamel.yaml wrapper objects into plain Python structures."""
    if isinstance(data, dict):
        return {str(k): to_plain_python(v) for k, v in data.items()}
    if isinstance(data, list):
        return [to_plain_python(v) for v in data]
    if isinstance(data, str):
        return str(data)
    return data


def peek_yaml_header(yaml_filename: str | Path | None) -> dict[str, Any]:
    """Best-effort peek at the first YAML document if it is a mapping header."""
    if not yaml_filename or str(yaml_filename) == "-":
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


def extract_figure_paths(header: Any, base_dir: Path) -> list[Path]:
    """Return resolved figure search paths declared in ``header['_figures_path']``."""
    if not isinstance(header, dict):
        return []
    paths = header.get("_figures_path", [])
    if isinstance(paths, str):
        paths = [paths]
    if not isinstance(paths, list):
        return []
    result: list[Path] = []
    for p in paths:
        p_str = str(p).strip()
        if not p_str:
            continue
        p_obj = Path(p_str).expanduser()
        result.append(
            p_obj.resolve() if p_obj.is_absolute() else (base_dir / p_obj).resolve()
        )
    return result


def parse_quiz_yaml_text(
    text: str,
    source_label: str | Path = "<string>",
    *,
    include_line_in_error: bool = True,
    max_docs_message: str | None = None,
) -> tuple[Any, list[Any]]:
    """Parse a QuizML YAML string into ``(header_data, questions_data)``.

    QuizML files contain up to 2 YAML documents separated by ``---``:
    - 0 documents: returns ``({}, [])``.
    - 1 document: if it is a YAML list, treats it as ``({}, questions)``;
      otherwise treats it as ``(header, [])``.
    - 2 documents: treats the first as ``header`` and the second as ``questions``.
    """
    yaml = YAML()
    yaml.Constructor = StringConstructor
    try:
        raw_docs = list(yaml.load_all(text))
    except YAMLError as err:
        if include_line_in_error:
            line = getattr(getattr(err, "problem_mark", None), "line", -1)
            raise QuizMLYamlSyntaxError(
                f"YAML parsing error in {source_label} near line {line}:\n{err}"
            ) from err
        raise QuizMLYamlSyntaxError(
            f"YAML parsing error in included file {source_label}: {err}"
        ) from err

    # Ignore empty documents (e.g. leading/trailing '---' or whitespace-only blocks).
    docs = [
        doc
        for doc in raw_docs
        if doc is not None and not (isinstance(doc, str) and not doc.strip())
    ]

    if len(docs) > 2:
        msg = max_docs_message or (
            "YAML file cannot have more than 2 documents: "
            "one for the header and one for the questions."
        )
        raise QuizMLYamlSyntaxError(msg)

    if not docs:
        return {}, []
    if len(docs) == 1:
        if isinstance(docs[0], list):
            return {}, docs[0]
        return docs[0], []
    return docs[0], docs[1]


def read_question_file(path: Path) -> tuple[Any, list[Any], str]:
    """Read an included QuizML YAML file and return ``(header, questions, text)``."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise QuizMLYamlSyntaxError(
            f"Error reading included file '{path}': {err}"
        ) from err

    header, questions = parse_quiz_yaml_text(
        text,
        source_label=path,
        include_line_in_error=False,
        max_docs_message=f"Included file {path} cannot have more than 2 documents.",
    )
    if not isinstance(questions, list):
        raise QuizMLYamlSyntaxError(
            f"Questions in included file {path} must be a YAML list."
        )
    return header, questions, text


def parse_roundtrip_yaml_text(
    text: str, label: str | Path = "<string>"
) -> tuple[YAML, list[Any], int | None]:
    """Parse multi-document QuizML YAML preserving comments for round-trip tools.

    Returns ``(yaml_instance, docs_list, questions_doc_index)``, where
    ``questions_doc_index`` is the index in ``docs_list`` containing the
    questions list (``0`` for a headerless file, ``1`` for a 2-document file,
    or ``None`` if the file has no documents).
    """
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


def read_roundtrip_yaml(path: Path) -> tuple[YAML, list[Any], int | None]:
    """Read a YAML file preserving comments for round-trip tools (sample, pin, grep)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise QuizMLError(f"Could not read YAML file {path}: {err}") from err
    return parse_roundtrip_yaml_text(text, path)
