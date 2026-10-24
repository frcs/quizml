import os
import tempfile

import pytest

from quizml.exceptions import Jinja2SyntaxError
from quizml.rendering import render, render_template


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


def test_custom_jinja_filters_callable_and_module_spec(tmp_path):
    template = tmp_path / "filters.j2"
    template.write_text(
        "<< header.title | shout >> - << 'hello world' | slugify >>",
        encoding="utf-8",
    )
    yaml_data = {"header": {"title": "Exam"}, "questions": []}

    result = render(
        yaml_data,
        str(template),
        jinja_filters={
            "shout": lambda s: f"{s.upper()}!",
            "slugify": "urllib.parse:quote_plus",
        },
    )
    assert result == "EXAM! - hello+world"


def test_target_context_and_filters_in_compile_target(tmp_path):
    from quizml.cli.compile import compile_target
    from quizml.markdown.markdown import MarkdownTranscoder

    template = tmp_path / "exam.j2"
    template.write_text(
        "Title: << header.title | upper_fn >> | Solutions: << show_solutions >> | Target: << target.name >>",
        encoding="utf-8",
    )
    out_file = tmp_path / "out.txt"
    yaml_data = {"header": {"title": "Midterm"}, "questions": []}
    transcoder = MarkdownTranscoder(yaml_data, base_dir=str(tmp_path))
    target = {
        "name": "solutions-tex",
        "template": str(template),
        "out": str(out_file),
        "context": {"show_solutions": True},
        "jinja_filters": {"upper_fn": "builtins:str.upper"},
    }
    compile_target(target, transcoder)
    assert (
        out_file.read_text(encoding="utf-8")
        == "Title: MIDTERM | Solutions: True | Target: solutions-tex"
    )


def test_custom_html_postprocessor(tmp_path):
    from quizml.markdown.markdown import MarkdownTranscoder
    from quizml.yaml import MarkdownString

    yamldoc = {
        "header": {},
        "questions": [
            {
                "type": "essay",
                "question": MarkdownString("Hello **world**"),
            }
        ],
    }
    transcoder = MarkdownTranscoder(yamldoc, base_dir=str(tmp_path))
    res = transcoder.transcode_target(
        {
            "markdown": {
                "format": "html",
                "html_postprocess": lambda html, opts: f"<div class='q'>{html.strip()}</div>",
            }
        }
    )
    assert (
        res["questions"][0]["question"]
        == "<div class='q'><p>Hello <strong>world</strong></p></div>"
    )


def test_preview_template_supports_custom_types_part_dividers_and_no_static_polling():
    import pathlib

    preview_path = (
        pathlib.Path(__file__).parent.parent
        / "src"
        / "quizml"
        / "templates"
        / "preview.html.j2"
    )
    yaml_data = {
        "header": {"title": "Preview Quiz"},
        "questions": [
            {"type": "part", "question": "Part A"},
            {
                "type": "geolocation",
                "marks": 3.5,
                "question": "Find Dublin",
                "answer": "53.3498 N, 6.2603 W",
            },
            {
                "type": "essay",
                "marks": 5,
                "question": "Explain",
                "answer": "Because.",
            },
        ],
    }
    html_static = render(yaml_data, str(preview_path))
    assert "Total Possible Marks: 8.5" in html_static
    assert "Part A" in html_static
    assert "data-questionid='1'" in html_static
    assert "data-questionid='2'" in html_static
    assert "data-questionid='3'" not in html_static
    assert "geolocation" in html_static
    assert "Find Dublin" in html_static
    assert "setInterval" not in html_static

    html_watch = render(
        yaml_data, str(preview_path), extra_context={"livereload_port": 35729}
    )
    assert "setInterval(checkServerUpdate, 100);" in html_watch


def test_docx_renderer_receives_configured_jinja_env(monkeypatch):
    from unittest.mock import MagicMock

    from quizml.rendering import docx as docx_renderer

    captured = {}

    class FakeDocxTemplate:
        def __init__(self, filename):
            captured["filename"] = filename

        def render(self, context, jinja_env=None):
            captured["context"] = context
            captured["jinja_env"] = jinja_env

        def save(self, stream):
            stream.write(b"PK-fake-docx")

    fake_mod = MagicMock(DocxTemplate=FakeDocxTemplate)
    monkeypatch.setitem(__import__("sys").modules, "docxtpl", fake_mod)

    out = docx_renderer.render(
        {"header": {"title": "Exam"}},
        "template.docx",
        jinja_filters={"shout": lambda s: s.upper()},
    )
    assert out == b"PK-fake-docx"
    assert "math" in captured["jinja_env"].globals
    assert "shout" in captured["jinja_env"].filters


