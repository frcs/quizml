import sys

import pytest

from quizml.cli.cli import main


def test_format_renumbering(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("""---
title: Test
---
- # <Q10>
  type: ma
  question: Q1
- # <Q5>
  type: ma
  question: Q2
""")

    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", "-i", str(yaml_file)])
    main()

    new_txt = yaml_file.read_text()
    assert "- # <Q1>" in new_txt
    assert "- # <Q2>" in new_txt
    assert "# <Q10>" not in new_txt
    assert "# <Q5>" not in new_txt


def test_format_idempotence(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_idem.yaml"
    yaml_file.write_text("""---
title: Test
---
- # <Q1>
  type: ma
""")

    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", "-i", str(yaml_file)])
    main()
    txt1 = yaml_file.read_text()
    main()
    txt2 = yaml_file.read_text()
    assert txt1 == txt2


def test_format_spurious_comments(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_spurious.yaml"
    # Messy numbering in different places
    yaml_file.write_text("""---
title: Test
# <Q0>
---
# <Q12>
- # <Q15>
  type: ma
  question: Q1 # <Q99>
""")

    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", "-i", str(yaml_file)])
    main()

    new_txt = yaml_file.read_text()
    # Should only have exactly one <Q1>
    assert new_txt.count("<Q") == 1
    assert "- # <Q1>" in new_txt
    assert "<Q0>" not in new_txt
    assert "<Q12>" not in new_txt
    assert "<Q15>" not in new_txt
    assert "<Q99>" not in new_txt


def test_format_no_space_numbering(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_nospace.yaml"
    yaml_file.write_text("""
- #<Q10>
  type: ma
""")
    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", "-i", str(yaml_file)])
    main()
    new_txt = yaml_file.read_text()
    assert "- # <Q1>" in new_txt
    assert "<Q10>" not in new_txt


def test_format_choices_literal_and_indent(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_choices.yaml"
    yaml_file.write_text("""
- type: mc
  choices:
    - o: Short string
    - x: Another one
""")
    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", "-i", str(yaml_file)])
    main()

    new_txt = yaml_file.read_text()
    # Check for literal block scalar indicator '|' followed by indented text
    assert "o: |\n      Short string" in new_txt
    # Check for zero indent of choices list items relative to 'choices' key
    # '  choices:' followed by '  - o:'
    assert "  choices:\n  - o:" in new_txt


def test_format_with_horizontal_rules(tmp_path, monkeypatch):
    yaml_file = tmp_path / "test_hr.yaml"
    yaml_file.write_text("""title: Quiz
---
- type: tf
  question: |
    Top
    ---
    Bottom
  answer: true
""")
    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", "-i", str(yaml_file)])
    main()
    new_txt = yaml_file.read_text()
    assert "- # <Q1>" in new_txt
    assert "Top" in new_txt
    assert "Bottom" in new_txt


def test_format_with_include(tmp_path, monkeypatch):
    bank_file = tmp_path / "bank.yaml"
    bank_file.write_text("""- type: mc
  question: Bank Q1
- type: mc
  question: Bank Q2
- type: mc
  question: Bank Q3
""")

    main_file = tmp_path / "exam.yaml"
    main_file.write_text("""title: Exam
---
- type: essay
  question: First question
- _include: bank.yaml
- type: essay
  question: Last question
""")

    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", "-i", str(main_file)])
    main()

    formatted = main_file.read_text()
    assert "- # <Q1>" in formatted
    assert "- # <Q2>, <Q3>, <Q4>" in formatted
    assert "<Q3>" in formatted
    assert "<Q4>" in formatted
    assert "_include: bank.yaml" in formatted
    assert "- # <Q5>" in formatted

    # Test idempotence: running format again preserves the exact same tags
    main()
    formatted_again = main_file.read_text()
    assert formatted == formatted_again


def test_format_with_include_numbers_every_question(tmp_path, monkeypatch):
    bank_file = tmp_path / "bank.yaml"
    bank_file.write_text("""- type: mc
  question: Bank Q1
- type: mc
  question: Bank Q2
- type: mc
  question: Bank Q3
- type: mc
  question: Bank Q4
""")

    main_file = tmp_path / "exam.yaml"
    main_file.write_text("""title: Exam
---
- type: essay
  question: First question
- _include: bank.yaml
- type: essay
  question: Last question
""")

    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", "-i", str(main_file)])
    main()

    formatted = main_file.read_text()
    assert "- # <Q1>" in formatted
    assert "- # <Q2>, <Q3>, <Q4>, <Q5>" in formatted
    assert "- # <Q6>" in formatted


def test_fmt_defaults_to_stdout_without_modifying_file(tmp_path, monkeypatch, capsys):
    yaml_file = tmp_path / "quiz.yaml"
    original = "- type: essay\n  question: Example\n"
    yaml_file.write_text(original)

    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", str(yaml_file)])
    main()

    assert yaml_file.read_text() == original
    assert "- # <Q1>" in capsys.readouterr().out


def test_fmt_check_reports_needed_changes(tmp_path, monkeypatch):
    yaml_file = tmp_path / "quiz.yaml"
    yaml_file.write_text("- type: essay\n  question: Example\n")
    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", "--check", str(yaml_file)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "<Q1>" not in yaml_file.read_text()


def test_fmt_reads_stdin(monkeypatch, capsys):
    from io import StringIO

    monkeypatch.setattr(sys, "argv", ["quizml", "fmt", "-"])
    monkeypatch.setattr(sys, "stdin", StringIO("- type: essay\n  question: Example\n"))
    main()
    assert "- # <Q1>" in capsys.readouterr().out


def test_format_preserves_q_comment_inside_literal_block():
    from quizml.cli.format import format_yaml_text

    src = """- type: essay
  question: |
    Consider the following snippet:
    # <Q1>
    - item one
    - item two
"""
    formatted = format_yaml_text(src)
    assert "    # <Q1>\n    - item one\n" in formatted
    assert "- # <Q1>\n  type: essay" in formatted

