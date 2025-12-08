"""bbquiz exceptions.

This module contains the custom exception classes used throughout the bbquiz project.
"""

class BBQuizError(Exception):
    """Base class for all bbquiz exceptions."""
    pass

class BBYamlSyntaxError(BBQuizError):
    """Raised for syntax errors in bbyaml files."""
    pass

class BBQuizConfigError(BBQuizError):
    """Raised for configuration errors."""
    pass

class MarkdownError(BBQuizError):
    """Raised for errors during Markdown processing."""
    pass

class LatexEqError(MarkdownError):
    """DEPRECATED: Use LatexCompilationError.
    Raised for errors related to LaTeX equation processing."""
    pass


class LatexToolError(BBQuizError):
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

class Jinja2SyntaxError(BBQuizError):
    """Raised for errors during Jinja2 template rendering."""
    pass
