import os

from rich import print
from rich.markdown import Markdown, TableElement
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table, box

from quizml import renderer
from quizml.cli.config import get_config
from quizml.cli.errorhandler import err_console
from quizml.cli.filelocator import FileLocator
from quizml.exceptions import QuizMLConfigError


class CustomTableElement(TableElement):
    def __rich_console__(self, console, options):
        for table in super().__rich_console__(console, options):
            # Check if the table has visible headers
            has_headers = any(col.header.plain.strip() for col in table.columns)

            if has_headers:
                # Main Question Table
                table.show_header = True
                table.box = box.SIMPLE_HEAVY  # Adds the rule and header structure
                table.padding = (0, 0, 0, 1)  # User preferred padding
                table.show_edge = False  # Hide bottom line
            else:
                # Summary Table (frameless alignment)
                table.show_header = False
                table.box = None
                table.padding = (0, 0, 0, 1)  # Align left, spacing between cols

            yield table


class QuizMLMarkdown(Markdown):
    elements = {**Markdown.elements, "table_open": CustomTableElement}


def add_hyperlinks(descr_str, filename):
    if not filename:
        return descr_str or ""
    path = os.path.abspath(f"./{filename}")
    uri = f"[link=file://{path}]{filename}[/link]"
    return (descr_str or filename).replace(filename, uri)


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

    rendered = renderer.render_template(quiz, template_path, locator.dirlist)

    # Padding arguments: (top, right, bottom, left)
    text_to_print = Padding(QuizMLMarkdown(rendered), (0, 0, 1, 4))
    err_console.print(text_to_print)


def print_table_ouputs(targets_output):
    # print to terminal a table of all targets outputs.
    table = Table(
        box=box.SIMPLE, collapse_padding=True, show_footer=False, show_header=False
    )

    table.add_column("Descr", no_wrap=True, justify="left")
    table.add_column("Cmd", no_wrap=True, justify="left")
    table.add_column("Status", no_wrap=True, justify="left")

    for row in targets_output:
        if row[2] == "[FAIL]":
            table.add_row(*row, style="red")
        elif row[2] == "":
            table.add_row(*row)

    err_console.print(Panel(table, title="Target Ouputs", border_style="magenta"))


def print_quiet_ouputs(targets_quiet_output):
    for row in targets_quiet_output:
        if row[1] == "[FAIL]":
            err_console.print("[bold red]x " + row[0] + "[/bold red]")
        elif row[1] == "":
            err_console.print("[bold green]o[/bold green] " + row[0])
