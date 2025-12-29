import io
import sys
from rich import print

def render(context, template_filename):
    """
    Renders a docx template using docxtpl.
    Returns bytes of the rendered document.
    """
    try:
        from docxtpl import DocxTemplate
    except ImportError:
        print("[bold red]Error:[/bold red] The 'docxtpl' package is required for docx templates.")
        print("Please install it with: [green]pip install docxtpl[/green]")
        sys.exit(1)

    doc = DocxTemplate(template_filename)
    
    # DocxTemplate.render takes a context dict just like jinja2
    doc.render(context)
    
    # Save to a bytes buffer
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream.read()
