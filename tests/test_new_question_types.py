import json
import os

from jsonschema import validate

from quizml.loader import load
from quizml.renderer import render


def test_new_question_types_schema_validation():
    # Load the schema
    schema_path = os.path.join("src", "quizml", "templates", "schema.json")
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    # Sample data from newquestions.yaml
    questions = [
        {
            "type": "fill",
            "marks": 5,
            "question": "The color of the sky on a clear day is _____.",
            "answers": ["blue", "Blue", "cyan"],
        },
        {
            "type": "mfill",
            "marks": 5,
            "question": "Roses are [color1] and violets are [color2].",
            "answers": {"color1": ["red", "Red"], "color2": ["blue", "Blue"]},
        },
        {
            "type": "num",
            "marks": 5,
            "question": "What is the value of $\\pi$ to two decimal places?",
            "answer": 3.14,
            "tolerance": 0.01,
        },
    ]

    # Validate against schema
    validate(instance=questions, schema=schema)


def test_new_question_types_rendering(tmp_path):
    # Create a temporary yaml file with the new questions
    questions_yaml = """
-
  type: fill
  marks: 5
  question: |
    The color of the sky on a clear day is _____.
  answers:
    - blue
    - Blue
    - cyan

-
  type: mfill
  marks: 5
  question: |
    Roses are [color1] and violets are [color2].
  answers:
    color1:
      - red
      - Red
    color2:
      - blue
      - Blue

-
  type: num
  marks: 5
  question: |
     What is the value of $\\\\pi$ to two decimal places?
  answer: 3.14
  tolerance: 0.01
"""
    temp_yaml = tmp_path / "temp_new_questions.yaml"
    temp_yaml.write_text(questions_yaml, encoding="utf-8")

    # Load using the updated schema
    doc, _ = load(str(temp_yaml))

    # Test rendering with each updated template
    templates = [
        "blackboard.txt.j2",
        "stats.txt.j2",
        "preview.html.j2",
        "tcd-exam.tex.j2",
    ]

    for template_name in templates:
        template_path = os.path.join("src", "quizml", "templates", template_name)
        output = render(doc, template_path)
        assert output is not None
        if template_name == "blackboard.txt.j2":
            assert "FIB\t" in output
            assert "FIB_PLUS\t" in output
            # Check for FIB_PLUS format: double tab before subsequent variables
            assert "color1\tred\tRed\t\tcolor2\tblue\tBlue" in output
            assert "NUM\t" in output
        elif template_name == "stats.txt.j2":
            assert "fill" in output
            assert "mfill" in output
            assert "num" in output
        elif template_name == "preview.html.j2":
            assert "Fill in the Blank" in output
            assert "Fill in Multiple Blanks" in output
            assert "Calculated Numeric" in output
        elif template_name == "tcd-exam.tex.j2":
            assert "fill-in" in output
            assert "numeric" in output
            assert "acceptable answers" in output
