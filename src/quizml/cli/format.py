"""CLI command handler for formatting QuizML YAML files."""

from pathlib import Path

from rich import print

from quizml.exceptions import QuizMLError
from quizml.tools.format import (
    clean_all_q_comments,
    format_file,
    format_yaml_string,
    is_blank_comment,
    is_q_comment,
    should_remove_comment,
    wrap_text_fields,
)


def format_yaml(args):
    yaml_path = Path(args.yaml_filename)
    if not yaml_path.exists():
        raise QuizMLError(f"File not found: {yaml_path}")

    has_changed, _ = format_file(yaml_path, in_place=True)
    if has_changed:
        print(f"Formatted and renumbered {yaml_path}")
    else:
        print(f"No changes made to {yaml_path}")


__all__ = [
    "format_yaml",
    "format_file",
    "format_yaml_string",
    "clean_all_q_comments",
    "wrap_text_fields",
    "is_q_comment",
    "is_blank_comment",
    "should_remove_comment",
]
