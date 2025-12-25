from rich.console import Console
from rich.markdown import Markdown, TableElement
from rich.table import Table
from rich import box

class CustomTableElement(TableElement):
    def __rich_console__(self, console, options):
        # Default padding is (0, 1). Let's try (0, 3) to see the difference.
        table = Table(box=box.SIMPLE_HEAVY, padding=(0, 3)) 

        if self.header is not None and self.header.row is not None:
            for column in self.header.row.cells:
                table.add_column(column.content)

        if self.body is not None:
            for row in self.body.rows:
                row_content = [element.content for element in row.cells]
                table.add_row(*row_content)

        yield table

# Monkey-patch the table_open element
Markdown.elements["table_open"] = CustomTableElement

txt = """
| Q | Type | Marks | # | Exp | Question Statement |
|---:|:---:|---:|---:|---:|---:|
| 1 | mc | 5.0 | 4 | 1.2 | If vector ${\\bf w}$ is of dimension $3 \times 1$ and matrix ${\\bf A}$ of… |
| 2 | tf | 5.0 | 2 | 2.5 | From this graph of the loss during training, we can say that there is underfitting.… |
"""

console = Console()
md = Markdown(txt)
console.print(md)

