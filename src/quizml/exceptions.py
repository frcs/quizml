"""QuizML exceptions and diagnostic formatting helpers."""

import os
import textwrap


class QuizMLError(Exception):
    """Base class for all quizml exceptions."""

    pass


class QuizMLYamlSyntaxError(QuizMLError):
    """Raised for syntax errors in quizmlyaml files."""

    pass


class QuizMLConfigError(QuizMLError):
    """Raised for configuration errors."""

    pass


class QuizMLBuildError(QuizMLError):
    """Raised when a configured output build command fails."""

    pass


class MarkdownError(QuizMLError):
    """Raised for errors during Markdown processing."""

    pass


class LatexToolError(QuizMLError):
    """Base class for errors related to external LaTeX tools."""

    pass


class LatexNotFoundError(LatexToolError):
    """Raised when the latex or pdflatex executable is not found."""

    pass


class GhostscriptNotFoundError(LatexToolError):
    """Raised when the gs (Ghostscript) executable is not found."""

    pass


class DvisvgmNotFoundError(LatexToolError):
    """Raised when the dvisvgm executable is not found."""

    pass


class LatexCompilationError(LatexToolError):
    """Raised when the LaTeX compilation fails."""

    pass


class MarkdownAttributeError(MarkdownError):
    """Raised for errors related to Markdown attributes."""

    pass


class MarkdownImageError(MarkdownError):
    """Raised for errors related to image processing."""

    pass


class TemplateRenderError(QuizMLError):
    """Raised when a document template cannot be rendered."""

    pass


class Jinja2SyntaxError(TemplateRenderError):
    """Raised for errors during Jinja2 template rendering."""

    pass


def text_wrap(msg):
    """Wrap diagnostic message to terminal width."""
    try:
        w, _ = os.get_terminal_size(0)
    except OSError:
        w = 80
    return textwrap.fill(msg, w - 5)


def msg_context_line(lines, lineo, charno=None, highlight=False):
    if lineo < 1 or lineo > len(lines):
        return ""
    if highlight:
        return f"❱ {lineo:>4} │  {lines[lineo - 1]}\n"
    return f"  {lineo:>4} │ {lines[lineo - 1]}\n"


def msg_context(lines, lineo, charno=None):
    """Format a 3-line source snippet around a 1-based line number."""
    msg = msg_context_line(lines, lineo - 1, charno, highlight=False)
    msg += msg_context_line(lines, lineo, charno, highlight=True)
    msg += msg_context_line(lines, lineo + 1, charno, highlight=False)
    return msg
