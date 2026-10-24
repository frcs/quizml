"""Unified template and document rendering package for QuizML."""

import pathlib

from quizml.rendering.docx import render as render_docx
from quizml.rendering.jinja import (
    _get_jinja_env,
    _load_filter_callable,
    get_jinja_env,
    render_template,
)
from quizml.rendering.qti import prepare_qti_context, render_qti


def render(
    yaml_data,
    template_filename,
    extra_context=None,
    template_search_dirs=None,
    jinja_filters=None,
    *,
    backend=None,
):
    """Render a QuizML document into text or binary output using the appropriate backend."""
    header = yaml_data["header"]
    paths = yaml_data.get("paths") or {
        "figure_dirs": header.get("_figures_path", [])
    }
    context = {
        "header": header,
        "questions": yaml_data["questions"],
        "paths": paths,
    }

    if extra_context:
        context.update(extra_context)

    str_template = str(template_filename)
    p = pathlib.Path(str_template)

    resolved_backend = backend
    if resolved_backend is None:
        if str_template.endswith(".docx"):
            resolved_backend = "docx"
        elif p.is_dir() or "qti" in p.name.lower():
            resolved_backend = "qti"
        else:
            resolved_backend = "jinja"

    if resolved_backend == "docx":
        docx_kwargs = {"jinja_filters": jinja_filters} if jinja_filters else {}
        return render_docx(context, str_template, **docx_kwargs)

    if resolved_backend == "qti":
        return render_qti(
            context,
            p,
            search_dirs=template_search_dirs,
            jinja_filters=jinja_filters,
        )

    kwargs = {"jinja_filters": jinja_filters} if jinja_filters else {}
    return render_template(
        context, str_template, template_search_dirs, **kwargs
    )


__all__ = [
    "_get_jinja_env",
    "_load_filter_callable",
    "get_jinja_env",
    "prepare_qti_context",
    "render",
    "render_docx",
    "render_qti",
    "render_template",
]
