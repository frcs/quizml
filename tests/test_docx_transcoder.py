"""Unit tests for dedicated Word OpenXML Markdown Transcoder."""

import mistletoe as mt
import pytest

from quizml.quizmlyaml import loads
from quizml.transcoder.docx import QuizMLYamlDocxRenderer
from quizml.transcoder.transcoder import MarkdownTranscoder, _setup_mistletoe_tokens


@pytest.fixture(autouse=True)
def setup_tokens():
    _setup_mistletoe_tokens()


def test_docx_inline_formatting():
    """Verifies bold, italic, code, and strikethrough OpenXML run generation."""
    md = "Normal **bold** *italic* ***bold-italic*** `code_var` ~~strike~~"
    doc = mt.Document(md)
    renderer = QuizMLYamlDocxRenderer()
    with renderer:
        xml = renderer.render(doc)

    assert "<w:b/>" in xml
    assert "<w:i/>" in xml
    assert "<w:strike/>" in xml
    assert "Consolas" in xml
    assert "bold" in xml
    assert "italic" in xml


def test_docx_table_rendering():
    """Verifies markdown table conversion into Word OpenXML <w:tbl>."""
    md = """
| Metric | Class 0 | Class 1 |
|:-------|--------:|--------:|
| Recall |   95.0% |   82.5% |
"""
    doc = mt.Document(md)
    renderer = QuizMLYamlDocxRenderer()
    with renderer:
        xml = renderer.render(doc)

    assert "<w:tbl>" in xml
    assert "<w:tblHeader/>" in xml
    assert "<w:gridCol/>" in xml
    assert "Metric" in xml
    assert "95.0%" in xml
    assert "82.5%" in xml


def test_docx_math_rendering():
    """Verifies inline and display LaTeX math conversion into native Word OMML (<m:oMath>)."""
    md = """
We know that $E=mc^2$ holds universally.

$$
\\int_0^1 x^2 dx = \\frac{1}{3}
$$
"""
    doc = mt.Document(md)
    renderer = QuizMLYamlDocxRenderer()
    with renderer:
        xml = renderer.render(doc)

    assert "<m:oMath>" in xml
    assert "<m:oMathPara>" in xml
    assert "E" in xml
    assert "<m:t>m</m:t>" in xml
    assert "<m:t>c</m:t>" in xml


def test_docx_image_marker_generation(tmp_path):
    """Verifies image and ImageWithWidth conversion into image markers."""
    img_file = tmp_path / "plot.png"
    img_file.write_bytes(b"dummy")

    md = f"![ROC Curve]({img_file}){{ width=20em }}"
    doc = mt.Document(md)
    renderer = QuizMLYamlDocxRenderer(base_dir=str(tmp_path))
    with renderer:
        xml = renderer.render(doc)

    assert "<!--QUIZML_IMG:" in xml
    assert str(img_file) in xml


def test_markdown_transcoder_docx_target(tmp_path):
    """Verifies full MarkdownTranscoder integration with docx format target."""
    from quizml.quizmlyaml.schema import load_schema

    yaml_text = """
title: 'Physics Test'
modulecode: 'PHYS101'
---
- type: mc
  marks: 2.0
  question: |
    Calculate the energy for **mass** $m$:
    $$
    E = mc^2
    $$
  choices:
  - o: '$m = 0$'
  - x: 'Energy is $E$'
"""
    doc_dict, _ = loads(yaml_text, schema=load_schema())
    transcoder = MarkdownTranscoder(doc_dict)
    target = {"fmt": "docx"}
    transcoded = transcoder.transcode_target(target)

    q = transcoded["questions"][0]
    # Question statement should have OMML display math and bold
    assert "<m:oMathPara>" in str(q["question"])
    assert "<w:b/>" in str(q["question"])

    # Choices should have OMML inline math
    assert "<m:oMath>" in str(q["choices"][0]["o"])
    assert "<m:oMath>" in str(q["choices"][1]["x"])


def test_docx_alignat_and_multiline_math():
    """Verifies alignat and multiline alignment equations convert to native Word OMML matrices."""
    md = r"""
\begin{alignat*}{3}
& {\frac {\partial {\mathbf{a}}^{\top }{\mathbf {w}}}{\partial {\mathbf{w}}}} &&= {\mathbf {a}} &&
\\ & {\frac {\partial {\mathbf {b}}^{\top }{\mathbf {A}}{\mathbf {w}}}{\partial {\mathbf {w}}}} && = {\mathbf {A}}^{\top }{\mathbf {b}}
&& \\ & {\frac {\partial {\mathbf {w}}^{\top }{\mathbf {A}}{\mathbf{w}}}{\partial {\mathbf {w}}}} && = ({\mathbf {A}}+{\mathbf {A}}^{\top }){\mathbf {w}} && \text{~~~~(or $2\mathbf{A}\mathbf{w}$ if $A$ symmetric)} \\ & \frac
{\partial {\mathbf {w}}^{\top }{\mathbf {w}}}{\partial {\mathbf {w}}} && =
2{\mathbf {w}} && \\ & {\frac {\partial \;{\mathbf {a}}^{\top }{\mathbf {w}}{\mathbf {w}}^{\top }{\mathbf {b}}}{\partial \;{\mathbf {w}}}} &&
= ({\mathbf {a}}{\mathbf {b}}^{\top }+{\mathbf {b}}{\mathbf {a}}^{\top }){\mathbf {w}} && \\
\end{alignat*}
"""
    doc = mt.Document(md)
    renderer = QuizMLYamlDocxRenderer()
    with renderer:
        xml = renderer.render(doc)

    assert "<m:oMathPara>" in xml
    assert "<m:m>" in xml  # Word native matrix/alignment
    assert "<m:mPr>" in xml  # Column alignment properties
    assert '<m:mcJc m:val="right"/>' in xml  # Right-aligned LHS
    assert '<m:mcJc m:val="left"/>' in xml  # Left-aligned RHS and annotations
    assert xml.count("<m:mr>") == 5  # 5 rows
    assert "<m:f>" in xml  # Fractions
    assert "symmetric" in xml
    assert "~~~~" not in xml  # Spurious tildes replaced with spaces
    assert r"\begin{" not in xml  # No raw LaTeX fallback
    assert r"\mathbf{" not in xml
