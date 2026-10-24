"""Document representation for loaded QuizML YAML quizzes."""


class QuizDocument(dict):
    """A dict-compatible representation of a loaded QuizML document.

    Keys:
        - ``header``: Quiz metadata dictionary.
        - ``questions``: List of validated/coerced question dictionaries.
        - ``paths``: Dictionary containing ``input_dir`` and ``figure_dirs``.

    Attributes:
        - ``header``: Shortcut for ``self["header"]``.
        - ``questions``: Shortcut for ``self["questions"]``.
        - ``paths``: Shortcut for ``self["paths"]``.
        - ``schema``: The JSON Schema dictionary used to validate/coerce the document (if any).
    """

    def __init__(self, mapping=None, *, schema=None, **kwargs):
        super().__init__(mapping or {}, **kwargs)
        self.schema = (
            schema
            if schema is not None
            else getattr(mapping, "schema", None)
        )

    @property
    def header(self) -> dict:
        return self.setdefault("header", {})

    @header.setter
    def header(self, value: dict):
        self["header"] = value

    @property
    def questions(self) -> list:
        return self.setdefault("questions", [])

    @questions.setter
    def questions(self, value: list):
        self["questions"] = value

    @property
    def paths(self) -> dict:
        return self.setdefault("paths", {})

    @paths.setter
    def paths(self, value: dict):
        self["paths"] = value

    def copy(self) -> "QuizDocument":
        return QuizDocument(super().copy(), schema=self.schema)
