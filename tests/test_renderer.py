import os
import tempfile

import pytest

from quizml.exceptions import Jinja2SyntaxError
from quizml.renderer import render, render_template


def test_render_template_success():
    # Create a temporary template file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jinja", delete=False) as tmp:
        tmp.write("Hello << name >>!")
        tmp_path = tmp.name

    try:
        context = {"name": "World"}
        result = render_template(context, tmp_path)
        assert result == "Hello World!"
    finally:
        os.remove(tmp_path)


def test_render_template_syntax_error():
    # Create a temporary template file with syntax error
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jinja", delete=False) as tmp:
        tmp.write("Hello << name >>! <| if x |>")  # Missing end block
        tmp_path = tmp.name

    try:
        context = {"name": "World"}
        with pytest.raises(Jinja2SyntaxError):
            render_template(context, tmp_path)
    finally:
        os.remove(tmp_path)


def test_render_function():
    # Test the high-level render function
    yaml_data = {
        "header": {"title": "My Quiz"},
        "questions": [{"question": "What is 1+1?"}],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jinja", delete=False) as tmp:
        tmp.write("Title: << header.title >>\nQuestion: << questions[0].question >>")
        tmp_path = tmp.name

    try:
        result = render(yaml_data, tmp_path)
        assert "Title: My Quiz" in result
        assert "Question: What is 1+1?" in result
    finally:
        os.remove(tmp_path)


def test_render_missing_template():
    with pytest.raises(Jinja2SyntaxError):
        render_template({}, "")


def test_template_composition_uses_quizml_search_paths(tmp_path):
    (tmp_path / "macros.j2").write_text(
        "<| macro greeting(name) |>Hello << name >>!<| endmacro |>",
        encoding="utf-8",
    )
    (tmp_path / "base.j2").write_text(
        "Before <| block content |>base<| endblock |> After", encoding="utf-8"
    )
    child = tmp_path / "custom.j2"
    child.write_text(
        '<| extends "base.j2" |><| import "macros.j2" as m |>'
        "<| block content |><< m.greeting(title) >><| endblock |>",
        encoding="utf-8",
    )

    assert render_template({"title": "QuizML"}, child) == "Before Hello QuizML! After"


def test_strict_undefined_reports_missing_template_variable(tmp_path):
    template = tmp_path / "undefined.j2"
    template.write_text("<< misspelled_name >>", encoding="utf-8")

    with pytest.raises(Jinja2SyntaxError, match="undefined variable"):
        render_template({}, template)
