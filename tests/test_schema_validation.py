import os

import pytest

from quizml.exceptions import QuizMLYamlSyntaxError
from quizml.loader import load


def test_incorrect_01():
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-incorrect-01.yaml")

    with pytest.raises(QuizMLYamlSyntaxError) as excinfo:
        load(yaml_file)

    # Check that the error message indicates a problem
    # The actual message depends on the schema and jsonschema version,
    # but it should mention the error.
    assert "YAML parsing error" in str(
        excinfo.value
    ) or "Schema validation error" in str(excinfo.value)


def test_incorrect_02():
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-incorrect-02.yaml")

    with pytest.raises(QuizMLYamlSyntaxError) as excinfo:
        load(yaml_file)

    assert "YAML parsing error" in str(
        excinfo.value
    ) or "Schema validation error" in str(excinfo.value)


def test_missing_file():
    with pytest.raises(QuizMLYamlSyntaxError) as excinfo:
        load("non_existent_file.yaml")
    assert "Yaml file not found" in str(excinfo.value)


@pytest.mark.parametrize(
    "question, expected_message",
    [
        ("- type: mcq\n  question: typo\n", "'mcq' is not one of"),
        (
            "- type: tf\n  question: typo\n  answer: true\n  anwser: true\n",
            "Additional properties are not allowed",
        ),
        (
            "- type: mc\n  question: typo\n  choices:\n    - x: yes\n      y: typo\n",
            "Additional properties are not allowed",
        ),
    ],
)
def test_default_schema_rejects_unknown_types_and_fields(
    tmp_path, question, expected_message
):
    quiz_file = tmp_path / "invalid.yaml"
    quiz_file.write_text(question, encoding="utf-8")

    with pytest.raises(QuizMLYamlSyntaxError, match=expected_message):
        load(str(quiz_file))
