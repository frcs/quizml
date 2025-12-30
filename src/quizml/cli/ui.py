import os
from rich import print
from rich.table import Table
from rich.table import box
from rich.panel import Panel
from rich.padding import Padding
from rich.markdown import Markdown, TableElement
from rich import box

from quizml.cli.errorhandler import print_error
import quizml.cli.filelocator as filelocator
from quizml import renderer
from quizml.exceptions import QuizMLConfigError, Jinja2SyntaxError
from quizml.cli.config import get_config

class CustomTableElement(TableElement):
    def __rich_console__(self, console, options):
        for table in super().__rich_console__(console, options):
            # Check if the table has visible headers
            has_headers = any(col.header.plain.strip() for col in table.columns)
            
            if has_headers:
                # Main Question Table
                table.show_header = True
                table.box = box.SIMPLE_HEAVY # Adds the rule and header structure
                table.padding = (0, 0, 0, 1) # User preferred padding
                table.show_edge = False # Hide bottom line
            else:
                # Summary Table (frameless alignment)
                table.show_header = False
                table.box = None
                table.padding = (0, 0, 0, 1) # Align left, spacing between cols
                
            yield table

Markdown.elements["table_open"] = CustomTableElement

def add_hyperlinks(descr_str, filename):
    path = os.path.abspath(f"./{filename}")
    uri = f"[link=file://{path}]{filename}[/link]"
    return  descr_str.replace(filename, uri)

def print_target_list(args):
    try:
        config = get_config(args)
    except QuizMLConfigError as err:
        print_error(str(err), title="QuizML Config Error")
        return

    table = Table(box=box.SIMPLE,
                  collapse_padding=True,
                  show_footer=False,
                  show_header=False)
    
    table.add_column("Name", no_wrap=True, justify="left")
    table.add_column("Descr", no_wrap=True, justify="left")
   
    for t in config['targets']:
        table.add_row(t['name'], t['descr'])
       
    print(table)

def print_stats_table(quiz, config):
    """
    prints a table with information about each question, using a user-defined jinja template.
    """
    
    try:
        template_name = config.get('stats_template', 'stats.jinja')
        template_path = filelocator.locate.path(template_name)
    except FileNotFoundError:
        print_error(f"Stats template '{template_name}' not found", title="Error")
        return

    try:
        #        rendered = renderer.render_template({'quiz': quiz}, template_path)
        rendered = renderer.render_template(quiz, template_path)

        # Padding arguments: (top, right, bottom, left)
        text_to_print = Padding(Markdown(rendered), (0, 0, 1, 4))
        print(text_to_print)
    except Jinja2SyntaxError as err:
        print_error(str(err), title="Jinja Template Error")

def print_table_ouputs(targets_output):
    # print to terminal a table of all targets outputs.
    table = Table(box=box.SIMPLE,
                  collapse_padding=True,
                  show_footer=False,
                  show_header=False)
    
    table.add_column("Descr", no_wrap=True, justify="left")
    table.add_column("Cmd", no_wrap=True, justify="left")
    table.add_column("Status", no_wrap=True, justify="left")

    for row in targets_output:
        if row[2]=="[FAIL]":
            table.add_row(*row, style="red")
        elif row[2]=="":
            table.add_row(*row)
       
    print(Panel(table,
                title="Target Ouputs",
                border_style="magenta"))
   
def print_quiet_ouputs(targets_quiet_output):

    for row in targets_quiet_output:
        if row[1]=="[FAIL]":
            print("[bold red]x " + row[0] + "[/bold red]")
        elif row[1]=="":
            print("[bold green]o[/bold green] " + row[0])
