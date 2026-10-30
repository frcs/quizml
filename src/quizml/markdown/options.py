"""Markdown option normalization and validation for QuizML."""

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from quizml.exceptions import QuizMLConfigError

VALID_MARKDOWN_KEYS: frozenset[str] = frozenset(
    {
        "format",
        "math",
        "html_postprocess",
        "png_dpi",
        "png_scale",
        "svg_scale",
        "svg_converter",
    }
)

HTML_MATH_BACKEND_MAP: dict[str, str] = {
    "png": "html",
    "svg": "html-svg",
    "mathml": "html-mathml",
    "passthrough": "html-passthrough",
    "mathjax": "html-passthrough",
    "katex": "html-passthrough",
    "none": "html-passthrough",
}

LEGACY_FMT_VALUES: tuple[str, ...] = (
    "latex",
    "html",
    "html-svg",
    "html-mathml",
    "docx",
)


@dataclass
class MarkdownOptions:
    """Normalized Markdown transcoding options."""

    fmt: str = "html"
    html_postprocess: str | Callable[..., str] | None = None
    png_dpi: int | float | None = None
    png_scale: int | float | None = None
    svg_scale: int | float | None = None
    svg_converter: str | None = None


def _raise_error(msg: str, config_error: bool) -> None:
    """Raise ``QuizMLConfigError`` if ``config_error``, else ``ValueError``."""
    if config_error:
        raise QuizMLConfigError(msg)
    raise ValueError(msg)


def _is_valid_postprocess(postprocess: Any) -> bool:
    """Return True if ``postprocess`` is a supported HTML postprocessor spec."""
    return (
        postprocess is None
        or postprocess == "blackboard_html"
        or callable(postprocess)
        or (isinstance(postprocess, str) and ":" in postprocess)
    )


def _resolve_renderer_fmt(
    output_format: str,
    math_backend: str,
    postprocess: Any,
    t_name: str,
    config_error: bool,
) -> str:
    """Map public ``markdown.format`` and ``markdown.math`` to internal ``fmt``."""
    non_html_err = (
        "markdown.html_postprocess can only be used with markdown.format: html."
        if config_error
        else "HTML postprocessing requires Markdown format 'html'."
    )

    if output_format == "latex":
        if postprocess is not None:
            _raise_error(non_html_err, config_error)
        return "latex"

    if output_format in ("markdown", "none"):
        if postprocess is not None:
            _raise_error(non_html_err, config_error)
        return "markdown"

    if output_format == "docx":
        if postprocess is not None:
            _raise_error(non_html_err, config_error)
        return "docx"

    if output_format == "html":
        renderer_format = HTML_MATH_BACKEND_MAP.get(math_backend)
        if renderer_format is None:
            _raise_error(
                f"Unknown Markdown math backend '{math_backend}' in target '{t_name}'."
                if config_error
                else f"Unknown Markdown math backend: {math_backend}",
                config_error,
            )
        return renderer_format

    _raise_error(
        f"Unknown Markdown format '{output_format}' in target '{t_name}'."
        if config_error
        else f"Unknown Markdown output format: {output_format}",
        config_error,
    )
    return "html"  # Unreachable


def normalize_markdown_options(
    options: dict[str, Any] | MarkdownOptions | None = None,
    *,
    target_name: str | None = None,
    config_error: bool = False,
) -> dict[str, Any]:
    """Translate public ``markdown`` (or legacy ``fmt``) settings into renderer options.

    Args:
        options: A dictionary (or ``MarkdownOptions`` instance) containing a
            ``markdown`` mapping or legacy ``fmt`` key.
        target_name: Optional target name used in ``QuizMLConfigError`` messages.
        config_error: If True, raise ``QuizMLConfigError`` with config-specific
            wording; otherwise raise ``ValueError``.
    """
    if isinstance(options, MarkdownOptions):
        opts = {k: v for k, v in asdict(options).items() if v is not None}
    else:
        opts = dict(options or {})

    t_name = str(target_name or opts.get("name", "<unnamed>"))
    markdown = opts.get("markdown")

    if isinstance(markdown, dict):
        for key in ("png_dpi", "png_scale", "svg_scale", "svg_converter"):
            if key in markdown and key not in opts:
                opts[key] = markdown[key]

    if markdown is not None:
        if not isinstance(markdown, dict):
            _raise_error(
                f"Target '{t_name}' markdown setting must be a mapping."
                if config_error
                else "The markdown option must be a mapping.",
                config_error,
            )

        unknown_settings = set(markdown) - VALID_MARKDOWN_KEYS
        if unknown_settings:
            unknown = ", ".join(sorted(unknown_settings))
            _raise_error(
                f"Unknown Markdown setting(s) for target '{t_name}': {unknown}."
                if config_error
                else f"Unknown Markdown setting(s): {unknown}",
                config_error,
            )

        # If 'fmt' was already resolved on a prior pass, return as-is.
        if "fmt" in opts and not config_error:
            return opts

        output_format = str(markdown.get("format", "html"))
        math_backend = str(markdown.get("math", "png"))
        postprocess = markdown.get("html_postprocess")

        if not _is_valid_postprocess(postprocess):
            _raise_error(
                f"Unknown HTML postprocessor '{postprocess}' in target '{t_name}'."
                if config_error
                else f"Unknown HTML postprocessor: {postprocess}",
                config_error,
            )

        opts["fmt"] = _resolve_renderer_fmt(
            output_format, math_backend, postprocess, t_name, config_error
        )
        opts["html_postprocess"] = postprocess
        for opt_key in ("png_dpi", "png_scale", "svg_scale", "svg_converter"):
            if opt_key in markdown:
                opts[opt_key] = markdown[opt_key]
        return opts

    if "fmt" in opts:
        legacy_fmt = opts["fmt"]
        if config_error:
            if legacy_fmt not in LEGACY_FMT_VALUES:
                raise QuizMLConfigError(f"Unknown legacy fmt value '{legacy_fmt}'.")
            if "html_postprocess" not in opts:
                opts["html_postprocess"] = (
                    "blackboard_html" if str(legacy_fmt).startswith("html") else None
                )
        return opts

    return opts
