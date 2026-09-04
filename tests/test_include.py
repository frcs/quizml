from pathlib import Path

import pytest

from quizml.exceptions import QuizMLYamlSyntaxError
from quizml.loader import count_included_questions, load, loads


def test_basic_include(tmp_path: Path):
    sub_yaml = tmp_path / "bank.yaml"
    sub_yaml.write_text(
        """
- type: essay
  marks: 5
  question: Sub question 1
  answer: Answer 1
- type: essay
  marks: 10
  question: Sub question 2
  answer: Answer 2
""",
        encoding="utf-8",
    )

    main_yaml = tmp_path / "main.yaml"
    main_yaml.write_text(
        """
title: Exam with Included Questions
---
- type: essay
  marks: 2
  question: Main Question 1
  answer: Main Answer 1
- _include: bank.yaml
- type: essay
  marks: 3
  question: Main Question 2
  answer: Main Answer 2
""",
        encoding="utf-8",
    )

    doc, _ = load(str(main_yaml), validate=False)
    questions = doc["questions"]
    assert len(questions) == 4
    assert questions[0]["question"] == "Main Question 1"
    assert questions[1]["question"] == "Sub question 1"
    assert questions[2]["question"] == "Sub question 2"
    assert questions[3]["question"] == "Main Question 2"


def test_include_with_header(tmp_path: Path):
    sub_yaml = tmp_path / "bank_with_header.yaml"
    sub_yaml.write_text(
        """
module: EEU1234
author: Jane Doe
---
- type: essay
  marks: 5
  question: Bank question
  answer: Answer
""",
        encoding="utf-8",
    )

    main_yaml = tmp_path / "main.yaml"
    main_yaml.write_text(
        """
title: Test Exam
---
- _include: bank_with_header.yaml
""",
        encoding="utf-8",
    )

    doc, _ = load(str(main_yaml), validate=False)
    assert doc["header"]["title"] == "Test Exam"
    # Sub-file header is ignored; only questions are spliced
    assert "author" not in doc["header"]
    assert len(doc["questions"]) == 1
    assert doc["questions"][0]["question"] == "Bank question"


def test_nested_and_relative_includes(tmp_path: Path):
    sub_dir = tmp_path / "questions"
    sub_dir.mkdir()
    nested_dir = sub_dir / "topics"
    nested_dir.mkdir()

    nested_file = nested_dir / "math.yaml"
    nested_file.write_text(
        """
- type: essay
  marks: 5
  question: What is 2 + 2?
  answer: 4
""",
        encoding="utf-8",
    )

    sub_file = sub_dir / "section_a.yaml"
    sub_file.write_text(
        """
- type: essay
  marks: 2
  question: Intro question
  answer: Intro answer
- _include: topics/math.yaml
""",
        encoding="utf-8",
    )

    main_yaml = tmp_path / "exam.yaml"
    main_yaml.write_text(
        """
title: Final Exam
---
- _include: questions/section_a.yaml
""",
        encoding="utf-8",
    )

    doc, _ = load(str(main_yaml), validate=False)
    assert len(doc["questions"]) == 2
    assert doc["questions"][0]["question"] == "Intro question"
    assert doc["questions"][1]["question"] == "What is 2 + 2?"


def test_include_missing_file(tmp_path: Path):
    main_yaml = tmp_path / "main.yaml"
    main_yaml.write_text(
        """
---
- _include: nonexistent.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(QuizMLYamlSyntaxError) as exc_info:
        load(str(main_yaml), validate=False)
    assert "Included YAML file not found" in str(exc_info.value)


def test_circular_include_detected(tmp_path: Path):
    file_a = tmp_path / "a.yaml"
    file_b = tmp_path / "b.yaml"

    file_a.write_text(
        """
---
- _include: b.yaml
""",
        encoding="utf-8",
    )
    file_b.write_text(
        """
---
- _include: a.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(QuizMLYamlSyntaxError) as exc_info:
        load(str(file_a), validate=False)
    assert "Circular include detected" in str(exc_info.value)


def test_include_sampling_with_count_and_seed(tmp_path: Path):
    bank_yaml = tmp_path / "bank.yaml"
    questions_yaml = "\n".join(
        f"- type: essay\n  marks: 1\n  question: Q{i}\n  answer: A{i}"
        for i in range(10)
    )
    bank_yaml.write_text(questions_yaml, encoding="utf-8")

    main_yaml = tmp_path / "exam.yaml"
    main_yaml.write_text(
        """
---
- _include: bank.yaml
  count: 3
  seed: 42
""",
        encoding="utf-8",
    )

    doc1, _ = load(str(main_yaml), validate=False)
    doc2, _ = load(str(main_yaml), validate=False)

    assert len(doc1["questions"]) == 3
    assert len(doc2["questions"]) == 3
    # With seed: 42, sampling should be deterministic
    q_titles_1 = [q["question"] for q in doc1["questions"]]
    q_titles_2 = [q["question"] for q in doc2["questions"]]
    assert q_titles_1 == q_titles_2


def test_include_count_larger_than_pool(tmp_path: Path):
    bank_yaml = tmp_path / "bank.yaml"
    bank_yaml.write_text(
        """
- type: essay
  marks: 1
  question: Q1
  answer: A1
""",
        encoding="utf-8",
    )

    main_yaml = tmp_path / "exam.yaml"
    main_yaml.write_text(
        """
---
- _include: bank.yaml
  count: 5
""",
        encoding="utf-8",
    )

    doc, _ = load(str(main_yaml), validate=False)
    # If count > total items, return all available items without error
    assert len(doc["questions"]) == 1


def test_include_invalid_count(tmp_path: Path):
    bank_yaml = tmp_path / "bank.yaml"
    bank_yaml.write_text(
        "- type: essay\n  marks: 1\n  question: Q1\n  answer: A1\n",
        encoding="utf-8",
    )

    main_yaml = tmp_path / "exam.yaml"
    main_yaml.write_text(
        """
---
- _include: bank.yaml
  count: -2
""",
        encoding="utf-8",
    )

    with pytest.raises(QuizMLYamlSyntaxError) as exc_info:
        load(str(main_yaml), validate=False)
    assert "Include 'count' cannot be negative" in str(exc_info.value)


def test_include_with_loads_and_base_dir(tmp_path: Path):
    sub_yaml = tmp_path / "sub.yaml"
    sub_yaml.write_text(
        "- type: essay\n  marks: 1\n  question: SubQ\n  answer: SubA\n",
        encoding="utf-8",
    )

    txt = """
---
- _include: sub.yaml
"""
    doc, _ = loads(txt, validate=False, base_dir=tmp_path)
    assert len(doc["questions"]) == 1
    assert doc["questions"][0]["question"] == "SubQ"


def test_include_with_schema_validation(tmp_path: Path):
    sub_yaml = tmp_path / "valid_sub.yaml"
    sub_yaml.write_text(
        """
- type: essay
  marks: 5
  question: Valid essay question
  answer: Some model answer
""",
        encoding="utf-8",
    )

    main_yaml = tmp_path / "main.yaml"
    main_yaml.write_text(
        """
title: Exam
---
- _include: valid_sub.yaml
""",
        encoding="utf-8",
    )

    # validate=True loads default schema.json
    doc, _ = load(str(main_yaml), validate=True)
    assert len(doc["questions"]) == 1
    assert doc["questions"][0]["marks"] == 5.0

    # Now test an included file with invalid schema (e.g. ma question missing required choices)
    bad_sub_yaml = tmp_path / "bad_sub.yaml"
    bad_sub_yaml.write_text(
        """
- type: ma
  marks: 5
  question: Bad question without choices
""",
        encoding="utf-8",
    )

    bad_main_yaml = tmp_path / "bad_main.yaml"
    bad_main_yaml.write_text(
        """
---
- _include: bad_sub.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(QuizMLYamlSyntaxError) as exc_info:
        load(str(bad_main_yaml), validate=True)
    assert "Schema validation error" in str(exc_info.value)


def test_unprefixed_include_raises_error(tmp_path: Path):
    main_yaml = tmp_path / "main.yaml"
    main_yaml.write_text(
        """
---
- include: bank.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(QuizMLYamlSyntaxError) as exc_info:
        load(str(main_yaml), validate=False)
    assert "Unknown directive 'include'. Did you mean '_include'?" in str(
        exc_info.value
    )


def test_count_included_questions(tmp_path: Path):
    bank_yaml = tmp_path / "bank.yaml"
    bank_yaml.write_text(
        """
- type: essay
  question: Q1
- type: essay
  question: Q2
- type: essay
  question: Q3
""",
        encoding="utf-8",
    )

    # Without count
    item = {"_include": "bank.yaml"}
    assert count_included_questions(item, base_dir=tmp_path) == 3

    # With count
    item_sampled = {"_include": "bank.yaml", "count": 2}
    assert count_included_questions(item_sampled, base_dir=tmp_path) == 2

    # Nonexistent file fallback
    item_missing = {"_include": "nonexistent.yaml"}
    assert count_included_questions(item_missing, base_dir=tmp_path) == 1


def test_include_relative_image_paths(tmp_path: Path):
    from PIL import Image

    # Create directory structure:
    # tmp_path/
    #   exams/exam.yaml
    #   banks/physics/
    #     mechanics.yaml
    #     fig/test.png
    exams_dir = tmp_path / "exams"
    exams_dir.mkdir()
    physics_dir = tmp_path / "banks" / "physics"
    (physics_dir / "fig").mkdir(parents=True)

    img = Image.new("RGB", (10, 10), color="blue")
    img.save(str(physics_dir / "fig" / "test.png"))

    mechanics_yaml = physics_dir / "mechanics.yaml"
    mechanics_yaml.write_text(
        """
- type: essay
  marks: 5
  question: |
    See diagram:
    ![](fig/test.png)
  answer: Answer
""",
        encoding="utf-8",
    )

    exam_yaml = exams_dir / "exam.yaml"
    exam_yaml.write_text(
        """
title: Final Exam
---
- _include: ../banks/physics/mechanics.yaml
""",
        encoding="utf-8",
    )

    doc, _ = load(str(exam_yaml), validate=True)
    # Check that ../banks/physics was accumulated into _figures_path
    assert "_figures_path" in doc["header"]
    assert "../banks/physics" in doc["header"]["_figures_path"]

    # Verify Markdown image embedding finds the image and converts to base64
    from quizml.markdown.markdown import MarkdownTranscoder

    transcoder = MarkdownTranscoder(doc)
    html_dict = transcoder.get_dict(opts={"fmt": "html"})
    rendered_q = [v for k, v in html_dict.items() if "data:image/png;base64," in v]
    assert len(rendered_q) == 1


def test_include_subfile_custom_figures_path(tmp_path: Path):
    from PIL import Image

    exams_dir = tmp_path / "exams"
    exams_dir.mkdir(exist_ok=True)
    physics_dir = tmp_path / "banks" / "physics"
    assets_dir = physics_dir / "custom_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (12, 12), color="green")
    img.save(str(assets_dir / "plot.png"))

    mechanics_yaml = physics_dir / "mechanics_custom.yaml"
    mechanics_yaml.write_text(
        """
_figures_path:
  - custom_assets/
---
- type: essay
  marks: 5
  question: |
    Custom asset:
    ![](plot.png)
  answer: Answer
""",
        encoding="utf-8",
    )

    exam_yaml = exams_dir / "exam_custom.yaml"
    exam_yaml.write_text(
        """
title: Custom Exam
---
- _include: ../banks/physics/mechanics_custom.yaml
""",
        encoding="utf-8",
    )

    doc, _ = load(str(exam_yaml), validate=True)
    assert "_figures_path" in doc["header"]
    # Both the bank directory and its custom_assets directory are accumulated
    fig_paths = doc["header"]["_figures_path"]
    assert "../banks/physics" in fig_paths
    assert "../banks/physics/custom_assets" in fig_paths

    # Verify Markdown image embedding finds plot.png inside custom_assets
    from quizml.markdown.markdown import MarkdownTranscoder

    transcoder = MarkdownTranscoder(doc)
    html_dict = transcoder.get_dict(opts={"fmt": "html"})
    rendered_q = [v for k, v in html_dict.items() if "data:image/png;base64," in v]
    assert len(rendered_q) == 1

    # Verify LaTeX graphicspath contains both directories
    from quizml.cli.filelocator import locate
    from quizml.renderer import render_template

    template_path = locate.path("tcd-exam.tex.j2")
    rendered_tex = render_template(doc, template_path)
    assert "{../banks/physics/}" in rendered_tex
    assert "{../banks/physics/custom_assets/}" in rendered_tex
