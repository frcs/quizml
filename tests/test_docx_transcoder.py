"""Unit tests for dedicated Word OpenXML Markdown Transcoder."""

import mistletoe as mt
import pytest

from quizml.markdown.docx import QuizMLYamlDocxRenderer
from quizml.markdown.markdown import MarkdownTranscoder, _quizml_token_scope
from quizml.yaml import load


@pytest.fixture(autouse=True)
def setup_tokens():
    with _quizml_token_scope():
        yield


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


def test_docx_line_break_handling():
    """Verifies that soft line breaks within paragraphs become spaces (like LaTeX),
    while hard line breaks (2 spaces or backslash) become <w:br/>."""
    soft_md = "First line\nsecond line\nthird line."
    doc = mt.Document(soft_md)
    renderer = QuizMLYamlDocxRenderer()
    with renderer:
        xml = renderer.render(doc)

    assert "<w:br/>" not in xml
    assert 'xml:space="preserve"> </w:t>' in xml
    assert "First line" in xml
    assert "second line" in xml
    assert "third line." in xml

    hard_md = "First line  \nsecond line\\\nthird line."
    doc_hard = mt.Document(hard_md)
    with renderer:
        xml_hard = renderer.render(doc_hard)

    assert "<w:br/>" in xml_hard


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
    quiz_file = tmp_path / "quiz.yaml"
    quiz_file.write_text(yaml_text, encoding="utf-8")
    doc_dict = load(str(quiz_file))
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


def test_docx_block_code_is_valid_xml():
    """Verifies fenced code blocks emit well-formed OpenXML."""
    import xml.etree.ElementTree as ET

    doc = mt.Document("```python\nx = 1\ny = 2\n```")
    with QuizMLYamlDocxRenderer() as renderer:
        xml = renderer.render(doc)

    wrapped = (
        '<root xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"{xml}</root>"
    )
    root = ET.fromstring(wrapped)
    assert (
        root.find(
            ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pBdr"
        )
        is not None
    )


def test_docx_image_width_linewidth_percent_and_invalid(tmp_path):
    """Verifies \\linewidth and % widths scale against 6.5in and invalid widths error."""
    from quizml.exceptions import MarkdownAttributeError

    img_file = tmp_path / "fig.png"
    img_file.write_bytes(b"dummy")

    with QuizMLYamlDocxRenderer(base_dir=str(tmp_path)) as renderer:
        xml_lw = renderer.render(mt.Document("![alt](fig.png){width=0.5\\linewidth}"))
        xml_pct = renderer.render(mt.Document("![alt](fig.png){width=50%}"))

    assert ":3.25-->" in xml_lw
    assert ":3.25-->" in xml_pct

    with pytest.raises(MarkdownAttributeError):
        with QuizMLYamlDocxRenderer(base_dir=str(tmp_path)) as renderer:
            renderer.render(mt.Document("![alt](fig.png){width=auto}"))


def test_docx_windows_image_marker_and_deterministic_svg_ids(tmp_path):
    """Verifies Windows-style colons in image markers and deterministic SVG docPr ids."""
    import io
    import zipfile
    from pathlib import Path

    from quizml.rendering.docx import _clean_docx_str, render_docx
    from quizml.yaml import loads

    # Windows-style drive letter path must not raise ValueError
    cleaned = _clean_docx_str(r"<!--QUIZML_IMG:C:\Users\alice\fig.png:4.0-->")
    assert cleaned == ""

    svg_file = tmp_path / "diagram.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50" viewBox="0 0 100 50">'
        '<rect width="100" height="50" fill="blue"/></svg>',
        encoding="utf-8",
    )
    doc_dict = loads(
        f"""
title: 'Deterministic SVG'
---
- type: mc
  marks: 2.0
  question: |
    ![]({svg_file}){{width=3in}}
  choices:
  - x: 'A'
  - o: 'B'
""",
        validate=False,
    )
    transcoded = MarkdownTranscoder(doc_dict).transcode_target({"fmt": "docx"})
    tpl_path = (
        Path(__file__).parent.parent / "src" / "quizml" / "templates" / "tcd-exam.docx"
    )
    ctx = {"header": transcoded["header"], "questions": transcoded["questions"]}
    b1 = render_docx(ctx, tpl_path)
    b2 = render_docx(ctx, tpl_path)
    with zipfile.ZipFile(io.BytesIO(b1)) as z1, zipfile.ZipFile(io.BytesIO(b2)) as z2:
        assert z1.read("word/document.xml") == z2.read("word/document.xml")
