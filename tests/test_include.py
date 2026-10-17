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


@pytest.mark.parametrize("directive, value", [("count", "3"), ("seed", "42")])
def test_include_rejects_sampling_directives(
    tmp_path: Path, directive: str, value: str
):
    bank_yaml = tmp_path / "bank.yaml"
    questions_yaml = "\n".join(
        f"- type: essay\n  marks: 1\n  question: Q{i}\n  answer: A{i}"
        for i in range(10)
    )
    bank_yaml.write_text(questions_yaml, encoding="utf-8")

    main_yaml = tmp_path / "exam.yaml"
    main_yaml.write_text(
        f"""
---
- _include: bank.yaml
  {directive}: {value}
""",
        encoding="utf-8",
    )

    with pytest.raises(QuizMLYamlSyntaxError, match="quizml sample"):
        load(str(main_yaml), validate=False)


def test_include_loads_all_questions_in_source_order(tmp_path: Path):
    bank_yaml = tmp_path / "bank.yaml"
    bank_yaml.write_text(
        """
- type: essay
  marks: 1
  question: Q1
  answer: A1
- type: essay
  marks: 1
  question: Q2
  answer: A2
""",
        encoding="utf-8",
    )

    main_yaml = tmp_path / "exam.yaml"
    main_yaml.write_text(
        """
---
- _include: bank.yaml
""",
        encoding="utf-8",
    )

    doc, _ = load(str(main_yaml), validate=False)
    assert [q["question"] for q in doc["questions"]] == ["Q1", "Q2"]


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

    # Included-file errors should point to the included source.
    bad_sub_yaml = tmp_path / "bad_sub.yaml"
    bad_sub_yaml.write_text(
        """
- type: tf
  marks: 5
  question: Bad true false question
  answer: maybe
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
    message = str(exc_info.value)
    assert "Schema validation error" in message
    assert str(bad_sub_yaml) in message
    assert "line ~5" in message


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

    # Count every question in the include.
    item = {"_include": "bank.yaml"}
    assert count_included_questions(item, base_dir=tmp_path) == 3

    # Nonexistent file fallback
    item_missing = {"_include": "nonexistent.yaml"}
    assert count_included_questions(item_missing, base_dir=tmp_path) == 1


def test_count_and_loading_share_included_file_document_rules(tmp_path: Path):
    bank_yaml = tmp_path / "bank.yaml"
    bank_yaml.write_text(
        "title: Bank\n---\n- type: essay\n  question: Q1\n---\nextra: document\n",
        encoding="utf-8",
    )
    include = {"_include": "bank.yaml"}

    # Counting remains best-effort for format comments, while compilation
    # rejects the same invalid include using the shared parser.
    assert count_included_questions(include, base_dir=tmp_path) == 1

    main_yaml = tmp_path / "main.yaml"
    main_yaml.write_text("---\n- _include: bank.yaml\n", encoding="utf-8")
    with pytest.raises(
        QuizMLYamlSyntaxError, match="cannot have more than 2 documents"
    ):
        load(str(main_yaml), validate=False)


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
    # Included asset directories are carried separately from user metadata.
    assert "_figures_path" not in doc["header"]
    assert "../banks/physics" in doc["paths"]["figure_dirs"]

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
    assert "_figures_path" not in doc["header"]
    # Both the bank directory and its custom_assets directory are accumulated
    fig_paths = doc["paths"]["figure_dirs"]
    assert "../banks/physics" in fig_paths
    assert "../banks/physics/custom_assets" in fig_paths

    # Verify Markdown image embedding finds plot.png inside custom_assets
    from quizml.markdown.markdown import MarkdownTranscoder

    transcoder = MarkdownTranscoder(doc)
    html_dict = transcoder.get_dict(opts={"fmt": "html"})
    rendered_q = [v for k, v in html_dict.items() if "data:image/png;base64," in v]
    assert len(rendered_q) == 1

    # Verify LaTeX graphicspath contains both directories
    from quizml.cli.filelocator import FileLocator
    from quizml.renderer import render_template

    locator = FileLocator()
    template_path = locator.path("tcd-exam.tex.j2")
    rendered_tex = render_template(doc, template_path, locator.dirlist)
    assert "{../banks/physics/}" in rendered_tex
    assert "{../banks/physics/custom_assets/}" in rendered_tex


def test_include_rejects_unknown_keys(tmp_path: Path):
    bank = tmp_path / "bank.yaml"
    bank.write_text("- type: essay\n  question: Q1\n", encoding="utf-8")
    main = tmp_path / "main.yaml"
    main.write_text("---\n- _include: bank.yaml\n  extra_key: 1\n", encoding="utf-8")

    with pytest.raises(QuizMLYamlSyntaxError, match="Unknown directive"):
        load(str(main), validate=False)


def test_loads_converts_scalar_strings_to_plain_str():
    doc, _ = loads(
        "title: Plain\n---\n- type: essay\n  question: Hello\n", validate=False
    )
    assert type(doc["header"]["title"]) is str
    assert type(doc["questions"][0]["type"]) is str


def test_question_id_and_title_and_duplicate_id_detection():
    valid_yaml = """
title: Exam
---
- id: q-backprop
  title: Backpropagation
  type: essay
  marks: 10
  question: Derive backpropagation.
- id: q-cnn
  title: CNN Receptive Field
  type: num
  marks: 5
  question: Compute receptive field.
  answer: 7
"""
    doc, _ = loads(valid_yaml, validate=True)
    assert doc["questions"][0]["id"] == "q-backprop"
    assert doc["questions"][0]["title"] == "Backpropagation"

    dup_yaml = """
---
- id: dup-1
  type: essay
  question: First
- id: dup-1
  type: essay
  question: Second
"""
    with pytest.raises(QuizMLYamlSyntaxError, match="Duplicate question id 'dup-1'"):
        loads(dup_yaml, validate=True)


def test_include_select_by_id_and_index(tmp_path: Path):
    from types import SimpleNamespace

    from quizml.cli.sample import run_sample

    bank = tmp_path / "bank.yaml"
    bank.write_text(
        """
- id: q-alpha
  title: Alpha
  type: essay
  question: First question
- id: q-beta
  title: Beta
  type: essay
  question: Second question
- id: q-gamma
  title: Gamma
  type: essay
  question: Third question
""",
        encoding="utf-8",
    )

    exam = tmp_path / "exam.yaml"
    exam.write_text(
        """
---
- _include: bank.yaml
  select:
    - q-gamma
    - 1
""",
        encoding="utf-8",
    )

    doc, _ = load(str(exam), validate=True)
    assert [q["id"] for q in doc["questions"]] == ["q-gamma", "q-alpha"]
    assert count_included_questions(
        {"_include": "bank.yaml", "select": ["q-gamma", 1]}, base_dir=tmp_path
    ) == 2

    # Also verify quizml sample expands select:
    sampled = tmp_path / "sampled.yaml"
    run_sample(
        SimpleNamespace(
            file=str(exam), output=str(sampled), seed=None, quiet=True
        )
    )
    sampled_doc, _ = load(str(sampled), validate=True)
    assert [q["id"] for q in sampled_doc["questions"]] == ["q-gamma", "q-alpha"]

    # Missing id raises a helpful error
    bad_exam = tmp_path / "bad_exam.yaml"
    bad_exam.write_text(
        "---\n- _include: bank.yaml\n  select: [nonexistent-id]\n",
        encoding="utf-8",
    )
    with pytest.raises(QuizMLYamlSyntaxError, match="nonexistent-id"):
        load(str(bad_exam), validate=True)

