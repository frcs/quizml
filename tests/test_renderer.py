
import pytest
import os
import tempfile
from quizml.renderer import render_template, render
from quizml.exceptions import Jinja2SyntaxError

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
