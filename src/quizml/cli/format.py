"""CLI adapter for YAML formatting."""

import difflib
from pathlib import Path

from quizml.exceptions import QuizMLError
from quizml.yaml.format import (
    clean_all_q_comments,
    format_yaml_text,
    is_blank_comment,
    is_q_comment,
    wrap_markdown,
    wrap_text_fields,
)


def run_format(args):
    import sys

    from .errorhandler import err_console

    source_name = args.file
    if source_name == "-":
        original = sys.stdin.read()
        base_dir = Path.cwd()
        filename = "<stdin>"
    else:
        path = Path(source_name)
        if not path.is_file():
            raise QuizMLError(f"File not found: {path}")
        original = path.read_text(encoding="utf-8")
        base_dir = path.parent
        filename = str(path)

    formatted = format_yaml_text(
        original,
        base_dir=base_dir,
        filename=filename,
        wrap_width=args.wrap,
    )
    changed = formatted != original

    if args.check:
        return not changed
    if args.diff:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            formatted.splitlines(keepends=True),
            fromfile=filename,
            tofile=f"{filename} (formatted)",
        )
        sys.stdout.writelines(diff)
        return True
    if args.in_place:
        if source_name == "-":
            raise QuizMLError("--in-place requires a file path")
        if changed:
            Path(source_name).write_text(formatted, encoding="utf-8")
            err_console.print(f"Formatted and renumbered {source_name}")
        else:
            err_console.print(f"No changes needed in {source_name}")
        return True

    sys.stdout.write(formatted)
    return True


__all__ = [
    "clean_all_q_comments",
    "format_yaml_text",
    "is_blank_comment",
    "is_q_comment",
    "run_format",
    "wrap_markdown",
    "wrap_text_fields",
]
