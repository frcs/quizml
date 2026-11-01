import os
import sys
from typing import ClassVar

from rich import print
from rich.markdown import Markdown, TableElement
from rich.table import Table, box

from quizml import rendering
from quizml.cli.config import get_config
from quizml.cli.errorhandler import err_console
from quizml.exceptions import QuizMLConfigError
from quizml.paths import FileLocator


class CustomTableElement(TableElement):
    def __rich_console__(self, console, options):
        for table in super().__rich_console__(console, options):
            # Check if the table has visible headers
            has_headers = any(col.header.plain.strip() for col in table.columns)

            if has_headers:
                # Main Question Table
                table.show_header = True
                table.box = box.SIMPLE  # Clean thin rule under header
                table.padding = (0, 0, 0, 1)  # Space between columns
                table.show_edge = False  # Hide outer border
                for col in table.columns:
                    col.header_style = "dim"
            else:
                # Summary Table (frameless alignment)
                table.show_header = False
                table.box = None
                table.padding = (0, 0, 0, 1)  # Align left, spacing between cols

            yield table


class QuizMLMarkdown(Markdown):
    elements: ClassVar[dict] = {**Markdown.elements, "table_open": CustomTableElement}


def add_hyperlinks(descr_str, filename):
    """Wrap file references in terminal hyperlink tags pointing to file:// URLs."""
    if not filename or filename == "-":
        return descr_str or ""
    if descr_str and "[link=" in descr_str:
        return descr_str

    abs_path = os.path.abspath(filename)
    uri = f"file://{abs_path}"
    basename = os.path.basename(abs_path)
    text = descr_str if (descr_str is not None and descr_str != "") else basename

    # When text is the raw full path (e.g. print_quiet_outputs)
    if text in (abs_path, filename):
        try:
            rel = os.path.relpath(abs_path)
            display = rel if not rel.startswith("..") else basename
        except ValueError:
            display = basename
        return f"[link={uri}]{display}[/link]"

    # If the output basename appears in descr_str (e.g. "latexmk ... quiz1.tex" or "quiz1.html")
    if basename and basename in text:
        return text.replace(basename, f"[link={uri}]{basename}[/link]")

    # If the filename as provided appears in text
    if filename in text:
        return text.replace(filename, f"[link={uri}]{basename}[/link]")

    # Fallback: append clickable link
    return f"{text} [link={uri}]{basename}[/link]"


def print_target_list(args):
    import sys

    config = get_config(args)

    if not sys.stdout.isatty():
        for t in config.get("targets", []):
            name = t.get("name", "<unnamed>")
            descr = t.get("descr", name)
            sys.stdout.write(f"{name}\t{descr}\n")
        sys.stdout.flush()
        return True

    table = Table(
        box=box.SIMPLE, collapse_padding=True, show_footer=False, show_header=False
    )

    table.add_column("Name", no_wrap=True, justify="left")
    table.add_column("Descr", no_wrap=True, justify="left")

    for t in config.get("targets", []):
        name = t.get("name", "<unnamed>")
        descr = t.get("descr", name)
        table.add_row(str(name), str(descr))

    print(table)
    return True


def print_stats_table(quiz, config):
    """
    prints a table with information about each question, using a user-defined jinja template.
    """
    yaml_filename = config.get("yaml_filename")
    base_dir = (
        os.path.dirname(os.path.abspath(yaml_filename))
        if yaml_filename and yaml_filename != "-"
        else None
    )

    template_name = config.get("stats_template", "stats.txt.j2")
    try:
        locator = FileLocator(base_dir=base_dir, config_dir=config.get("_config_dir"))
        template_path = locator.path(template_name)
    except FileNotFoundError as err:
        raise QuizMLConfigError(f"Stats template '{template_name}' not found") from err

    rendered = rendering.render_template(quiz, template_path, locator.dirlist)
    err_console.print(QuizMLMarkdown(rendered))
    err_console.print()


def print_table_outputs(targets_output):
    """Print a clean status list of all target outputs to stderr."""
    if not targets_output:
        return

    rows = []
    for item in targets_output:
        if hasattr(item, "description") and hasattr(item, "status"):
            descr = item.description or item.name
            out = item.output_path or ""
            cmd = item.descr_cmd or out
            is_ok = item.status == "succeeded"
        else:
            descr = item[0] if len(item) > 0 else ""
            cmd = item[1] if len(item) > 1 else ""
            is_ok = (item[2] != "[FAIL]") if len(item) > 2 else True
            out = ""
        rows.append((descr, cmd, out, is_ok))

    if not err_console.is_terminal:
        for descr, cmd, _, is_ok in rows:
            status = "OK" if is_ok else "FAIL"
            sys.stderr.write(f"{status}\t{descr}\t{cmd}\n")
        sys.stderr.flush()
        return

    err_console.print("[bold]Targets:[/bold]")
    max_descr_len = max((len(descr) for descr, _, _, _ in rows), default=0)

    for descr, cmd, out, is_ok in rows:
        icon = "[bold green]✔[/bold green]" if is_ok else "[bold red]✖[/bold red]"
        cmd_display = add_hyperlinks(cmd, out) if out else cmd
        err_suffix = "" if is_ok else " [bold red](failed)[/bold red]"
        err_console.print(
            f"  {icon} [bold]{descr:<{max_descr_len}}[/bold]  {cmd_display}{err_suffix}"
        )


def print_quiet_outputs(targets_quiet_output):
    """Print quiet one-line statuses of target outputs to stderr."""
    rows = []
    for item in targets_quiet_output:
        if hasattr(item, "output_path") and hasattr(item, "status"):
            out = item.output_path or ""
            is_ok = item.status == "succeeded"
        else:
            out = item[0] if len(item) > 0 else ""
            is_ok = (item[1] != "[FAIL]") if len(item) > 1 else True
        rows.append((out, is_ok))

    if not err_console.is_terminal:
        for out, is_ok in rows:
            status = "OK" if is_ok else "FAIL"
            sys.stderr.write(f"{status}\t{out}\n")
        sys.stderr.flush()
        return

    for out, is_ok in rows:
        icon = "[bold green]✔[/bold green]" if is_ok else "[bold red]✖[/bold red]"
        out_display = add_hyperlinks(out, out)
        err_suffix = "" if is_ok else " [bold red](failed)[/bold red]"
        err_console.print(f"{icon} {out_display}{err_suffix}")
