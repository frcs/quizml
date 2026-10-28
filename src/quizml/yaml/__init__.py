"""Independent QuizML YAML and Question-Bank Module.

Provides multi-document YAML parsing, recursive ``_include`` expansion,
``select`` and deterministic ``count``/``seed`` sampling, JSON Schema validation
and type coercion, formatting, pinning, and diffing.
"""

import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from quizml.exceptions import QuizMLYamlSyntaxError
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
    should_remove_comment,
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


def loads(
    quizmlyaml_txt,
    validate=True,
    schema=None,
    filename="<string>",
    base_dir=None,
) -> QuizDocument:
    """Parse a QuizML YAML string into a validated, coerced ``QuizDocument``."""
    yaml = YAML()
    yaml.Constructor = StringConstructor
    try:
        raw_docs = list(yaml.load_all(quizmlyaml_txt))
    except YAMLError as err:
        line = -1
        if hasattr(err, "problem_mark"):
            line = err.problem_mark.line
        raise QuizMLYamlSyntaxError(
            f"YAML parsing error in {filename} near line {line}:\n{err}"
        ) from err

    yamldocs = [
        d
        for d in raw_docs
        if d is not None and not (isinstance(d, str) and not doc_strip(d))
    ]

    if base_dir is None:
        if filename and filename != "<string>":
            base_dir = Path(filename).parent.resolve()
        else:
            base_dir = Path.cwd()
    else:
        base_dir = Path(base_dir).resolve()

    if len(yamldocs) > 2:
        raise QuizMLYamlSyntaxError(
            "YAML file cannot have more than 2 documents: "
            "one for the header and one for the questions."
        )

    if not yamldocs:
        return QuizDocument(
            {
                "header": {},
                "questions": [],
                "paths": {"input_dir": str(base_dir), "figure_dirs": []},
            },
            schema=schema,
        )

    if len(yamldocs) == 1:
        if isinstance(yamldocs[0], list):
            header_data, questions_data = {}, yamldocs[0]
        else:
            header_data, questions_data = yamldocs[0], []
    else:
        header_data, questions_data = yamldocs[0], yamldocs[1]

    if validate:
        validate_header(header_data, schema, quizmlyaml_txt, filename)

    root_figure_dirs = []
    if isinstance(header_data, dict):
        root_figure_dirs = header_data.pop("_figures_path", [])
    if isinstance(root_figure_dirs, str):
        root_figure_dirs = [root_figure_dirs]
    elif not isinstance(root_figure_dirs, list):
        root_figure_dirs = []

    accumulated_figure_dirs = []

    if questions_data and isinstance(questions_data, list):
        questions_data = resolve_includes(
            questions_data,
            base_dir=base_dir,
            root_dir=base_dir,
            accumulated_figure_dirs=accumulated_figure_dirs,
            schema=schema if validate else None,
            source_text=quizmlyaml_txt,
            source_path=filename,
        )
        seen_ids = set()
        for q in questions_data:
            if isinstance(q, dict) and q.get("id"):
                qid = str(q["id"]).strip()
                if qid in seen_ids:
                    raise QuizMLYamlSyntaxError(
                        f"Duplicate question id '{qid}' in {filename}"
                    )
                seen_ids.add(qid)
    figure_dirs = list(dict.fromkeys(root_figure_dirs + accumulated_figure_dirs))

    if validate and schema and questions_data:
        validate_questions_list(
            questions_data, schema, source_text=quizmlyaml_txt, filename=filename
        )

    doc = {
        "header": to_plain_python(header_data) if header_data else {},
        "questions": to_plain_python(questions_data) if questions_data else [],
        "paths": {"input_dir": str(base_dir), "figure_dirs": figure_dirs},
    }
    doc = coerce_data(doc, schema)
    return QuizDocument(doc, schema=schema)


def doc_strip(val: str) -> str:
    return val.strip()


def load(
    quizmlyaml_path, validate=True, schema_path=None, schema_extensions=None
) -> QuizDocument:
    """Load a QuizML YAML file (or ``-`` for stdin) into a ``QuizDocument``."""
    if quizmlyaml_path == "-":
        quizmlyaml_txt = sys.stdin.read()
        base_dir = Path.cwd().resolve()
        filename = "<stdin>"
        stem = "stdin"
    else:
        try:
            quizmlyaml_txt = Path(quizmlyaml_path).read_text(encoding="utf-8")
        except FileNotFoundError as err:
            raise QuizMLYamlSyntaxError(
                f"Yaml file not found: {quizmlyaml_path}"
            ) from err
        base_dir = Path(quizmlyaml_path).parent.resolve()
        filename = str(quizmlyaml_path)
        stem = Path(quizmlyaml_path).stem

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
    "GrepMatch",
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
    "should_remove_comment",
    "to_plain_python",
    "validate_header",
    "validate_questions_list",
    "validate_source_questions",
    "wrap_markdown",
    "wrap_text_fields",
]
