from rich.markdown import Markdown

from quizml.cli import compile as compile_cli
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


def test_livereload_server_binds_only_to_loopback():
    server = LiveReloadServer()

    assert server.start() is not None
    try:
        assert server._server.server_address[0] == "127.0.0.1"
    finally:
        server.stop()


def test_watch_mode_recursively_watches_input_parent(tmp_path, monkeypatch):
    scheduled = {}

    class FakeObserver:
        def schedule(self, handler, path, recursive=False):
            scheduled.update(path=path, recursive=recursive)

        def start(self):
            pass

        def stop(self):
            pass

        def join(self):
            pass

    class StopEvent:
        def wait(self, timeout=None):
            raise KeyboardInterrupt

    monkeypatch.setattr(compile_cli, "Observer", FakeObserver)
    monkeypatch.setattr(compile_cli.threading, "Event", StopEvent)
    yaml_path = tmp_path / "quiz.yaml"

    compile_cli.compile_on_change(type("Args", (), {"yaml_filename": str(yaml_path)})())

    assert scheduled == {"path": str(tmp_path), "recursive": True}
