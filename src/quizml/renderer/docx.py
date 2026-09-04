"""Word (.docx) template rendering using docxtpl."""

import io
from pathlib import Path

from quizml.exceptions import QuizMLError


def render_docx(context: dict, template_filename: str | Path) -> bytes:
    """Renders a Word .docx template using docxtpl.

    Returns the bytes of the rendered document.
    """
    try:
        from docxtpl import DocxTemplate
    except ImportError as err:
        raise QuizMLError(
            "The 'docxtpl' package is required for rendering .docx templates. "
            "Please install it with: pip install docxtpl"
        ) from err

    doc = DocxTemplate(str(template_filename))
    doc.render(context)

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream.read()
