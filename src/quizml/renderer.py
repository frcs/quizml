import math
import pathlib
from functools import lru_cache

import jinja2

from quizml.exceptions import Jinja2SyntaxError, TemplateRenderError
from quizml.utils import msg_context, text_wrap


@lru_cache(maxsize=16)
def _get_jinja_env(search_dirs):
    """Returns a configured Jinja2 Environment with QuizML custom delimiters."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(search_dirs),
        undefined=jinja2.StrictUndefined,
        extensions=["jinja2.ext.do"],
        comment_start_string="<#",
        comment_end_string="#>",
        block_start_string="<|",
        block_end_string="|>",
        variable_start_string="<<",
        variable_end_string=">>",
    )
    env.globals["math"] = math
    return env


def get_jinja_env(search_dirs=None):
    """Return a cached environment configured for the supplied template paths."""
    if search_dirs is None:
        search_dirs = [pathlib.Path(__file__).parent / "templates"]
    return _get_jinja_env(tuple(str(pathlib.Path(path)) for path in search_dirs))


def render_template(context, template_filename, search_dirs=None):
    if not template_filename:
        msg = "Template filename is missing, can't render jinja."
        raise Jinja2SyntaxError(msg)

    try:
        template_path = pathlib.Path(template_filename).resolve()
        template_search_dirs = [template_path.parent]
        if search_dirs:
            template_search_dirs.extend(search_dirs)
        else:
            template_search_dirs.append(pathlib.Path(__file__).parent / "templates")
        env = get_jinja_env(template_search_dirs)
        template_name = template_path.name
        template_src, _, _ = env.loader.get_source(env, template_name)
        template = env.get_template(template_name)
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

    except jinja2.TemplateNotFound as exc:
        msg = f"Template '{exc.name}' could not be loaded from {template_filename}."
        raise Jinja2SyntaxError(msg) from exc

    except jinja2.TemplateError as exc:
        lineno = getattr(exc, "lineno", None)
        msg = f"in {template_filename}"
        if lineno is not None:
            msg += f", line {lineno}"
        msg += "\n\n" + str(exc) + "\n\n"
        raise Jinja2SyntaxError(msg) from exc
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise TemplateRenderError(
            f"Could not read template '{template_filename}': {detail}"
        ) from exc

    return render_content


def render(
    yaml_data, template_filename, extra_context=None, template_search_dirs=None
):
    header = yaml_data["header"]
    paths = yaml_data.get("paths") or {
        "figure_dirs": header.get("_figures_path", [])
    }
    context = {
        "header": header,
        "questions": yaml_data["questions"],
        "paths": paths,
        # "total_marks" : get_total_marks(yaml_data)
    }

    if extra_context:
        context.update(extra_context)

    if template_filename.endswith(".docx"):
        from quizml import docx_renderer

        return docx_renderer.render(context, template_filename)

    return render_template(context, template_filename, template_search_dirs)
