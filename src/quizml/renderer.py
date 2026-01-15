import math
import pathlib

import jinja2

from quizml.exceptions import Jinja2SyntaxError
from quizml.utils import msg_context, text_wrap


def render_template(context, template_filename):
    if not template_filename:
        msg = "Template filename is missing, can't render jinja."
        raise Jinja2SyntaxError(msg)

    try:
        template_src = pathlib.Path(template_filename).read_text()
        env = jinja2.Environment(
            extensions=["jinja2.ext.do"],
            comment_start_string="<#",
            comment_end_string="#>",
            block_start_string="<|",
            block_end_string="|>",
            variable_start_string="<<",
            variable_end_string=">>",
        )
        env.globals["math"] = math
        template = env.from_string(template_src)
        render_content = template.render(context)

    except jinja2.TemplateSyntaxError as exc:
        lineno = exc.lineno
        lines = template_src.split("\n")
        msg = f"in {template_filename}, line {lineno}\n\n"
        msg = msg + msg_context(lines, lineno) + "\n"
        msg = msg + text_wrap(exc.message)
        raise Jinja2SyntaxError(msg) from exc

    except jinja2.UndefinedError as exc:
        msg = f"in {template_filename}\n\n"
        msg = msg + exc.message + "\n\n"
        msg = msg + "The template tries to access an undefined variable. \n\n"
        raise Jinja2SyntaxError(msg) from exc

    except jinja2.TemplateError as exc:
        lineno = exc.lineno
        msg = f"in {template_filename}, line {lineno}\n\n"
        msg = msg + exc.message + "\n\n"
        raise Jinja2SyntaxError(msg) from exc

    except Jinja2SyntaxError as exc:
        msg = f"in {template_filename}\n\n"
        msg = msg + f"{exc}" + "\n\n"
        raise Jinja2SyntaxError(msg) from exc

    return render_content


def render(yaml_data, template_filename, extra_context=None):
    context = {
        "header": yaml_data["header"],
        "questions": yaml_data["questions"],
        # "total_marks" : get_total_marks(yaml_data)
    }

    if extra_context:
        context.update(extra_context)

    if template_filename.endswith(".docx"):
        from quizml import docx_renderer

        return docx_renderer.render(context, template_filename)

    return render_template(context, template_filename)

    return ""
