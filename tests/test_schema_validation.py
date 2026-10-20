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


def test_default_schema_does_not_depend_on_cwd_template_lookup(tmp_path, monkeypatch):
    template_dir = tmp_path / "quizml-templates"
    template_dir.mkdir()
    (template_dir / "schema.json").write_text(
        '{"type": "array"}', encoding="utf-8"
    )
    quiz_file = tmp_path / "invalid.yaml"
    quiz_file.write_text(
        "- type: unknown\n  question: Not a supported question\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(QuizMLYamlSyntaxError, match="not one of"):
        load(str(quiz_file))


@pytest.mark.parametrize(
    "yaml_text, expected_path",
    [
        ("title: [1, 2]\n---\n- type: essay\n  question: Q\n", "title"),
        (
            "_figures_path: {invalid: true}\n---\n- type: essay\n  question: Q\n",
            "_figures_path",
        ),
    ],
)
def test_default_schema_validates_known_header_fields(
    tmp_path, yaml_text, expected_path
):
    quiz_file = tmp_path / "invalid-header.yaml"
    quiz_file.write_text(yaml_text, encoding="utf-8")

    with pytest.raises(QuizMLYamlSyntaxError) as exc_info:
        load(str(quiz_file))

    message = str(exc_info.value)
    assert "Header schema validation error" in message
    assert expected_path in message
    assert "line ~1" in message


def test_default_schema_allows_empty_and_null_header_fields(tmp_path):
    quiz_text = (
        "examvenue:\n"
        "title: null\n"
        "instructions: null\n"
        "_figures_path: null\n"
        "_targets: null\n"
        "---\n"
        "- type: tf\n"
        "  question: Is empty header allowed?\n"
        "  answer: true\n"
    )
    quiz_file = tmp_path / "empty-header.yaml"
    quiz_file.write_text(quiz_text, encoding="utf-8")

    document, _ = load(str(quiz_file))
    assert document["header"]["examvenue"] is None
    assert document["header"]["title"] is None
    assert document["header"]["instructions"] is None
    assert document["header"]["_targets"] is None
    assert document["paths"]["figure_dirs"] == []


def test_default_schema_allows_custom_header_metadata(tmp_path):
    quiz_file = tmp_path / "custom-header.yaml"
    quiz_file.write_text(
        "custom_metadata: project-specific\n---\n- type: essay\n  question: Q\n",
        encoding="utf-8",
    )

    document, _ = load(str(quiz_file))

    assert document["header"]["custom_metadata"] == "project-specific"
