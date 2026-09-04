"""CLI command handler for quiz diffing and duplicate question detection."""

import os

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table, box

from quizml.exceptions import QuizMLYamlSyntaxError
from quizml.quizmlyaml import load
from quizml.tools.diff import (
    compare_quiz_files,
    get_choices_content,
    normalize_text,
    questions_are_similar,
)


def print_dups_table(qstats):
    """Prints a table with information about duplicated questions."""
    has_dups = False
    console = Console()
    table = Table(box=box.SIMPLE, collapse_padding=True, show_footer=True)

    table.add_column("Q", no_wrap=True, justify="right")
    table.add_column("Type", no_wrap=True, justify="center")
    table.add_column("Question Statement", no_wrap=False, justify="left")
    table.add_column("Dups", no_wrap=False, justify="left")

    for q in qstats:
        if q.get("dups"):
            has_dups = True
            table.add_row(
                str(q["index"]),
                q["type"],
                q["excerpt"],
                ", ".join(q.get("dups", [])),
            )

    if has_dups:
        console.print(table)
    else:
        print("no dups found")


def diff(args):
    """CLI runner for comparing questions across multiple quiz YAML files."""
    files = [args.yaml_filename]
    for item in args.otherfiles:
        if item not in files:
            files.append(item)

    for f in files:
        if not os.path.exists(f):
            print(Panel(f"File {f} not found", title="Error", border_style="red"))
            return
        try:
            load(f, validate=False)
        except QuizMLYamlSyntaxError as err:
            print(
                Panel(
                    str(err),
                    title=f"QuizMLYaml Syntax Error in file {f}",
                    border_style="red",
                )
            )
            return

    qstats = compare_quiz_files(files[0], files[1:])
    print_dups_table(qstats)


__all__ = [
    "diff",
    "print_dups_table",
    "normalize_text",
    "get_choices_content",
    "questions_are_similar",
]
