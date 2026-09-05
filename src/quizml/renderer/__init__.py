"""QuizML Template Rendering module.

Supports Jinja2 text templates (LaTeX, Blackboard CSV, HTML) with custom delimiters
as well as Microsoft Word documents via docxtpl.
"""

from pathlib import Path

from quizml.renderer.docx import render_docx
from quizml.renderer.jinja import get_jinja_env, render_template


def render(
    doc: dict, template_path: str | Path, extra_context: dict | None = None
) -> str | bytes:
    """Renders a QuizML document dictionary into a target output string or bytes.

    :param doc: The transcoded or plain QuizML document (must contain 'header' and 'questions').
    :param template_path: Path to the Jinja2 (.j2) or Word (.docx) template.
    :param extra_context: Optional additional key-value pairs to pass into the template.
    :return: Rendered text (str) or binary document (bytes for docx).
    """
    context = {
        "header": doc.get("header", {}),
        "questions": doc.get("questions", []),
    }
    if extra_context:
        context.update(extra_context)

    template_str = str(template_path)
    if not Path(template_str).exists():
        from quizml.filelocator import locate

        try:
            template_str = locate.path(template_str)
        except FileNotFoundError:
            pass

    if template_str.endswith(".docx"):
        return render_docx(context, template_str)

    p = Path(template_str)
    if p.is_dir() or "qti12" in p.name:
        from quizml.renderer.qti import render_qti

        return render_qti(context, p)

    return render_template(context, template_str)


__all__ = [
    "render",
    "render_template",
    "render_docx",
    "render_qti",
    "get_jinja_env",
]
