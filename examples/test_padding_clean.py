from rich.console import Console
from rich.markdown import Markdown, TableElement

class CustomTableElement(TableElement):
    def __rich_console__(self, console, options):
        for table in super().__rich_console__(console, options):
            table.padding = (0, 3) # Set custom padding here
            yield table

# Register the custom element
Markdown.elements["table_open"] = CustomTableElement

txt = """
| Q | Type | Marks | # | Exp | Question Statement |
|---:|:---:|---:|---:|---:|---|
| 1 | mc | 5.0 | 4 | 1.2 | If vector ${\\bf w}$ is of dimension $3 \times 1$ and matrix ${\\bf A}$ of… |
| 2 | tf | 5.0 | 2 | 2.5 | From this graph of the loss during training, we can say that there is underfitting.… |
"""

console = Console()
md = Markdown(txt)
console.print(md)
