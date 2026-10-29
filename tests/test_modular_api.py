"""Unit tests for the standalone modular Python APIs of QuizML."""

import io
import zipfile

import quizml
from quizml.build import BuildResult, compile_quiz, load_config, resolve_targets
from quizml.markdown import transcode, transcode_many, transcode_text
from quizml.rendering import render
from quizml.yaml import (
    QuizDocument,
    compare_quiz_files,
    format_yaml_text,
    load,
    load_schema,
    loads,
)


def test_top_level_quizml_exports():
    assert hasattr(quizml, "load")
    assert hasattr(quizml, "loads")
    assert hasattr(quizml, "transcode")
    assert hasattr(quizml, "transcode_text")
    assert hasattr(quizml, "transcode_many")
    assert hasattr(quizml, "render")
    assert hasattr(quizml, "compile_quiz")
    assert hasattr(quizml, "QuizDocument")
    assert hasattr(quizml, "BuildResult")


def test_quiz_document_dict_and_attribute_access(tmp_path):
    quiz_file = tmp_path / "exam.yaml"
    quiz_file.write_text(
        """
title: Modular Test
---
- type: tf
  marks: 2.0
  question: Is QuizML modular?
  answer: true
""",
        encoding="utf-8",
    )

    doc = load(str(quiz_file))
    assert isinstance(doc, QuizDocument)
    assert isinstance(doc, dict)
    assert doc.header["title"] == "Modular Test"
    assert doc["header"]["title"] == "Modular Test"
    assert len(doc.questions) == 1
    assert doc.questions[0]["answer"] is True
    assert doc.schema is not None
    assert "input_dir" in doc.paths


def test_standalone_transcode_text_and_many():
    # Single text to HTML with MathML
    html_out = transcode_text(
        "Compute **bold** $x^2 + y^2$.",
        format="html",
        math="mathml",
    )
    assert "<strong>bold</strong>" in html_out
    assert "<math" in html_out

    # Single text to LaTeX
    latex_out = transcode_text("Compute *italic* `code`.", format="latex")
    assert r"\textit{italic}" in latex_out
    assert r"\texttt{code}" in latex_out

    # Single text to Word OpenXML
    docx_out = transcode_text("Equation $E=mc^2$ and **strong**.", format="docx")
    assert "<m:oMath>" in str(docx_out)
    assert "<w:b/>" in str(docx_out)

    # Batch transcode_many
    batch = transcode_many(
        ["First *item*", "Second **item**"],
        format="html",
        math="passthrough",
    )
    assert "<em>item</em>" in batch["First *item*"]
    assert "<strong>item</strong>" in batch["Second **item**"]


def test_standalone_transcode_document_preserves_quiz_document():
    doc = loads(
        """
title: '*Header Title*'
---
- type: essay
  question: Explain **backpropagation**.
""",
        validate=True,
        schema=load_schema(),
    )
    transcoded = transcode(doc, format="latex")
    assert isinstance(transcoded, QuizDocument)
    assert r"\textit{Header Title}" in transcoded.header["title"]
    assert r"\textbf{backpropagation}" in transcoded.questions[0]["question"]


def test_docx_cache_key_differentiates_macro_preamble():
    doc = loads(
        """
---
- type: essay
  question: 'Vector $\\bx$.'
""",
        validate=True,
        schema=load_schema(),
    )
    from quizml.markdown import MarkdownTranscoder

    transcoder = MarkdownTranscoder(doc)
    d1 = transcoder.docx_dict(
        {"fmt": "docx", "html_pre": r"\newcommand{\bx}{\mathbf{x}}"}
    )
    d2 = transcoder.docx_dict(
        {"fmt": "docx", "html_pre": r"\newcommand{\bx}{\mathbb{R}}"}
    )
    assert str(d1["Vector $\\bx$."]) != str(d2["Vector $\\bx$."])


def test_unified_rendering_dispatch(tmp_path):
    doc = loads(
        """
title: Dispatch Test
---
- type: mc
  marks: 2.0
  question: What is 1 + 1?
  choices:
    - o: '1'
    - x: '2'
""",
        validate=True,
        schema=load_schema(),
    )
    transcoded_html = transcode(doc, format="html", math="mathml")

    # 1. Jinja template
    tpl = tmp_path / "simple.j2"
    tpl.write_text(
        "<< header.title | trim >>: << questions | length >>", encoding="utf-8"
    )
    assert render(transcoded_html, tpl) == "<p>Dispatch Test</p>: 1"

    # 2. QTI 1.2 directory dispatch
    qti_dir = quizml.FileLocator().path("qti12")
    qti_bytes = render(transcoded_html, qti_dir)
    assert isinstance(qti_bytes, bytes)
    with zipfile.ZipFile(io.BytesIO(qti_bytes)) as zf:
        assert "quiz.xml" in zf.namelist()


def test_headless_compile_quiz(tmp_path):
    quiz_file = tmp_path / "headless.yaml"
    quiz_file.write_text(
        """
title: Headless Build
---
- type: tf
  marks: 1.0
  question: Headless compile works?
  answer: true
""",
        encoding="utf-8",
    )

    stats_called = []
    result = compile_quiz(
        str(quiz_file),
        targets=["html-preview", "moodle"],
        on_stats=lambda doc, cfg: stats_called.append(doc.header["title"]),
    )

    assert isinstance(result, BuildResult)
    assert result.ok is True
    assert stats_called == ["Headless Build"]
    assert [t.name for t in result.targets] == ["html-preview", "moodle"]
    assert all(t.status == "succeeded" for t in result.targets)
    assert (tmp_path / "headless.html").is_file()
    assert (tmp_path / "headless.xml").is_file()


def test_pure_yaml_format_and_diff(tmp_path):
    raw = "- type: tf\n  question: Same question?\n  answer: true\n"
    formatted = format_yaml_text(raw)
    assert "- # <Q1>" in formatted

    f1 = tmp_path / "a.yaml"
    f2 = tmp_path / "b.yaml"
    f1.write_text(formatted, encoding="utf-8")
    f2.write_text(formatted, encoding="utf-8")

    stats = compare_quiz_files([str(f1), str(f2)])
    assert len(stats) == 1
    assert stats[0]["dups"] == [str(f2)]


def test_load_config_and_resolve_targets_headless(tmp_path):
    cfg = load_config(yaml_filename=str(tmp_path / "exam.yaml"))
    doc = loads("title: Test\n---\n[]", validate=False)
    targets = resolve_targets(cfg, doc, target_names=["html-preview"])
    assert len(targets) == 1
    assert targets[0]["name"] == "html-preview"
