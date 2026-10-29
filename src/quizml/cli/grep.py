"""CLI adapter for searching and grepping questions across QuizML YAML files."""

import sys
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table, box

from quizml.cli.errorhandler import err_console
from quizml.yaml.grep import format_matching_questions, grep_questions


def run_grep(args):
    """Execute question search across files or standard input."""
    base_dir = Path.cwd().resolve()
    pattern = getattr(args, "pattern", "") or ""
    paths = getattr(args, "paths", None) or []

    regexp_arg = getattr(args, "regexp_pattern", None)
    if regexp_arg is not None:
        pattern = regexp_arg
        pos_paths = []
        if getattr(args, "pattern", ""):
            pos_paths.append(args.pattern)
        if getattr(args, "paths", None):
            pos_paths.extend(args.paths)
        paths = pos_paths
    elif (
        (getattr(args, "type", None) or getattr(args, "field", None))
        and not paths
        and pattern
    ):
        p = Path(pattern)
        if p.exists():
            paths = [pattern]
            pattern = ""

    if not paths:
        paths = ["."]

    output_path = getattr(args, "output", None)

    matches = grep_questions(
        pattern,
        paths=paths,
        ignore_case=getattr(args, "ignore_case", False),
        fixed_strings=getattr(args, "fixed_strings", False),
        invert_match=getattr(args, "invert_match", False),
        field=getattr(args, "field", None),
        qtype=getattr(args, "type", None),
        unique=getattr(args, "unique", False),
        recursive=getattr(args, "recursive", True),
        base_dir=base_dir,
    )

    if not matches:
        if not getattr(args, "quiet", False):
            display_pattern = (
                pattern
                if pattern
                else (f"type={args.type}" if getattr(args, "type", None) else "")
            )
            err_console.print(f"no questions found matching '{display_pattern}'")
        return False

    # Mode 1: --files-with-matches (-l)
    if getattr(args, "files_with_matches", False):
        seen_files = []
        for m in matches:
            p_str = str(m.file_path)
            if p_str not in seen_files:
                seen_files.append(p_str)
        for f in seen_files:
            sys.stdout.write(f"{f}\n")
        sys.stdout.flush()
        return True

    # Mode 2: --count (-c)
    if getattr(args, "count", False):
        counts = Counter(str(m.file_path) for m in matches)
        if len(counts) > 1:
            for f_str, count in sorted(counts.items()):
                sys.stdout.write(f"{f_str}: {count}\n")
        else:
            sys.stdout.write(f"{len(matches)}\n")
        sys.stdout.flush()
        return True

    # Mode 3: --table / --summary
    if getattr(args, "summary", False):
        return print_summary_table(matches, quiet=getattr(args, "quiet", False))

    # Mode 4: Default YAML output
    yaml_text = format_matching_questions(
        matches,
        wrap_width=getattr(args, "wrap", None),
        show_provenance=not getattr(args, "no_provenance", False),
    )

    if output_path:
        out_p = Path(output_path).expanduser().resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(yaml_text, encoding="utf-8")
        if not getattr(args, "quiet", False):
            err_console.print(
                f"Wrote {len(matches)} matching question(s) to {output_path}"
            )
    else:
        if sys.stdout.isatty():
            console = Console()
            console.print(
                Syntax(
                    yaml_text.rstrip(),
                    "yaml",
                    theme="monokai",
                    background_color="default",
                )
            )
        else:
            sys.stdout.write(yaml_text)
            sys.stdout.flush()

    if not getattr(args, "quiet", False) and not output_path and sys.stderr.isatty():
        n_files = len({str(m.file_path) for m in matches})
        file_word = "file" if n_files == 1 else "files"
        q_word = "question" if len(matches) == 1 else "questions"
        err_console.print(
            f"[dim]Found {len(matches)} {q_word} across {n_files} {file_word}.[/dim]"
        )

    return True


def print_summary_table(matches, quiet=False):
    """Render a tabular overview of matching questions."""
    if not quiet and not sys.stdout.isatty():
        # Non-TTY piped output: emit tab-separated records
        for m in matches:
            excerpt_one_line = " ".join(m.statement_excerpt.splitlines())
            marks_str = str(m.marks) if m.marks != "" else "-"
            sys.stdout.write(
                f"{m.file_path}\tQ{m.question_index}\t{m.question_type}\t{marks_str}\t{excerpt_one_line}\n"
            )
        sys.stdout.flush()
        return True

    console = Console()
    table = Table(box=box.SIMPLE, collapse_padding=True, show_footer=False)
    table.add_column("File", justify="left")
    table.add_column("Q", justify="right", no_wrap=True)
    table.add_column("Type", justify="center", no_wrap=True)
    table.add_column("Marks", justify="right", no_wrap=True)
    table.add_column("Question Statement", justify="left")

    for m in matches:
        marks_str = str(m.marks) if m.marks != "" else "-"
        table.add_row(
            str(m.file_path),
            f"{m.question_index}",
            m.question_type,
            marks_str,
            m.statement_excerpt,
        )

    console.print(table)
    return True
