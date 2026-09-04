import sys
from unittest.mock import patch

import pytest

from quizml.cli.cli import main
from quizml.cli.docs import (
    get_all_topics,
    get_docs_dir,
    get_llms_file,
    handle_docs,
    page_content,
    parse_sidebar,
)


def test_get_docs_dir():
    docs_dir = get_docs_dir()
    assert docs_dir.is_dir()
    assert (docs_dir / "_sidebar.md").is_file()


def test_get_llms_file():
    llms_file = get_llms_file()
    assert llms_file is not None
    assert llms_file.is_file()
    assert "QuizML" in llms_file.read_text(encoding="utf-8")


def test_parse_sidebar():
    docs_dir = get_docs_dir()
    items = parse_sidebar(docs_dir)
    assert len(items) > 5

    filenames = [item.filename for item in items]
    assert "quickstart.md" in filenames
    assert "syntax_questions.md" in filenames
    assert "targets.md" in filenames

    # Verify alias generation
    questions_item = next(
        item for item in items if item.filename == "syntax_questions.md"
    )
    assert "questions" in questions_item.aliases
    assert "syntax-questions" in questions_item.aliases


def test_handle_docs_list_non_tty(capsys):
    with patch("sys.stdout.isatty", return_value=False):
        handle_docs("list")
    captured = capsys.readouterr()
    assert "QuizML Documentation Topics:" in captured.out
    assert "quickstart" in captured.out
    assert "syntax_questions" in captured.out


def test_handle_docs_specific_topic_non_tty(capsys):
    with patch("sys.stdout.isatty", return_value=False):
        handle_docs("questions")
    captured = capsys.readouterr()
    assert "Question Types Syntax" in captured.out
    assert "### Essay" in captured.out
    assert "### True/False" in captured.out


def test_handle_docs_alias_non_tty(capsys):
    with patch("sys.stdout.isatty", return_value=False):
        handle_docs("yaml")
    captured = capsys.readouterr()
    assert "Test File Syntax" in captured.out or "yaml" in captured.out.lower()


def test_handle_docs_all_non_tty(capsys):
    with patch("sys.stdout.isatty", return_value=False):
        handle_docs("all")
    captured = capsys.readouterr()
    assert "<!-- Section:" in captured.out
    assert "quickstart.md" in captured.out
    assert "syntax_questions.md" in captured.out
    assert len(captured.out.splitlines()) > 500


def test_get_all_topics():
    topics = get_all_topics()
    assert "all" in topics
    assert "quickstart" in topics
    assert "usage" in topics
    assert "syntax_yaml" in topics or "yaml" in topics


def test_handle_docs_default_piped_is_all(capsys):
    # When piped (non-tty) without topic, defaults to dumping full documentation
    with patch("sys.stdout.isatty", return_value=False):
        handle_docs("")
    captured = capsys.readouterr()
    assert "<!-- Section:" in captured.out
    assert "targets.md" in captured.out


def test_handle_docs_overview_non_tty(capsys):
    with patch("sys.stdout.isatty", return_value=False):
        handle_docs("overview")
    captured = capsys.readouterr()
    assert "QuizML" in captured.out


def test_handle_docs_llms_non_tty(capsys):
    with patch("sys.stdout.isatty", return_value=False):
        handle_docs("llms")
    captured = capsys.readouterr()
    assert "QuizML Project Context for LLMs" in captured.out
    assert "Core Philosophy" in captured.out


def test_handle_docs_tty_no_pager(capsys):
    with patch("sys.stdout.isatty", return_value=True):
        handle_docs("targets", no_pager=True)
    captured = capsys.readouterr()
    assert "targets" in captured.out.lower()


def test_page_content_invokes_pager():
    from unittest.mock import MagicMock

    from rich.markdown import Markdown

    mock_proc = MagicMock()
    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        page_content(Markdown("# Test Header"))
        assert mock_popen.called
        assert mock_proc.communicate.called
        called_input = mock_proc.communicate.call_args[1].get("input", "")
        assert "Test Header" in called_input


def test_page_content_cat_fallback(capsys):
    from rich.markdown import Markdown

    with patch.dict("os.environ", {"PAGER": "cat"}):
        page_content(Markdown("# Heading in Cat"))
    captured = capsys.readouterr()
    assert "Heading in Cat" in captured.out


def test_handle_docs_unknown_topic(capsys):
    with pytest.raises(SystemExit) as exc_info:
        handle_docs("completely_invalid_topic_xyz")
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Unknown documentation topic 'completely_invalid_topic_xyz'" in captured.err
    assert "Available topics:" in captured.err


def test_cli_docs_integration(capsys):
    with patch.object(sys, "argv", ["quizml", "--docs", "quickstart"]):
        with patch("sys.stdout.isatty", return_value=False):
            main()
    captured = capsys.readouterr()
    assert "Quick Start" in captured.out


def test_cli_docs_no_pager_integration(capsys):
    with patch.object(sys, "argv", ["quizml", "--docs", "quickstart", "--no-pager"]):
        with patch("sys.stdout.isatty", return_value=True):
            main()
    captured = capsys.readouterr()
    assert "Quick Start" in captured.out
