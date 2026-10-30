"""Independent QuizML YAML and Question-Bank Module.

Provides multi-document YAML parsing, recursive ``_include`` expansion,
``select`` and deterministic ``count``/``seed`` sampling, JSON Schema validation
and type coercion, formatting, pinning, and diffing.
"""

import sys
from pathlib import Path
from typing import Any

from quizml.exceptions import QuizMLError, QuizMLYamlSyntaxError
from quizml.yaml.diff import (
    compare_quiz_files,
    get_choices_content,
    normalize_text,
    questions_are_similar,
)
from quizml.yaml.document import QuizDocument
from quizml.yaml.format import (
    clean_all_q_comments,
    format_yaml_text,
    is_blank_comment,
    is_q_comment,
    wrap_markdown,
    wrap_text_fields,
)
from quizml.yaml.grep import (
    GrepMatch,
    find_quiz_files_for_grep,
    format_matching_questions,
    grep_questions,
    is_question_match,
)
from quizml.yaml.includes import (
    count_included_questions,
    expand_roundtrip_includes,
    normalize_select_list,
    resolve_include_path,
    resolve_includes,
    resolve_select_indices,
    select_questions,
)
from quizml.yaml.parser import (
    StringConstructor,
    extract_figure_paths,
    parse_quiz_yaml_text,
    parse_roundtrip_yaml_text,
    peek_yaml_header,
    read_question_file,
    read_roundtrip_yaml,
    to_plain_python,
)
from quizml.yaml.pin import (
    default_version_constraint,
    generate_question_id,
    parse_version_tuple,
    pin_yaml_text,
)
from quizml.yaml.schema import (
    CustomTypeChecker,
    DefaultFillingValidator,
    MarkdownString,
    ScalarValidator,
    apply_schema_extensions,
    coerce_data,
    coerce_value,
    is_boolean,
    is_format_markdown,
    is_integer,
    is_number,
    load_schema,
    validate_header,
    validate_questions_list,
    validate_source_questions,
)


def _resolve_base_dir(base_dir: str | Path | None, filename: str | Path) -> Path:
    """Resolve the anchor directory used for relative ``_include`` and figure paths."""
    if base_dir is not None:
        return Path(base_dir).resolve()
    if filename and str(filename) not in ("<string>", "<stdin>"):
        return Path(filename).parent.resolve()
    return Path.cwd().resolve()


def _extract_root_figure_dirs(header_data: Any) -> list[str]:
    """Pop and normalize ``_figures_path`` from the root header mapping."""
    if not isinstance(header_data, dict):
        return []
    raw_dirs = header_data.pop("_figures_path", [])
    if isinstance(raw_dirs, str):
        return [raw_dirs]
    if isinstance(raw_dirs, list):
        return [str(d) for d in raw_dirs]
    return []


def _validate_unique_question_ids(
    questions_data: list[Any], filename: str | Path
) -> None:
    """Ensure no two questions in the resolved question list share the same ``id``."""
    seen_ids: set[str] = set()
    for q in questions_data:
        if isinstance(q, dict) and q.get("id"):
            qid = str(q["id"]).strip()
            if qid in seen_ids:
                raise QuizMLYamlSyntaxError(
                    f"Duplicate question id '{qid}' in {filename}"
                )
            seen_ids.add(qid)


def loads(
    quizmlyaml_txt: str,
    validate: bool = True,
    schema: dict[str, Any] | None = None,
    filename: str | Path = "<string>",
    base_dir: str | Path | None = None,
) -> QuizDocument:
    """Parse a QuizML YAML string into a validated, coerced ``QuizDocument``.

    Pipeline stages:
    1. Parse multi-document YAML text into ``(header_data, questions_data)``
       using ``StringConstructor`` (preserving line/column metadata).
    2. Validate the header against ``schema['definitions']['header']``.
    3. Recursively expand ``_include`` directives and check for duplicate ``id``s.
    4. Validate the flattened question list against the root JSON Schema
       (which also populates default values such as ``marks``).
    5. Convert ``ruamel.yaml`` nodes to plain Python types and coerce scalar
       strings into ``int``, ``float``, ``bool``, and ``MarkdownString``.
    """
    resolved_base_dir = _resolve_base_dir(base_dir, filename)
    header_data, questions_data = parse_quiz_yaml_text(
        quizmlyaml_txt, source_label=filename
    )

    if not header_data and not questions_data:
        return QuizDocument(
            {
                "header": {},
                "questions": [],
                "paths": {"input_dir": str(resolved_base_dir), "figure_dirs": []},
            },
            schema=schema,
        )

    if validate:
        validate_header(header_data, schema, quizmlyaml_txt, str(filename))

    root_figure_dirs = _extract_root_figure_dirs(header_data)
    accumulated_figure_dirs: list[str] = []

    if questions_data and isinstance(questions_data, list):
        questions_data = resolve_includes(
            questions_data,
            base_dir=resolved_base_dir,
            root_dir=resolved_base_dir,
            accumulated_figure_dirs=accumulated_figure_dirs,
            schema=schema if validate else None,
            source_text=quizmlyaml_txt,
            source_path=str(filename),
        )
        _validate_unique_question_ids(questions_data, filename)

    figure_dirs = list(dict.fromkeys(root_figure_dirs + accumulated_figure_dirs))

    if validate and schema and questions_data:
        validate_questions_list(
            questions_data,
            schema,
            source_text=quizmlyaml_txt,
            filename=str(filename),
        )

    doc: dict[str, Any] = {
        "header": to_plain_python(header_data) if header_data else {},
        "questions": to_plain_python(questions_data) if questions_data else [],
        "paths": {"input_dir": str(resolved_base_dir), "figure_dirs": figure_dirs},
    }
    doc = coerce_data(doc, schema)
    return QuizDocument(doc, schema=schema)


def load(
    quizmlyaml_path: str | Path,
    validate: bool = True,
    schema_path: str | Path | None = None,
    schema_extensions: dict[str, Any] | None = None,
) -> QuizDocument:
    """Load a QuizML YAML file (or ``-`` for stdin) into a ``QuizDocument``."""
    if str(quizmlyaml_path) == "-":
        quizmlyaml_txt = sys.stdin.read()
        base_dir = Path.cwd().resolve()
        filename = "<stdin>"
        stem = "stdin"
    else:
        path_obj = Path(quizmlyaml_path)
        try:
            quizmlyaml_txt = path_obj.read_text(encoding="utf-8")
        except FileNotFoundError as err:
            raise QuizMLError(f"Yaml file not found: {quizmlyaml_path}") from err
        except OSError as err:
            raise QuizMLError(
                f"Could not read YAML file {quizmlyaml_path}: {err}"
            ) from err
        base_dir = path_obj.parent.resolve()
        filename = str(quizmlyaml_path)
        stem = path_obj.stem

    schema = (
        load_schema(schema_path=schema_path, schema_extensions=schema_extensions)
        if validate
        else None
    )

    doc = loads(
        quizmlyaml_txt,
        validate=validate,
        schema=schema,
        filename=filename,
        base_dir=base_dir,
    )
    doc["header"]["inputbasename"] = stem
    return doc


__all__ = [
    "CustomTypeChecker",
    "DefaultFillingValidator",
    "GrepMatch",
    "MarkdownString",
    "QuizDocument",
    "ScalarValidator",
    "StringConstructor",
    "apply_schema_extensions",
    "clean_all_q_comments",
    "coerce_data",
    "coerce_value",
    "compare_quiz_files",
    "count_included_questions",
    "default_version_constraint",
    "expand_roundtrip_includes",
    "extract_figure_paths",
    "find_quiz_files_for_grep",
    "format_matching_questions",
    "format_yaml_text",
    "generate_question_id",
    "get_choices_content",
    "grep_questions",
    "is_blank_comment",
    "is_boolean",
    "is_format_markdown",
    "is_integer",
    "is_number",
    "is_q_comment",
    "is_question_match",
    "load",
    "load_schema",
    "loads",
    "normalize_select_list",
    "normalize_text",
    "parse_quiz_yaml_text",
    "parse_roundtrip_yaml_text",
    "parse_version_tuple",
    "peek_yaml_header",
    "pin_yaml_text",
    "questions_are_similar",
    "read_question_file",
    "read_roundtrip_yaml",
    "resolve_include_path",
    "resolve_includes",
    "resolve_select_indices",
    "select_questions",
    "to_plain_python",
    "validate_header",
    "validate_questions_list",
    "validate_source_questions",
    "wrap_markdown",
    "wrap_text_fields",
]
