from rich.markdown import Markdown

from quizml.cli.livereload import LiveReloadServer
from quizml.cli.ui import CustomTableElement, QuizMLMarkdown


def test_cli_table_markdown_does_not_patch_rich_globally():
    assert Markdown.elements.get("table_open") is not CustomTableElement
    assert QuizMLMarkdown.elements["table_open"] is CustomTableElement


def test_livereload_timestamps_belong_to_server_instances():
    first = LiveReloadServer()
    second = LiveReloadServer()

    first.update_timestamp()

    assert first.timestamp > 0
    assert second.timestamp == 0
