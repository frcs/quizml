import io

from jinja2 import TemplateError

from .exceptions import QuizMLConfigError, TemplateRenderError


def render(context, template_filename):
    """
    Renders a docx template using docxtpl.
    Returns bytes of the rendered document.
    """
    try:
        from docxtpl import DocxTemplate
    except ImportError as err:
        raise QuizMLConfigError(
            "The 'docxtpl' package is required for DOCX templates."
        ) from err

    try:
        doc = DocxTemplate(template_filename)

        # DocxTemplate.render takes a context dict just like jinja2
        doc.render(context)

        # Save to a bytes buffer
        file_stream = io.BytesIO()
        doc.save(file_stream)
    except TemplateError as err:
        raise TemplateRenderError(
            f"DOCX template '{template_filename}' failed: {err}"
        ) from err
    except OSError as err:
        detail = err.strerror or str(err)
        raise TemplateRenderError(
            f"Could not read DOCX template '{template_filename}': {detail}"
        ) from err
    file_stream.seek(0)

    return file_stream.read()
