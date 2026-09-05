"""Tests for Moodle XML quiz export."""

import xml.etree.ElementTree as ET
from pathlib import Path

from quizml.builder.config import load_config, resolve_targets
from quizml.builder.scheduler import compile_render_target
from quizml.quizmlyaml.parser import parse_yaml_docs
from quizml.renderer import render
from quizml.transcoder import MarkdownTranscoder


def test_moodle_export_all_question_types():
    yaml_text = r"""
title: "Moodle Midterm Exam"
instructions: "Answer all questions."
---
- type: mc
  title: "Single Choice"
  marks: 2.0
  question: "What is $2 + 2$?"
  shuffle: false
  feedback: "Basic arithmetic."
  feedback_correct: "Well done!"
  feedback_incorrect: "Try again."
  choices:
  - o: "3"
  - x: "4"
  - o: "5"

- type: ma
  title: "Multi Choice"
  marks: 3.0
  question: "Select prime numbers:"
  choices:
  - x: "2"
  - x: "3"
  - o: "4"
  - x: "5"

- type: tf
  title: "True False"
  marks: 1.0
  question: "The Earth is round."
  answer: true
  feedback_correct: "Correct, it is an oblate spheroid."

- type: num
  title: "Numerical"
  marks: 2.0
  question: "What is $\\pi$ to two decimals?"
  answer: 3.14
  tolerance: 0.01

- type: fill
  title: "Short Answer"
  marks: 2.0
  question: "The capital of France is ___."
  answers:
  - "Paris"
  - "paris"

- type: mfill
  title: "Multi Fill"
  marks: 4.0
  question: "Roses are [color1] and violets are [color2]."
  answers:
    color1:
    - "red"
    - "Red"
    color2:
    - "blue"
    - "Blue"

- type: matching
  title: "Matching"
  marks: 3.0
  question: "Match languages to paradigms:"
  choices:
  - A: "Haskell"
    B: "Functional"
  - A: "C"
    B: "Procedural"

- type: ordering
  title: "Ordering"
  marks: 2.0
  question: "Order the numbers:"
  choices:
  - "First"
  - "Second"
  - "Third"

- type: essay
  title: "Essay"
  marks: 5.0
  question: "Explain gradient descent."
  answer: "Model answer explaining optimization steps..."
"""
    header, questions = parse_yaml_docs(yaml_text)
    yaml_doc = {"header": header, "questions": questions}

    transcoder = MarkdownTranscoder(yaml_doc)
    yaml_transcoded = transcoder.transcode_target({"fmt": "html-mathml"})

    template_path = (
        Path(__file__).parent.parent / "src" / "quizml" / "templates" / "moodle.xml.j2"
    )
    rendered_xml = render(yaml_transcoded, template_path)

    assert isinstance(rendered_xml, str)
    assert rendered_xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    # Verify well-formed XML via ElementTree
    root = ET.fromstring(rendered_xml)
    assert root.tag == "quiz"

    # Category + 9 questions = 10 questions total
    question_nodes = root.findall("question")
    assert len(question_nodes) == 10

    # 1. Category
    cat_node = question_nodes[0]
    assert cat_node.attrib.get("type") == "category"
    cat_text = cat_node.find("category/text").text
    assert "$course$/top/Moodle Midterm Exam" in cat_text

    # 2. MC (Single choice)
    mc_node = question_nodes[1]
    assert mc_node.attrib.get("type") == "multichoice"
    assert mc_node.find("single").text == "true"
    assert mc_node.find("shuffleanswers").text == "0"
    mc_answers = mc_node.findall("answer")
    assert len(mc_answers) == 3
    # Fractions should be 0, 100, 0
    assert mc_answers[0].attrib.get("fraction") == "0"
    assert mc_answers[1].attrib.get("fraction") == "100"
    assert mc_answers[2].attrib.get("fraction") == "0"
    assert mc_answers[1].find("text").text == "4"

    # 3. MA (Multiple choice multiple answers)
    ma_node = question_nodes[2]
    assert ma_node.attrib.get("type") == "multichoice"
    assert ma_node.find("single").text == "false"
    ma_answers = ma_node.findall("answer")
    assert len(ma_answers) == 4
    # 3 correct (2, 3, 5) -> +33.33333%, 1 incorrect (4) -> -100%
    fractions = [float(a.attrib.get("fraction")) for a in ma_answers]
    assert round(fractions[0], 2) == 33.33
    assert round(fractions[1], 2) == 33.33
    assert round(fractions[2], 2) == -100.0
    assert round(fractions[3], 2) == 33.33

    # 4. TF (True / False)
    tf_node = question_nodes[3]
    assert tf_node.attrib.get("type") == "truefalse"
    tf_answers = tf_node.findall("answer")
    assert len(tf_answers) == 2
    # Answer is True -> fraction 100 on true, 0 on false
    assert tf_answers[0].attrib.get("fraction") == "100"
    assert tf_answers[0].find("text").text == "true"
    assert tf_answers[1].attrib.get("fraction") == "0"
    assert tf_answers[1].find("text").text == "false"

    # 5. Numerical
    num_node = question_nodes[4]
    assert num_node.attrib.get("type") == "numerical"
    num_answer = num_node.find("answer")
    assert num_answer.attrib.get("fraction") == "100"
    assert num_answer.find("text").text == "3.14"
    assert num_answer.find("tolerance").text == "0.01"

    # 6. Fill (Short answer)
    fill_node = question_nodes[5]
    assert fill_node.attrib.get("type") == "shortanswer"
    fill_answers = fill_node.findall("answer")
    assert len(fill_answers) == 2
    assert fill_answers[0].find("text").text == "Paris"
    assert fill_answers[1].find("text").text == "paris"

    # 7. Multi-Fill (Cloze)
    mfill_node = question_nodes[6]
    assert mfill_node.attrib.get("type") == "cloze"
    cloze_text = mfill_node.find("questiontext/text").text
    assert "{1:SHORTANSWER:=red~=Red}" in cloze_text
    assert "{1:SHORTANSWER:=blue~=Blue}" in cloze_text

    # 8. Matching
    match_node = question_nodes[7]
    assert match_node.attrib.get("type") == "match"
    subquestions = match_node.findall("subquestion")
    assert len(subquestions) == 2
    assert subquestions[0].find("text").text == "Haskell"
    assert subquestions[0].find("answer/text").text == "Functional"
    assert subquestions[1].find("text").text == "C"
    assert subquestions[1].find("answer/text").text == "Procedural"

    # 9. Ordering
    ord_node = question_nodes[8]
    assert ord_node.attrib.get("type") == "ordering"
    assert ord_node.find("layouttype").text == "VERTICAL"
    ord_answers = ord_node.findall("answer")
    assert len(ord_answers) == 3
    assert [a.find("text").text for a in ord_answers] == ["First", "Second", "Third"]

    # 10. Essay
    essay_node = question_nodes[9]
    assert essay_node.attrib.get("type") == "essay"
    assert essay_node.find("responseformat").text == "editor"
    grader_info = essay_node.find("graderinfo/text").text
    assert "Model answer explaining optimization steps..." in grader_info


def test_compile_moodle_target_via_pipeline(tmp_path):
    quiz_file = tmp_path / "sample_moodle_quiz.yaml"
    quiz_file.write_text(
        r"""
title: "Pipeline Moodle Test"
---
- type: mc
  question: "What is $x + y$?"
  choices:
  - x: "Correct"
  - o: "Wrong"
""",
        encoding="utf-8",
    )

    config = load_config()
    from quizml.quizmlyaml import load

    yaml_doc, _ = load(str(quiz_file))

    targets = resolve_targets(
        config,
        yaml_doc,
        requested_targets=["moodle"],
        yaml_filename=str(quiz_file),
    )

    assert len(targets) == 1
    target = targets[0]
    assert target["name"] == "moodle"
    assert target["out"].endswith(".xml")

    # Set output in temporary path
    out_file = tmp_path / "output.xml"
    target["out"] = str(out_file)

    transcoder = MarkdownTranscoder(yaml_doc, base_dir=str(tmp_path))
    success, err = compile_render_target(target, transcoder)
    assert success is True, f"Compilation failed: {err}"
    assert out_file.exists()

    content = out_file.read_text(encoding="utf-8")
    assert '<?xml version="1.0" encoding="UTF-8"?>' in content
    assert "<quiz>" in content
    assert '<math display="inline"' in content

    # Validate XML
    root = ET.fromstring(content)
    assert root.tag == "quiz"


def test_moodle_export_with_tables_and_display_equations(tmp_path):
    quiz_file = tmp_path / "table_math_quiz.yaml"
    quiz_file.write_text(
        r"""
title: "Math and Tables Quiz"
---
- type: mc
  question: |
    Consider the following table:

    | Feature | Value |
    |:--------|------:|
    | Height  |   180 |
    | Weight  |    75 |

    Here is the cost function:

    $$
    J(\theta) = \frac{1}{2m} \sum_{i=1}^m (h_\theta(x^{(i)}) - y^{(i)})^2
    $$

    And another relation:

    \begin{equation}
    E = mc^2
    \end{equation}

    What is the cost?
  choices:
  - x: "$J(\\theta) \\ge 0$"
  - o: "$J(\\theta) < 0$"
""",
        encoding="utf-8",
    )

    from quizml.quizmlyaml import load

    yaml_doc, _ = load(str(quiz_file))
    config = load_config()
    targets = resolve_targets(
        config,
        yaml_doc,
        requested_targets=["moodle"],
        yaml_filename=str(quiz_file),
    )

    out_file = tmp_path / "moodle_output.xml"
    targets[0]["out"] = str(out_file)

    transcoder = MarkdownTranscoder(yaml_doc, base_dir=str(tmp_path))
    success, err = compile_render_target(targets[0], transcoder)
    assert success is True, f"Compilation failed: {err}"
    assert out_file.exists()

    content = out_file.read_text(encoding="utf-8")
    assert "<table" in content
    assert '<math display="block"' in content
    assert "<p><math display=\"block\"" in content

    # XML must be valid and well-formed
    root = ET.fromstring(content)
    assert root.tag == "quiz"

