"""Tests for IMS QTI 1.2 package generation, XML schema validity, and metadata mapping."""

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from quizml.cli.compile import compile_target
from quizml.cli.config import get_config, get_target_list
from quizml.loader import load, loads
from quizml.markdown.markdown import MarkdownTranscoder
from quizml.qti_renderer import (
    _derive_duration_from_examtime,
    prepare_qti_context,
    render_qti,
)


def test_derive_duration_from_examtime():
    assert _derive_duration_from_examtime("09:30-11:30") == 120
    assert _derive_duration_from_examtime("14:00 - 15:30") == 90
    assert _derive_duration_from_examtime("invalid") is None


def test_prepare_qti_context_fallbacks_and_result_release():
    context = {
        "header": {
            "modulename": "Deep Learning",
            "examtime": "09:30-11:30",
            "instructions": "Answer all questions.",
            "_qti": {
                "due_at": "2025-05-20 17:00",
                "release_score": "after_submission",
                "release_solutions": "after_due_date",
                "shuffle_answers": True,
                "access_code": "Secret2025",
            },
        },
        "questions": [],
    }
    qti_ctx = prepare_qti_context(context)
    qti = qti_ctx["qti"]

    assert qti["title"] == "Deep Learning"
    assert qti["time_limit"] == 120
    assert qti["description"] == "Answer all questions."
    assert qti["release_score"] == "after_submission"
    assert qti["release_solutions"] == "after_due_date"
    assert qti["show_correct_answers_at"] == "2025-05-20 17:00"
    assert qti["shuffle_answers"] is True
    assert qti["access_code"] == "Secret2025"


def test_qti_render_produces_valid_zip_and_xml(tmp_path):
    yaml_text = r"""
title: "Test Exam"
instructions: "Read carefully."
_qti:
  time_limit: 60
  allowed_attempts: 2
  scoring_policy: keep_highest
  shuffle_answers: true
  due_at: "2025-06-01 12:00"
  release_score: after_submission
  release_solutions: after_due_date
---
- type: mc
  title: "Single Choice Q1"
  marks: 2.5
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
  title: "Multi Choice Q2"
  marks: 4.0
  question: "Select prime numbers:"
  choices:
  - x: "2"
  - x: "3"
  - o: "4"
  - x: "5"

- type: tf
  marks: 1.0
  question: "The Earth is round."
  answer: true

- type: num
  marks: 2.0
  question: "Enter the value of $\\pi$ to two decimals:"
  answer: 3.14
  tolerance: 0.01

- type: fill
  marks: 2.0
  question: "The capital of France is ___."
  answers:
  - "Paris"
  - "paris"

- type: mfill
  marks: 4.0
  question: "Roses are [color1] and violets are [color2]."
  answers:
    color1: ["red", "Red"]
    color2: ["blue", "Blue"]

- type: essay
  marks: 5.0
  question: "Discuss the architecture of Transformers."
  answer: "Model answer: Self-attention mechanisms allow..."
  comments: "Internal lecturer grading rubric: 2.5 pts for attention, 2.5 pts for feedforward."

- type: matching
  marks: 3.0
  question: "Match languages to their paradigms:"
  choices:
  - A: "Haskell"
    B: "Functional"
  - A: "C"
    B: "Procedural"

- type: ordering
  marks: 2.0
  question: "Order the numbers from low to high:"
  choices:
  - "One"
  - "Two"
  - "Three"
"""
    yaml_doc, _ = loads(yaml_text)

    transcoder = MarkdownTranscoder(yaml_doc)
    yaml_transcoded = transcoder.transcode_target({"fmt": "html-mathml"})

    pkg_template_dir = (
        Path(__file__).parent.parent / "src" / "quizml" / "templates" / "qti12"
    )
    zip_bytes = render_qti(yaml_transcoded, pkg_template_dir)

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0

    # Verify ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = zf.namelist()
        assert "quiz.xml" in names
        assert "imsmanifest.xml" in names
        assert "assessment_meta.xml" in names

        # Verify XML validity with ElementTree
        manifest_root = ET.fromstring(zf.read("imsmanifest.xml"))
        assert manifest_root.tag.endswith("manifest")

        meta_root = ET.fromstring(zf.read("assessment_meta.xml"))
        assert meta_root.tag.endswith("quiz")
        title_elem = meta_root.find("{http://canvas.instructure.com/xsd/cccv1p0}title")
        assert title_elem is not None and title_elem.text == "Test Exam"

        quiz_root = ET.fromstring(zf.read("quiz.xml"))
        assert quiz_root.tag.endswith("questestinterop")

        # Verify items in quiz.xml
        items = quiz_root.findall(
            ".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}item"
        )
        assert len(items) == 9

        # Verify Q1 (MC) has shuffle="No" because shuffle: false was specified
        mc_item = items[0]
        render_choice = mc_item.find(
            ".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}render_choice"
        )
        assert render_choice is not None
        assert render_choice.attrib.get("shuffle") == "No"

        # Verify feedback elements in Q1
        feedbacks = mc_item.findall(
            "{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}itemfeedback"
        )
        fb_idents = [f.attrib.get("ident") for f in feedbacks]
        assert "general_fb" in fb_idents
        assert "correct_fb" in fb_idents
        assert "incorrect_fb" in fb_idents

        # Verify essay rubric in Q7
        essay_item = items[6]
        essay_fb = essay_item.findall(
            "{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}itemfeedback"
        )
        essay_fb_idents = [f.attrib.get("ident") for f in essay_fb]
        assert "rubric" in essay_fb_idents


def test_compile_qti_target_via_pipeline(tmp_path):
    import argparse

    quiz_file = tmp_path / "sample_quiz.yaml"
    quiz_file.write_text(
        """
title: "Pipeline Test Quiz"
_qti:
  time_limit: 45
---
- type: mc
  question: "Is this working?"
  choices:
  - o: "Yes"
  - x: "No"
""",
        encoding="utf-8",
    )

    args = argparse.Namespace(
        config=None, target=["qti"], yaml_filename=str(quiz_file)
    )
    config = get_config(args)
    yaml_doc, _ = load(str(quiz_file), validate=False)

    targets = get_target_list(args, config, yaml_doc)
    assert len(targets) == 1
    target = targets[0]
    assert target["name"] == "qti"
    assert target["out"].endswith(".qti.zip")

    transcoder = MarkdownTranscoder(yaml_doc, base_dir=str(tmp_path))
    compile_target(target, transcoder)

    out_zip = Path(target["out"])
    assert out_zip.exists()

    with zipfile.ZipFile(out_zip, "r") as zf:
        assert "quiz.xml" in zf.namelist()
        assert "imsmanifest.xml" in zf.namelist()
        assert "assessment_meta.xml" in zf.namelist()


def test_qti_export_with_image_and_backward_compatibility(tmp_path):
    # Test with examples/quiz1.yaml which contains an SVG image reference and math equations
    import argparse

    from quizml.loader import load

    quiz_path = Path(__file__).parent.parent / "examples" / "quiz1.yaml"
    yaml_doc, _ = load(str(quiz_path), validate=True)

    args = argparse.Namespace(
        config=None, target=["qti"], yaml_filename=str(quiz_path)
    )
    config = get_config(args)
    targets = get_target_list(args, config, yaml_doc)
    assert len(targets) == 1
    target = targets[0]
    # Redirect output to tmp_path
    target["out"] = str(tmp_path / "quiz1.qti.zip")

    transcoder = MarkdownTranscoder(yaml_doc, base_dir=str(quiz_path.parent))
    compile_target(target, transcoder)

    out_zip = Path(target["out"])
    assert out_zip.exists()

    with zipfile.ZipFile(out_zip, "r") as zf:
        quiz_xml = zf.read("quiz.xml").decode("utf-8")
        assert "<math" in quiz_xml  # MathML rendered
        assert "images/img_" in quiz_xml  # Image bundled into package
        assert any(n.startswith("images/img_") for n in zf.namelist())
        root = ET.fromstring(quiz_xml)
        items = root.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}item")
        assert len(items) == 2


def test_qti_part_section_support(tmp_path):
    yaml_text = r"""
title: "Exam with Sections"
---
- type: part
  title: "Section 1: Fundamentals"
  question: "Answer all questions in this part."
- type: mc
  question: "What is 1 + 1?"
  choices:
  - o: "2"
  - x: "3"
- type: part
  title: "Section 2: Advanced"
- type: tf
  question: "Calculus is fun."
  answer: true
"""
    yaml_doc, _ = loads(yaml_text)

    transcoder = MarkdownTranscoder(yaml_doc)
    yaml_transcoded = transcoder.transcode_target({"fmt": "html-mathml"})

    pkg_template_dir = (
        Path(__file__).parent.parent / "src" / "quizml" / "templates" / "qti12"
    )
    zip_bytes = render_qti(yaml_transcoded, pkg_template_dir)

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        quiz_xml = zf.read("quiz.xml")
        root = ET.fromstring(quiz_xml)
        sections = root.findall(
            ".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}section"
        )
        # Should have root_section, section_1, and section_3
        assert len(sections) >= 2
