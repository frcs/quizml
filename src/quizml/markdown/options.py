"""Markdown option normalization and validation for QuizML."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quizml.exceptions import QuizMLConfigError

VALID_MARKDOWN_KEYS = {
    "format",
    "math",
    "html_postprocess",
    "png_dpi",
    "png_scale",
    "svg_scale",
    "svg_converter",
}

HTML_MATH_BACKEND_MAP = {
    "png": "html",
    "svg": "html-svg",
    "mathml": "html-mathml",
    "passthrough": "html-passthrough",
    "mathjax": "html-passthrough",
    "katex": "html-passthrough",
    "none": "html-passthrough",
}

LEGACY_FMT_VALUES = ("latex", "html", "html-svg", "html-mathml", "docx")


@dataclass
class MarkdownOptions:
    """Normalized Markdown transcoding options."""

    fmt: str = "html"
    html_postprocess: str | Callable | None = None
    png_dpi: int | float | None = None
    png_scale: int | float | None = None
    svg_scale: int | float | None = None
    svg_converter: str | None = None


def _raise_error(msg: str, config_error: bool):
    if config_error:
        raise QuizMLConfigError(msg)
    raise ValueError(msg)


def normalize_markdown_options(
    options: dict[str, Any] | None = None,
    *,
    target_name: str | None = None,
    config_error: bool = False,
) -> dict[str, Any]:
    """Translate public `markdown` (or legacy `fmt`) settings into internal renderer options.

    Args:
        options: A dictionary containing `markdown` mapping or legacy `fmt` key.
        target_name: Optional target name used in `QuizMLConfigError` messages.
        config_error: If True, raise `QuizMLConfigError` with config-specific wording;
                      otherwise raise `ValueError`.
    """
    options = dict(options or {})
    t_name = target_name or options.get("name", "<unnamed>")
    markdown = options.get("markdown")

    if isinstance(markdown, dict):
        for key in ("png_dpi", "png_scale", "svg_scale", "svg_converter"):
            if key in markdown and key not in options:
                options[key] = markdown[key]

    if markdown is not None:
        if not isinstance(markdown, dict):
            if config_error:
                raise QuizMLConfigError(
                    f"Target '{t_name}' markdown setting must be a mapping."
                )
            raise ValueError("The markdown option must be a mapping.")

        unknown_settings = set(markdown) - VALID_MARKDOWN_KEYS
        if unknown_settings:
            unknown = ", ".join(sorted(unknown_settings))
            if config_error:
                raise QuizMLConfigError(
                    f"Unknown Markdown setting(s) for target '{t_name}': {unknown}."
                )
            raise ValueError(f"Unknown Markdown setting(s): {unknown}")

        if "fmt" in options and not config_error:
            return options

        output_format = markdown.get("format", "html")
        math_backend = markdown.get("math", "png")
        postprocess = markdown.get("html_postprocess")

        valid_postprocess = (
            postprocess is None
            or postprocess == "blackboard_html"
            or callable(postprocess)
            or (isinstance(postprocess, str) and ":" in postprocess)
        )
        if not valid_postprocess:
            if config_error:
                raise QuizMLConfigError(
                    f"Unknown HTML postprocessor '{postprocess}' in target '{t_name}'."
                )
            raise ValueError(f"Unknown HTML postprocessor: {postprocess}")

        if output_format == "latex":
            if postprocess is not None:
                _raise_error(
                    "markdown.html_postprocess can only be used with markdown.format: html."
                    if config_error
                    else "HTML postprocessing requires Markdown format 'html'.",
                    config_error,
                )
            options["fmt"] = "latex"
        elif output_format in ("markdown", "none"):
            if postprocess is not None:
                _raise_error(
                    "markdown.html_postprocess can only be used with markdown.format: html."
                    if config_error
                    else "HTML postprocessing requires Markdown format 'html'.",
                    config_error,
                )
            options["fmt"] = "markdown"
        elif output_format == "docx":
            if postprocess is not None:
                _raise_error(
                    "markdown.html_postprocess can only be used with markdown.format: html."
                    if config_error
                    else "HTML postprocessing requires Markdown format 'html'.",
                    config_error,
                )
            options["fmt"] = "docx"
        elif output_format == "html":
            renderer_format = HTML_MATH_BACKEND_MAP.get(math_backend)
            if renderer_format is None:
                if config_error:
                    raise QuizMLConfigError(
                        f"Unknown Markdown math backend '{math_backend}' in target '{t_name}'."
                    )
                raise ValueError(f"Unknown Markdown math backend: {math_backend}")
            options["fmt"] = renderer_format
        else:
            if config_error:
                raise QuizMLConfigError(
                    f"Unknown Markdown format '{output_format}' in target '{t_name}'."
                )
            raise ValueError(f"Unknown Markdown output format: {output_format}")

        options["html_postprocess"] = postprocess
        for opt_key in ("png_dpi", "png_scale", "svg_scale", "svg_converter"):
            if opt_key in markdown:
                options[opt_key] = markdown[opt_key]
        return options

    if "fmt" in options:
        legacy_fmt = options["fmt"]
        if config_error:
            if legacy_fmt not in LEGACY_FMT_VALUES:
                raise QuizMLConfigError(f"Unknown legacy fmt value '{legacy_fmt}'.")
            if "html_postprocess" not in options:
                options["html_postprocess"] = (
                    "blackboard_html" if str(legacy_fmt).startswith("html") else None
                )
        return options

    return options
