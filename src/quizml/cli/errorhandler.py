import sys

from rich.console import Console

err_console = Console(stderr=True)


def print_error(message, title="Error"):
    """Prints an error message to stderr in compiler format."""
    prefix_word = title.lower()
    if err_console.is_terminal:
        color = "yellow" if prefix_word == "warning" else "red"
        err_console.print(f"[bold {color}]{prefix_word}:[/bold {color}] {message}")
    else:
        sys.stderr.write(f"{prefix_word}: {message}\n")
        sys.stderr.flush()
