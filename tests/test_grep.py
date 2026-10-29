import pytest

from quizml.cli.cli import build_parser, main
from quizml.yaml.grep import (
    find_quiz_files_for_grep,
    format_matching_questions,
    grep_questions,
    is_question_match,
)


@pytest.fixture
def sample_quiz_dir(tmp_path):
    quiz1 = tmp_path / "exam1.yaml"
    quiz1.write_text(
        """title: Exam 1
---
- type: mc
  marks: 5
  question: What is backpropagation?
  choices:
  - x: An algorithm for computing gradients
  - o: A type of activation function

- type: tf
  marks: 2
  question: ReLU avoids vanishing gradient in positive domain.
  figure: relu-curve.png
  choices:
  - x: True
  - o: False
"""
    )

    subdir = tmp_path / "bank"
    subdir.mkdir()
    quiz2 = subdir / "exam2.yaml"
    quiz2.write_text(
        """title: Exam 2
---
- type: mc
  marks: 5
  question: What is backpropagation?
  choices:
  - x: An algorithm for computing gradients
  - o: A type of activation function

- type: ma
  marks: 6
  question: Which activation functions suffer from vanishing gradient?
  figure: activations-VG.png
  choices:
  - x: Sigmoid
  - x: Tanh
  - o: ReLU
"""
    )
    return tmp_path


def test_is_question_match():
    q = {
        "type": "mc",
        "question": "Calculate derivative of sigmoid.",
        "figure": "sigmoid.png",
        "choices": [{"x": "s(1-s)"}, {"o": "1-s"}],
    }

    assert is_question_match(q, "sigmoid")
    assert not is_question_match(q, "tanh")
    assert is_question_match(q, "SIGMOID", ignore_case=True)
    assert not is_question_match(q, "SIGMOID", ignore_case=False)
    assert is_question_match(q, "sigmoid\\.png")
    assert is_question_match(q, "sigmoid.png", fixed_strings=True)

    # Field specific
    assert is_question_match(q, "sigmoid", field="question")
    assert not is_question_match(q, "s(1-s)", fixed_strings=True, field="question")
    assert is_question_match(q, "s(1-s)", fixed_strings=True, field="choices")
    assert is_question_match(q, r"s\(1-s\)", field="choices")
    assert is_question_match(q, "sigmoid.png", field="figure")

    # Invert match
    assert not is_question_match(q, "sigmoid", invert_match=True)
    assert is_question_match(q, "tanh", invert_match=True)

    # Type specific
    assert is_question_match(q, "sigmoid", qtype="mc")
    assert not is_question_match(q, "sigmoid", qtype="tf")

    # Empty pattern or wildcard matches anything
    assert is_question_match(q, "*")
    assert is_question_match(q, "")
    assert is_question_match(q)
    assert is_question_match(q, "*", qtype="mc")
    assert not is_question_match(q, "*", qtype="tf")


def test_find_quiz_files_for_grep(sample_quiz_dir):
    files = find_quiz_files_for_grep([sample_quiz_dir], recursive=True)
    assert len(files) == 2
    assert any(f.name == "exam1.yaml" for f in files)
    assert any(f.name == "exam2.yaml" for f in files)

    non_rec = find_quiz_files_for_grep([sample_quiz_dir], recursive=False)
    assert len(non_rec) == 1
    assert non_rec[0].name == "exam1.yaml"


def test_grep_questions_basic(sample_quiz_dir):
    matches = grep_questions("backpropagation", [sample_quiz_dir])
    assert len(matches) == 2
    files = {m.file_path.name for m in matches}
    assert files == {"exam1.yaml", "exam2.yaml"}

    vg_matches = grep_questions("activations-VG", [sample_quiz_dir])
    assert len(vg_matches) == 1
    assert vg_matches[0].file_path.name == "exam2.yaml"
    assert vg_matches[0].question_index == 2
    assert vg_matches[0].question_type == "ma"


def test_grep_questions_unique(sample_quiz_dir):
    # backpropagation appears in both exam1.yaml and exam2.yaml identically
    matches_all = grep_questions("backpropagation", [sample_quiz_dir], unique=False)
    assert len(matches_all) == 2

    matches_unique = grep_questions("backpropagation", [sample_quiz_dir], unique=True)
    assert len(matches_unique) == 1
    assert len(matches_unique[0].also_in) == 1


def test_format_matching_questions(sample_quiz_dir):
    matches = grep_questions("activations-VG", [sample_quiz_dir])
    yaml_text = format_matching_questions(matches, show_provenance=True)

    assert "# " in yaml_text
    assert "activations-VG.png" in yaml_text
    assert "type: ma" in yaml_text
    assert "choices:" in yaml_text


def test_cli_grep_wildcard_and_empty_pattern(sample_quiz_dir, capsys):
    parser = build_parser()

    # Search with explicit wildcard "*"
    args = parser.parse_args(["search", "-t", "mc", "-i", "*", str(sample_quiz_dir)])
    from quizml.cli.grep import run_grep

    ret = run_grep(args)
    assert ret is True
    captured = capsys.readouterr()
    assert "What is backpropagation?" in captured.out
    assert "activations-VG" not in captured.out

    # Search omitting pattern entirely when filtering by type
    args_no_pat = parser.parse_args(["search", "-t", "ma", str(sample_quiz_dir)])
    ret_no_pat = run_grep(args_no_pat)
    assert ret_no_pat is True
    captured_no_pat = capsys.readouterr()
    assert "activations-VG.png" in captured_no_pat.out
    assert "What is backpropagation?" not in captured_no_pat.out

    # Search with -e / --regexp option
    args_regexp = parser.parse_args(
        ["search", "-e", "activations-VG", str(sample_quiz_dir)]
    )
    ret_regexp = run_grep(args_regexp)
    assert ret_regexp is True
    captured_regexp = capsys.readouterr()
    assert "activations-VG.png" in captured_regexp.out


def test_cli_grep_stdout(sample_quiz_dir, capsys):
    parser = build_parser()
    args = parser.parse_args(["grep", "activations-VG", str(sample_quiz_dir)])

    from quizml.cli.grep import run_grep

    ret = run_grep(args)
    assert ret is True

    captured = capsys.readouterr()
    assert "type: ma" in captured.out
    assert "activations-VG.png" in captured.out


def test_cli_grep_files_with_matches(sample_quiz_dir, capsys):
    parser = build_parser()
    args = parser.parse_args(["grep", "-l", "backpropagation", str(sample_quiz_dir)])

    from quizml.cli.grep import run_grep

    ret = run_grep(args)
    assert ret is True

    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert len(lines) == 2
    assert any("exam1.yaml" in line for line in lines)
    assert any("exam2.yaml" in line for line in lines)


def test_cli_grep_count(sample_quiz_dir, capsys):
    parser = build_parser()
    args = parser.parse_args(["grep", "-c", "backpropagation", str(sample_quiz_dir)])

    from quizml.cli.grep import run_grep

    ret = run_grep(args)
    assert ret is True

    captured = capsys.readouterr()
    assert "exam1.yaml: 1" in captured.out
    assert "exam2.yaml: 1" in captured.out


def test_cli_grep_table(sample_quiz_dir, capsys):
    parser = build_parser()
    args = parser.parse_args(
        ["grep", "--table", "vanishing gradient", str(sample_quiz_dir)]
    )

    from quizml.cli.grep import run_grep

    ret = run_grep(args)
    assert ret is True

    captured = capsys.readouterr()
    assert "exam1.yaml" in captured.out or "exam2.yaml" in captured.out


def test_cli_grep_output_file(sample_quiz_dir, tmp_path):
    out_file = tmp_path / "matched.yaml"
    parser = build_parser()
    args = parser.parse_args(
        ["grep", "activations-VG", str(sample_quiz_dir), "-o", str(out_file)]
    )

    from quizml.cli.grep import run_grep

    ret = run_grep(args)
    assert ret is True
    assert out_file.exists()
    content = out_file.read_text()
    assert "activations-VG.png" in content


def test_cli_grep_exit_code_zero_on_match(sample_quiz_dir, monkeypatch):
    monkeypatch.setattr(
        "sys.argv", ["quizml", "grep", "backpropagation", str(sample_quiz_dir)]
    )
    # main() exits on error, or returns None / finishes on 0
    try:
        main()
    except SystemExit as e:
        assert e.code == 0


def test_cli_grep_exit_code_one_on_no_match(sample_quiz_dir, monkeypatch):
    monkeypatch.setattr(
        "sys.argv", ["quizml", "grep", "nonexistent_xyz", str(sample_quiz_dir)]
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_cli_grep_syntax_highlighting_on_tty(sample_quiz_dir, monkeypatch):
    from rich.syntax import Syntax

    from quizml.cli.grep import run_grep

    parser = build_parser()
    args = parser.parse_args(["grep", "activations-VG", str(sample_quiz_dir)])

    printed_syntax = []

    class MockConsole:
        def print(self, renderable, *args, **kwargs):
            if isinstance(renderable, Syntax):
                printed_syntax.append(renderable)

    monkeypatch.setattr("quizml.cli.grep.Console", lambda: MockConsole())
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    ret = run_grep(args)
    assert ret is True
    assert len(printed_syntax) == 1
    assert printed_syntax[0].lexer.name.lower() == "yaml"
