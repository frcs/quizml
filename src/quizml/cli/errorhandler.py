from rich.console import Console
from rich.panel import Panel

err_console = Console(stderr=True)


def print_error(message, title="Error"):
    """Prints an error message in a rich panel to stderr."""
    err_console.print(Panel(str(message), title=title, border_style="red"))
