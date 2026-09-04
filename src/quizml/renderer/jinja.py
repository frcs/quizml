"""Jinja2 rendering engine with LaTeX-safe custom delimiters."""

import functools
import math
import os
import pathlib
import textwrap

import jinja2

from quizml.exceptions import Jinja2SyntaxError


def _text_wrap(msg: str) -> str:
    try:
        w, _ = os.get_terminal_size(0)
    except OSError:
        w = 80
    return textwrap.fill(msg, max(20, w - 5))


def _msg_context_line(lines: list[str], lineo: int, highlight: bool = False) -> str:
    if lineo < 1 or lineo > len(lines):
        return ""
    if highlight:
        return f"❱ {lineo:>4} │  {lines[lineo - 1]}\n"
    return f"  {lineo:>4} │ {lines[lineo - 1]}\n"


def _msg_context(lines: list[str], lineo: int) -> str:
    msg = _msg_context_line(lines, lineo - 1, highlight=False)
    msg += _msg_context_line(lines, lineo, highlight=True)
    msg += _msg_context_line(lines, lineo + 1, highlight=False)
    return msg


@functools.lru_cache(maxsize=1)
def get_jinja_env():
    """Returns a configured Jinja2 Environment with QuizML custom delimiters."""
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
    return env


def render_template(context: dict, template_filename: str | pathlib.Path) -> str:
    """Renders a Jinja2 template file with the given context dict."""
    if not template_filename:
        msg = "Template filename is missing, can't render jinja."
        raise Jinja2SyntaxError(msg)

    template_path = pathlib.Path(template_filename)
    try:
        template_src = template_path.read_text(encoding="utf-8")
        env = get_jinja_env()
        template = env.from_string(template_src)
        return template.render(context)

    except jinja2.TemplateSyntaxError as exc:
        lineno = exc.lineno
        lines = template_src.split("\n")
        msg = f"in {template_filename}, line {lineno}\n\n"
        msg = msg + _msg_context(lines, lineno) + "\n"
        msg = msg + _text_wrap(exc.message)
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

    except Exception as exc:
        msg = f"in {template_filename}\n\n"
        msg = msg + f"{exc}" + "\n\n"
        raise Jinja2SyntaxError(msg) from exc
