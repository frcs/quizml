"""quizml exceptions.

This module contains the custom exception classes used throughout the quizml project.
"""


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


class Make4htNotFoundError(LatexToolError):
    """Raised when the make4ht executable is not found."""

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
