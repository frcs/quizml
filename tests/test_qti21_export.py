"""Tests for IMS QTI 2.1 package generation, XML schema validity, and Blackboard Ultra compatibility."""

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from quizml.builder.config import load_config, resolve_targets
from quizml.builder.scheduler import compile_render_target
from quizml.quizmlyaml.parser import parse_yaml_docs
from quizml.renderer.qti import render_qti
from quizml.transcoder import MarkdownTranscoder


def test_qti21_render_produces_valid_zip_and_xml():
    yaml_text = r"""
title: "Sample QTI 2.1 Exam"
instructions: "Answer all questions."
_qti:
  time_limit: 90
  shuffle_answers: true
---
- type: mc
  title: "Single Choice"
  marks: 2.5
  question: "What is $2 + 2$?"
  shuffle: false
  feedback: "Basic addition."
  feedback_correct: "Correct!"
  feedback_incorrect: "Incorrect."
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
  marks: 1.0
  question: "The Earth is round."
  answer: true

- type: num
  marks: 2.0
  question: 'Enter the value of $\pi$:'
  answer: 3.14

- type: fill
  marks: 2.0
  question: "The capital of France is ___."
  answers:
  - "Paris"
  - "paris"

- type: essay
  marks: 5.0
  question: "Explain gradient descent."
  answer: "Model answer..."

- type: matching
  marks: 3.0
  question: "Match languages to paradigms:"
  choices:
  - A: "Haskell"
    B: "Functional"
  - A: "C"
    B: "Procedural"

- type: ordering
  marks: 2.0
  question: "Order the numbers:"
  choices:
  - "First"
  - "Second"
  - "Third"
"""
    header, questions = parse_yaml_docs(yaml_text)
    yaml_doc = {"header": header, "questions": questions}

    transcoder = MarkdownTranscoder(yaml_doc)
    yaml_transcoded = transcoder.transcode_target({"fmt": "html-mathml"})

    pkg_template_dir = (
        Path(__file__).parent.parent / "src" / "quizml" / "templates" / "qti21"
    )
    zip_bytes = render_qti(yaml_transcoded, pkg_template_dir)

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = zf.namelist()
        assert "imsmanifest.xml" in names
        assert "assessment.xml" in names

        # Verify all 8 items are present
        for i in range(1, 9):
            assert f"items/item_{i}.xml" in names

        # 1. Verify imsmanifest.xml
        manifest_raw = zf.read("imsmanifest.xml")
        manifest_root = ET.fromstring(manifest_raw)
        assert manifest_root.tag.endswith("manifest")

        resources = manifest_root.findall(
            ".//{http://www.imsglobal.org/xsd/imscp_v1p1}resource"
        )
        # 1 test resource + 8 item resources
        assert len(resources) == 9

        # Ensure imsqti_item_xmlv2p1 type is used for all items
        item_res = [
            r for r in resources if r.attrib.get("type") == "imsqti_item_xmlv2p1"
        ]
        assert len(item_res) == 8

        test_res = [
            r for r in resources if r.attrib.get("type") == "imsqti_test_xmlv2p1"
        ]
        assert len(test_res) == 1

        # 2. Verify assessment.xml
        assessment_raw = zf.read("assessment.xml")
        assessment_root = ET.fromstring(assessment_raw)
        assert assessment_root.tag.endswith("assessmentTest")
        item_refs = assessment_root.findall(
            ".//{http://www.imsglobal.org/xsd/imsqti_v2p1}assessmentItemRef"
        )
        assert len(item_refs) == 8

        # 3. Verify item 1 (MC)
        q1_raw = zf.read("items/item_1.xml")
        q1_root = ET.fromstring(q1_raw)
        assert q1_root.tag.endswith("assessmentItem")
        choice_interaction = q1_root.find(
            ".//{http://www.imsglobal.org/xsd/imsqti_v2p1}choiceInteraction"
        )
        assert choice_interaction is not None
        assert choice_interaction.attrib.get("maxChoices") == "1"
        assert (
            choice_interaction.attrib.get("shuffle") == "false"
        )  # Explicitly set false in question

        # Correct response is choice_1 ("4")
        correct_val = q1_root.find(
            ".//{http://www.imsglobal.org/xsd/imsqti_v2p1}correctResponse/{http://www.imsglobal.org/xsd/imsqti_v2p1}value"
        )
        assert correct_val is not None
        assert correct_val.text == "choice_1"

        # 4. Verify item 2 (MA)
        q2_raw = zf.read("items/item_2.xml")
        q2_root = ET.fromstring(q2_raw)
        ma_interaction = q2_root.find(
            ".//{http://www.imsglobal.org/xsd/imsqti_v2p1}choiceInteraction"
        )
        assert ma_interaction is not None
        assert (
            ma_interaction.attrib.get("maxChoices") == "0"
        )  # Unlimited choices for MA
        correct_vals = [
            v.text
            for v in q2_root.findall(
                ".//{http://www.imsglobal.org/xsd/imsqti_v2p1}correctResponse/{http://www.imsglobal.org/xsd/imsqti_v2p1}value"
            )
        ]
        assert correct_vals == [
            "choice_0",
            "choice_1",
            "choice_3",
        ]  # 2, 3, 5 are primes

        # 5. Verify item 3 (TF)
        q3_raw = zf.read("items/item_3.xml")
        q3_root = ET.fromstring(q3_raw)
        tf_interaction = q3_root.find(
            ".//{http://www.imsglobal.org/xsd/imsqti_v2p1}choiceInteraction"
        )
        assert tf_interaction is not None
        assert tf_interaction.attrib.get("maxChoices") == "1"
        tf_val = q3_root.find(
            ".//{http://www.imsglobal.org/xsd/imsqti_v2p1}correctResponse/{http://www.imsglobal.org/xsd/imsqti_v2p1}value"
        )
        assert tf_val is not None and tf_val.text == "true"

        # 6. Verify item 6 (Essay)
        q6_raw = zf.read("items/item_6.xml")
        q6_root = ET.fromstring(q6_raw)
        essay_interaction = q6_root.find(
            ".//{http://www.imsglobal.org/xsd/imsqti_v2p1}extendedTextInteraction"
        )
        assert essay_interaction is not None


def test_compile_qti21_target_via_pipeline(tmp_path):
    quiz_file = tmp_path / "sample_qti21_quiz.yaml"
    quiz_file.write_text(
        """
title: "Pipeline Test Quiz QTI 2.1"
_qti:
  time_limit: 45
---
- type: mc
  question: "Is this QTI 2.1?"
  choices:
  - x: "Yes"
  - o: "No"
""",
        encoding="utf-8",
    )

    config = load_config()
    header, questions = parse_yaml_docs(
        quiz_file.read_text(encoding="utf-8"), str(quiz_file)
    )
    yaml_doc = {"header": header, "questions": questions}

    targets = resolve_targets(
        config,
        yaml_doc,
        requested_targets=["qti21"],
        yaml_filename=str(quiz_file),
    )
    assert len(targets) == 1
    target = targets[0]
    assert target["name"] == "qti21"
    assert target["out"].endswith(".qti21.zip")

    transcoder = MarkdownTranscoder(yaml_doc, base_dir=str(tmp_path))
    success, err = compile_render_target(target, transcoder)
    assert success is True, f"Compilation failed: {err}"

    out_zip = Path(target["out"])
    assert out_zip.exists()

    with zipfile.ZipFile(out_zip, "r") as zf:
        assert "imsmanifest.xml" in zf.namelist()
        assert "assessment.xml" in zf.namelist()
        assert "items/item_1.xml" in zf.namelist()


def test_qti21_export_with_image_and_html_tables(tmp_path):
    # Test with examples/quiz1.yaml which contains SVG image and Math
    from quizml.quizmlyaml import load

    quiz_path = Path(__file__).parent.parent / "examples" / "quiz1.yaml"
    yaml_doc, _ = load(str(quiz_path), validate=True)

    config = load_config()
    targets = resolve_targets(
        config,
        yaml_doc,
        requested_targets=["qti21"],
        yaml_filename=str(quiz_path),
    )
    assert len(targets) == 1
    target = targets[0]
    target["out"] = str(tmp_path / "quiz1.qti21.zip")

    transcoder = MarkdownTranscoder(yaml_doc, base_dir=str(quiz_path.parent))
    success, err = compile_render_target(target, transcoder)
    assert success is True, f"Failed: {err}"

    out_zip = Path(target["out"])
    assert out_zip.exists()

    with zipfile.ZipFile(out_zip, "r") as zf:
        names = zf.namelist()
        assert "items/item_1.xml" in names
        assert "items/item_2.xml" in names

        # Check item 1 has MathML
        q1_xml = zf.read("items/item_1.xml").decode("utf-8")
        assert "<math" in q1_xml
        # Choice 3 (1x1) is correct
        assert "<value>choice_3</value>" in q1_xml

        # Check item 2 renders image with relative package root path
        q2_xml = zf.read("items/item_2.xml").decode("utf-8")
        assert 'src="../img_' in q2_xml
        assert any(n.startswith("img_") for n in names)

        # Check imsmanifest.xml declares ccres webcontent and item dependency
        manifest_xml = zf.read("imsmanifest.xml").decode("utf-8")
        assert "ccres00001" in manifest_xml



def test_qti21_table_and_media_cleaning():
    from quizml.renderer.qti import _process_qti_html

    html_with_table_and_data_uri = (
        '<div class="confmat">'
        '<table style="padding: 0.25em; border-collapse: collapse;">'
        '<thead><tr><th style="background: silver;">Header</th></tr></thead>'
        '<tbody><tr><td style="padding: 4px;">Cell</td></tr></tbody>'
        "</table>"
        "</div>"
        '<p><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" width="10.0" height="10.0"/></p>'
    )
    media_store = {}
    cleaned, media = _process_qti_html(
        html_with_table_and_data_uri, media_store, qti_version="2.1"
    )

    # Tables should have divs and thead/tbody unwrapped, and inline styles stripped
    assert "<div" not in cleaned
    assert "<thead" not in cleaned
    assert "<tbody" not in cleaned
    assert "background: silver" not in cleaned
    assert '<table border="1"' in cleaned
    assert "<th>Header</th>" in cleaned
    assert "<td>Cell</td>" in cleaned

    # QTI 2.1 rewrites <img> to point to relative package root "../img_xxxx.png"
    assert '<img' in cleaned
    assert 'src="../img_' in cleaned
    assert 'width="10"' in cleaned
    assert 'height="10"' in cleaned
    assert len(media) == 1
    assert media[0] in media_store
    assert len(media_store[media[0]]) > 0

    # QTI 1.2 keeps <img> with external image paths
    media_store_12 = {}
    cleaned_12, _ = _process_qti_html(
        html_with_table_and_data_uri, media_store_12, qti_version="1.2"
    )
    assert '<img' in cleaned_12
    assert 'src="images/img_' in cleaned_12
    assert 'width="10"' in cleaned_12
