"""CLI adapter for comparing questions across quiz files."""

from rich.console import Console
from rich.table import Table, box

from quizml.cli.errorhandler import err_console
from quizml.yaml.diff import (
    compare_quiz_files,
    get_choices_content,
    normalize_text,
    questions_are_similar,
)


def diff(args):
    """Find if questions can be found in other exams."""
    files = [args.yaml_filename]
    for item in args.otherfiles:
        if item not in files:
            files.append(item)

    qstats = compare_quiz_files(files)
    has_dups = print_dups_table(qstats, quiet=getattr(args, "quiet", False))
    if getattr(args, "check", False) and has_dups:
        return False
    return True


def print_dups_table(qstats, quiet=False):
    """Print a table with information about duplicate questions."""
    import sys

    has_dups = any("dups" in q for q in qstats)

    if has_dups and not quiet and not sys.stdout.isatty():
        for i, q in enumerate(qstats):
            if "dups" in q:
                excerpt_one_line = " ".join(str(q["excerpt"]).splitlines())
                dups_str = ", ".join(q.get("dups", []))
                sys.stdout.write(
                    f"{i + 1}\t{q.get('type', 'unknown')}\t{excerpt_one_line}\t{dups_str}\n"
                )
        sys.stdout.flush()
        return has_dups

    console = Console()

    table = Table(box=box.SIMPLE, collapse_padding=True, show_footer=True)

    table.add_column("Q", no_wrap=True, justify="right")
    table.add_column("Type", no_wrap=True, justify="center")
    table.add_column("Question Statement", no_wrap=False, justify="left")
    table.add_column("Dups", no_wrap=False, justify="left")

    for i, q in enumerate(qstats):
        if "dups" in q:
            table.add_row(
                f"{i + 1}",
                q.get("type", "unknown"),
                q["excerpt"],
                ", ".join(q.get("dups", "")),
            )

    if has_dups:
        if not quiet:
            console.print(table)
    elif not quiet:
        err_console.print("no dups found")

    return has_dups


__all__ = [
    "compare_quiz_files",
    "diff",
    "get_choices_content",
    "normalize_text",
    "print_dups_table",
    "questions_are_similar",
]
