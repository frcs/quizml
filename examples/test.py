
from rich.console import Console
from rich.markdown import Markdown, TableElement


from rich import box

class CustomTableElement(TableElement):
    def __rich_console__(self, console, options):
        for table in super().__rich_console__(console, options):
            # Check if the table has visible headers
            has_headers = any(col.header.plain.strip() for col in table.columns)
            
            if has_headers:
                # Main Question Table
                table.show_header = True
                table.box = box.SIMPLE_HEAVY # Adds the rule and header structure
                table.padding = (0, 1, 0, 0) # User preferred padding
                table.show_edge = False # Hide bottom line
            else:
                # Summary Table (frameless alignment)
                table.show_header = False
                table.box = None
                table.padding = (0, 1, 0, 0) # Align left, spacing between cols
                
            yield table

Markdown.elements["table_open"] = CustomTableElement

txt = """
| Q | Type | Marks | # | Exp | Question Statement |
|---:|:---:|---:|---:|---:|---|
| 1 | mc | 5.0 | 4 | 1.2 | If vector ${\\bf w}$ is of dimension $3 \\times 1$ and matrix ${\\bf A}$ of… |
| 2 | tf | 5.0 | 2 | 2.5 | From this graph of the loss during training, we can say that there is underfitting.… |


total: 100 (with random exp. mark at 35)

"""

console = Console()
md = Markdown(txt)
console.print(md)


