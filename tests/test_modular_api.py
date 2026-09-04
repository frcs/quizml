"""Unit tests for QuizML's modular Python API and --ingest CLI feature."""

import io
import json
import sys
from pathlib import Path

import quizml
from quizml import builder, tools
from quizml.cli.cli import main


def test_top_level_exports():
    """Verify clean top-level module and symbol exports."""
    assert hasattr(quizml, "load")
    assert hasattr(quizml, "loads")
    assert hasattr(quizml, "transcode")
    assert hasattr(quizml, "render")
    assert hasattr(quizml, "compile_quiz")
    assert hasattr(quizml, "TargetResult")
    assert hasattr(quizml, "quizmlyaml")
    assert hasattr(quizml, "transcoder")
    assert hasattr(quizml, "renderer")
    assert hasattr(quizml, "builder")
    assert hasattr(quizml, "tools")


def test_modular_pipeline_flow(tmp_path: Path):
    """Test step-by-step modular compilation pipeline."""
    sample_yaml = tmp_path / "exam.yaml"
    sample_yaml.write_text(
        """title: Modular Exam
---
- type: tf
  marks: 2.0
  question: "Is QuizML **modular**?"
  answer: true
""",
        encoding="utf-8",
    )

    # 1. Ingest via quizmlyaml.load
    doc, schema = quizml.load(sample_yaml, validate=True)
    assert doc["header"]["title"] == "Modular Exam"
    assert len(doc["questions"]) == 1
    assert doc["questions"][0]["marks"] == 2.0
    assert doc["questions"][0]["answer"] is True

    # 2. Transcode to HTML
    doc_html = quizml.transcode(doc, target="html")
    assert "<strong>modular</strong>" in doc_html["questions"][0]["question"]

    # 3. Transcode to LaTeX
    doc_latex = quizml.transcode(doc, target="latex")
    assert "\\textbf{modular}" in doc_latex["questions"][0]["question"]

    # 4. Render using Jinja2
    template_file = tmp_path / "exam.txt.j2"
    template_file.write_text(
        "Exam: << header.title >>\nQuestion: << questions[0].question >>",
        encoding="utf-8",
    )
    output = quizml.render(doc_latex, template_file)
    assert "Exam: Modular Exam" in output
    assert "\\textbf{modular}" in output


def test_builder_compile_quiz(tmp_path: Path):
    """Test builder.compile_quiz execution."""
    quiz_file = tmp_path / "quiz.yaml"
    quiz_file.write_text(
        """title: Test Quiz
---
- type: essay
  marks: 5
  question: Explain DAG compilation.
  answer: Dependency graph.
""",
        encoding="utf-8",
    )

    custom_cfg = {
        "yaml_filename": str(quiz_file),
        "schema_path": "schema.json",
        "default_targets": ["txt"],
        "targets": [
            {
                "name": "txt",
                "template": str(tmp_path / "simple.txt.j2"),
                "out": str(tmp_path / "output.txt"),
                "descr": "Text Export",
                "descr_cmd": "Write output.txt",
                "fmt": "html",
            }
        ],
    }

    template_path = tmp_path / "simple.txt.j2"
    template_path.write_text("Title: << header.title >>\n", encoding="utf-8")

    results = builder.compile_quiz(
        yaml_file=quiz_file,
        targets=["txt"],
        config=custom_cfg,
    )

    assert len(results) == 1
    assert results[0].success is True
    assert (tmp_path / "output.txt").exists()
    content = (tmp_path / "output.txt").read_text(encoding="utf-8")
    assert "<p>Test Quiz</p>" in content


def test_tools_format_file(tmp_path: Path):
    """Test tools.format_file standalone utility."""
    test_yaml = tmp_path / "unformatted.yaml"
    test_yaml.write_text(
        """
- # <Q99>
  type: tf
  question: True or false?
  answer: true
""",
        encoding="utf-8",
    )

    changed, formatted = tools.format_file(test_yaml, in_place=True)
    assert changed is True
    assert "- # <Q1>" in formatted
    assert "# <Q99>" not in formatted
    assert "- # <Q1>" in test_yaml.read_text(encoding="utf-8")


def test_tools_cleanup_build(tmp_path: Path):
    """Test tools.cleanup_build and find_cleanup_files."""
    exam = tmp_path / "testexam.yaml"
    exam.write_text("title: Test\n---\n[]")

    pdf = tmp_path / "testexam.pdf"
    pdf.write_text("dummy pdf")
    aux = tmp_path / "testexam.aux"
    aux.write_text("dummy aux")
    keep = tmp_path / "important.py"
    keep.write_text("print('keep me')")

    candidates = tools.find_cleanup_files(tmp_path)
    assert pdf in candidates
    assert aux in candidates
    assert keep not in candidates

    # Run cleanup
    cleaned = tools.cleanup_build(tmp_path, dry_run=False)
    assert pdf in cleaned
    assert aux in cleaned
    assert not pdf.exists()
    assert not aux.exists()
    assert keep.exists()


def test_tools_diff(tmp_path: Path):
    """Test tools.compare_quiz_files and questions_are_similar."""
    q1 = {"type": "essay", "question": "Explain gradient descent."}
    q2 = {"type": "essay", "question": "explain Gradient Descent."}
    q3 = {"type": "mc", "question": "Explain gradient descent."}

    assert tools.questions_are_similar(q1, q2) is True
    assert tools.questions_are_similar(q1, q3) is False

    f1 = tmp_path / "exam1.yaml"
    f1.write_text("""
- type: essay
  question: Explain gradient descent.
""")
    f2 = tmp_path / "exam2.yaml"
    f2.write_text("""
- type: essay
  question: explain gradient descent.
""")

    comparison = tools.compare_quiz_files(f1, [f2])
    assert len(comparison) == 1
    assert str(f2) in comparison[0]["dups"]


def test_cli_ingest(tmp_path: Path, monkeypatch, capsys):
    """Test CLI --ingest outputs valid JSON IR."""
    yaml_file = tmp_path / "ingest_test.yaml"
    yaml_file.write_text(
        """title: Ingest Test
---
- type: tf
  marks: 1.5
  question: First question
  answer: false
""",
        encoding="utf-8",
    )

    # Test ordering 1: quizml --ingest file.yaml
    monkeypatch.setattr(sys, "argv", ["quizml", "--ingest", str(yaml_file)])
    main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["header"]["title"] == "Ingest Test"
    assert data["questions"][0]["marks"] == 1.5
    assert data["questions"][0]["answer"] is False

    # Test ordering 2: quizml file.yaml --ingest
    monkeypatch.setattr(sys, "argv", ["quizml", str(yaml_file), "--ingest"])
    main()
    captured2 = capsys.readouterr()
    data2 = json.loads(captured2.out)
    assert data2 == data


def test_cli_transcode(tmp_path: Path, monkeypatch, capsys):
    """Test CLI --transcode produces transcoded JSON IR."""
    yaml_file = tmp_path / "transcode_test.yaml"
    yaml_file.write_text(
        """title: Transcode Test
---
- type: essay
  marks: 5
  question: "Explain **backprop** in $O(N)$."
  answer: "Gradient method."
""",
        encoding="utf-8",
    )

    # 1. Transcode to LaTeX
    monkeypatch.setattr(
        sys, "argv", ["quizml", str(yaml_file), "--transcode", "latex"]
    )
    main()
    captured_latex = capsys.readouterr()
    data_latex = json.loads(captured_latex.out)
    q_latex = data_latex["questions"][0]["question"]
    assert "\\textbf{backprop}" in q_latex
    assert "$O(N)$" in q_latex

    # 2. Transcode to HTML
    monkeypatch.setattr(sys, "argv", ["quizml", "--transcode", "html", str(yaml_file)])
    main()
    captured_html = capsys.readouterr()
    data_html = json.loads(captured_html.out)
    q_html = data_html["questions"][0]["question"]
    assert "<strong>backprop</strong>" in q_html


def test_cli_render(tmp_path: Path, monkeypatch, capsys):
    """Test CLI --render produces final rendered document."""
    yaml_file = tmp_path / "render_test.yaml"
    yaml_file.write_text(
        """title: Direct Render Test
---
- type: tf
  marks: 2
  question: "Is this rendered directly?"
  answer: true
""",
        encoding="utf-8",
    )

    # Render LaTeX template directly from YAML (auto-infers latex format)
    monkeypatch.setattr(
        sys, "argv", ["quizml", str(yaml_file), "--render", "tcd-exam.tex.j2"]
    )
    main()
    captured = capsys.readouterr()
    assert "\\documentclass{tcdexams}" in captured.out
    assert "Direct Render Test" in captured.out


def test_cli_piped_flow(tmp_path: Path, monkeypatch, capsys):
    """Test 3-stage pipe: ingest -> transcode -> render across separate invocations via stdin."""
    yaml_file = tmp_path / "pipe_test.yaml"
    yaml_file.write_text(
        """title: Pipe Assessment
---
- type: essay
  marks: 10
  question: "Discuss **Transformers** in deep learning."
  answer: "Attention is all you need."
""",
        encoding="utf-8",
    )

    # Stage 1: Ingest
    monkeypatch.setattr(sys, "argv", ["quizml", "--ingest", str(yaml_file)])
    main()
    ingest_json = capsys.readouterr().out

    # Stage 2: Transcode via stdin
    monkeypatch.setattr(sys, "stdin", io.StringIO(ingest_json))
    monkeypatch.setattr(sys, "argv", ["quizml", "-", "--transcode", "latex"])
    main()
    transcode_json = capsys.readouterr().out
    assert "\\textbf{Transformers}" in transcode_json

    # Stage 3: Render via stdin
    monkeypatch.setattr(sys, "stdin", io.StringIO(transcode_json))
    monkeypatch.setattr(sys, "argv", ["quizml", "-", "--render", "tcd-exam.tex.j2"])
    main()
    rendered_tex = capsys.readouterr().out
    assert "\\documentclass{tcdexams}" in rendered_tex
    assert "Pipe Assessment" in rendered_tex
    assert "\\textbf{Transformers}" in rendered_tex

