from rich.console import Console
from rich.markdown import Markdown, TableElement

class InspectTableElement(TableElement):
    def __rich_console__(self, console, options):
        for table in super().__rich_console__(console, options):
            headers = [c.header for c in table.columns]
            print(f"Table headers: {headers}")
            yield table

Markdown.elements["table_open"] = InspectTableElement

txt = """
| Q | Type | Marks | # | Exp | Question Statement |
|---:|:---:|---:|---:|---:|---|
| 1 | mc | 5.0 | 4 | 1.2 | ... |

| | |
|---|---|
| Total Marks | 100 |
"""

console = Console()
md = Markdown(txt)
console.print(md)
