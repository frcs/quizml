"""QuizML YAML Ingestion and Validation module.

Handles string-safe scalar parsing, recursive _include resolution,
JSON Schema validation with default values injection, and type coercion.
"""

import os
from pathlib import Path

from quizml.exceptions import QuizMLYamlSyntaxError
from quizml.quizmlyaml.includes import count_included_questions, resolve_includes
from quizml.quizmlyaml.parser import (
    StringConstructor,
    _to_plain_python,
    parse_yaml_docs,
)
from quizml.quizmlyaml.schema import load_schema
from quizml.quizmlyaml.validator import (
    DefaultFillingValidator,
    MarkdownString,
    coerce_data,
    validate_questions,
)


def loads(
    quizmlyaml_txt: str,
    validate: bool = True,
    schema: dict | None = None,
    filename: str = "<string>",
    base_dir: str | Path | None = None,
) -> tuple[dict, dict | None]:
    """Parses QuizML YAML text into a structured document dict (header + questions).

    Resolves '_include' directives, validates against schema (if validate=True),
    and coerces values based on schema definitions.
    """
    header_data, questions_data = parse_yaml_docs(quizmlyaml_txt, filename=filename)

    if base_dir is None:
        if filename and filename != "<string>":
            base_dir = Path(filename).parent.resolve()
        else:
            base_dir = Path.cwd()
    else:
        base_dir = Path(base_dir).resolve()

    if questions_data and isinstance(questions_data, list):
        accumulated_figure_dirs = []
        questions_data = resolve_includes(
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

    if validate and schema and questions_data:
        validate_questions(quizmlyaml_txt, questions_data, schema, filename=filename)

    doc = {
        "header": _to_plain_python(header_data) if header_data else {},
        "questions": _to_plain_python(questions_data) if questions_data else [],
    }
    doc = coerce_data(doc, schema)

    return doc, schema


def load(
    quizmlyaml_path: str | Path,
    validate: bool = True,
    schema_path: str | Path | None = None,
) -> tuple[dict, dict | None]:
    """Loads a QuizML YAML file from disk, validates, and returns (doc, schema)."""
    try:
        quizmlyaml_txt = Path(quizmlyaml_path).read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise QuizMLYamlSyntaxError(f"Yaml file not found: {quizmlyaml_path}") from err

    schema = None
    if validate:
        schema = load_schema(schema_path)

    doc, _ = loads(
        quizmlyaml_txt,
        validate=validate,
        schema=schema,
        filename=str(quizmlyaml_path),
        base_dir=Path(quizmlyaml_path).parent.resolve(),
    )

    basename, _ = os.path.splitext(quizmlyaml_path)
    doc["header"]["inputbasename"] = basename

    return doc, schema


__all__ = [
    "load",
    "loads",
    "load_schema",
    "count_included_questions",
    "MarkdownString",
    "StringConstructor",
    "DefaultFillingValidator",
    "parse_yaml_docs",
    "resolve_includes",
    "coerce_data",
]
