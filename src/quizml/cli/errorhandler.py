import os
import textwrap

from rich.panel import Panel
from rich import print

from quizml.utils import text_wrap, msg_context

def print_error(message, title="Error"):
    """Prints an error message in a rich panel."""
    print(Panel(str(message), title=title, border_style="red"))
