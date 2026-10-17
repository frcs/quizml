import io
import math

import jinja2
from jinja2 import TemplateError

from .exceptions import QuizMLConfigError, TemplateRenderError


def render(context, template_filename, jinja_filters=None):
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
        jinja_env = jinja2.Environment(
            undefined=jinja2.StrictUndefined,
            extensions=["jinja2.ext.do"],
        )
        jinja_env.globals["math"] = math
        if jinja_filters:
            from .renderer import _load_filter_callable

            if not isinstance(jinja_filters, dict):
                raise QuizMLConfigError("The 'jinja_filters' setting must be a mapping.")
            for name, spec in jinja_filters.items():
                jinja_env.filters[name] = _load_filter_callable(spec)

        # DocxTemplate.render takes a context dict and optional jinja_env
        try:
            doc.render(context, jinja_env=jinja_env)
        except TypeError:
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
