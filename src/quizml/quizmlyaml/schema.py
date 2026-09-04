"""JSON Schema loading for QuizML documents."""

import json
from pathlib import Path

from quizml.exceptions import QuizMLYamlSyntaxError


def load_schema(schema_path: str | Path | None = None) -> dict:
    """Loads and returns the QuizML JSON Schema dictionary.

    If schema_path is None, resolves the bundled default schema.json.
    """
    if schema_path is None:
        from quizml.cli.filelocator import locate

        try:
            schema_path = locate.path("schema.json")
        except FileNotFoundError as err:
            raise QuizMLYamlSyntaxError("Default schema.json not found") from err

    try:
        schema_str = Path(schema_path).read_text(encoding="utf-8")
        return json.loads(schema_str)
    except FileNotFoundError as err:
        raise QuizMLYamlSyntaxError(f"Schema file not found: {schema_path}") from err
    except json.JSONDecodeError as err:
        raise QuizMLYamlSyntaxError(f"Invalid JSON in schema: {err}") from err
    except TypeError as err:
        raise QuizMLYamlSyntaxError(
            "Schema must be provided for validation when validate=True."
        ) from err
