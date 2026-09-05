import os
import tempfile

import pytest

from quizml.exceptions import Jinja2SyntaxError
from quizml.renderer import render, render_template


def test_render_template_success():
    # Create a temporary template file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jinja', delete=False) as tmp:
        tmp.write("Hello << name >>!")
        tmp_path = tmp.name
    
    try:
        context = {'name': 'World'}
        result = render_template(context, tmp_path)
        assert result == "Hello World!"
    finally:
        os.remove(tmp_path)

def test_render_template_syntax_error():
    # Create a temporary template file with syntax error
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jinja', delete=False) as tmp:
        tmp.write("Hello << name >>! <| if x |>") # Missing end block
        tmp_path = tmp.name
    
    try:
        context = {'name': 'World'}
        with pytest.raises(Jinja2SyntaxError):
            render_template(context, tmp_path)
    finally:
        os.remove(tmp_path)

def test_render_function():
    # Test the high-level render function
    yaml_data = {
        'header': {'title': 'My Quiz'},
        'questions': [{'question': 'What is 1+1?'}]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jinja', delete=False) as tmp:
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


def test_blackboard_table_sanitization():
    from quizml.renderer.blackboard import (
        process_questions_for_blackboard,
        sanitize_blackboard_html,
    )

    raw_html = (
        '<div class="confmat">\n'
        '<style scoped>.confmat td {border: 1px solid gray;}</style>\n'
        '<table style="border-collapse: collapse;">\n'
        '<thead><tr><th>Head 1</th><th>Head 2</th></tr></thead>\n'
        '<tbody><tr><td style="color: red;">Val 1</td><td>Val 2</td></tr></tbody>\n'
        '</table>\n'
        '</div>'
    )
    cleaned = sanitize_blackboard_html(raw_html)
    assert "<style" not in cleaned
    assert "<div" not in cleaned
    assert "<thead" not in cleaned
    assert "<tbody" not in cleaned
    assert '<table border="1" style="border-collapse: collapse;">' in cleaned
    assert "<th>Head 1</th>" in cleaned
    assert "<td>Val 1</td>" in cleaned
    assert "\n" not in cleaned
    assert "\t" not in cleaned


def test_blackboard_render_integration():
    doc = {
        "header": {"title": "Quiz"},
        "questions": [
            {
                "type": "mc",
                "question": '<div class="test"><style>p{}</style><table><tr><td>Q1</td></tr></table></div>',
                "choices": [
                    {"x": "Option A"},
                    {"o": "Option B"},
                ],
            }
        ],
    }
    rendered = render(doc, "blackboard.txt.j2")
    assert '<table border="1"' in rendered
    assert "<div" not in rendered
    assert "<style" not in rendered
    assert "\t" in rendered
    assert "MC\t" in rendered

