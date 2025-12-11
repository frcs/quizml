import os
import textwrap

from rich.panel import Panel
from rich import print

def print_error(message, title="Error"):
    """Prints an error message in a rich panel."""
    print(Panel(str(message), title=title, border_style="red"))

def text_wrap(msg):
    try:
        w, _ = os.get_terminal_size(0)
    except OSError:
        w = 80  # Default width if terminal size can't be determined
    return textwrap.fill(msg, w - 5)

def msg_context_line(lines, lineo, charno=None, highlight=False):
    if (lineo < 1 or lineo > len(lines)):
        return ""
    if highlight:
        # Using simple formatting for now to avoid dependency on rich here
        # This can be enhanced later if needed.
        return f"❱ {lineo:>4} │  {lines[lineo-1]}\n"
    else:
        return f"  {lineo:>4} │ {lines[lineo-1]}\n"

def msg_context(lines, lineo, charno=None):
    msg = msg_context_line(lines, lineo - 1, charno, highlight=False)
    msg += msg_context_line(lines, lineo, charno, highlight=True)
    msg += msg_context_line(lines, lineo + 1, charno, highlight=False)
    return msg
