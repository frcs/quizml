"""Document representation for loaded QuizML YAML quizzes."""

from collections.abc import Mapping
from typing import Any


class QuizDocument(dict[str, Any]):
    """A dict-compatible representation of a loaded QuizML document.

    Keys:
        - ``header``: Quiz metadata dictionary.
        - ``questions``: List of validated/coerced question dictionaries.
        - ``paths``: Dictionary containing ``input_dir`` and ``figure_dirs``.

    Attributes:
        - ``header``: Shortcut for ``self["header"]``.
        - ``questions``: Shortcut for ``self["questions"]``.
        - ``paths``: Shortcut for ``self["paths"]``.
        - ``schema``: The JSON Schema dictionary used to validate and coerce
          the document (if any).
    """

    schema: dict[str, Any] | None

    def __init__(
        self,
        mapping: Mapping[str, Any] | None = None,
        *,
        schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(mapping or {}, **kwargs)
        self.schema = schema if schema is not None else getattr(mapping, "schema", None)

    @property
    def header(self) -> dict[str, Any]:
        """Return (and initialize if missing) the quiz header dictionary."""
        return self.setdefault("header", {})

    @header.setter
    def header(self, value: dict[str, Any]) -> None:
        self["header"] = value

    @property
    def questions(self) -> list[dict[str, Any]]:
        """Return (and initialize if missing) the list of question dicts."""
        return self.setdefault("questions", [])

    @questions.setter
    def questions(self, value: list[dict[str, Any]]) -> None:
        self["questions"] = value

    @property
    def paths(self) -> dict[str, Any]:
        """Return (and initialize if missing) the paths metadata dictionary."""
        return self.setdefault("paths", {})

    @paths.setter
    def paths(self, value: dict[str, Any]) -> None:
        self["paths"] = value

    def copy(self) -> "QuizDocument":
        """Return a shallow copy preserving the associated JSON Schema."""
        return QuizDocument(super().copy(), schema=self.schema)
