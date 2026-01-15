
from rich import print
from rich.panel import Panel


def print_error(message, title="Error"):
    """Prints an error message in a rich panel."""
    print(Panel(str(message), title=title, border_style="red"))
