from quizml.paths import find_path
from quizml.cli.filelocator import FileLocator


def test_find_path_uses_search_directory_order(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "asset.txt").write_text("first", encoding="utf-8")
    (second / "asset.txt").write_text("second", encoding="utf-8")

    found, index = find_path("asset.txt", [first, second])

    assert found == (first / "asset.txt").resolve()
    assert index == 0


def test_find_path_absolute_and_missing(tmp_path):
    asset = tmp_path / "asset.txt"
    asset.write_text("asset", encoding="utf-8")

    assert find_path(str(asset), []) == (asset.resolve(), None)
    assert find_path("missing.txt", [tmp_path]) is None


def test_file_locator_captures_explicit_command_directory(tmp_path, monkeypatch):
    initial_dir = FileLocator().cw_dir
    monkeypatch.chdir(tmp_path)

    assert FileLocator().cw_dir == str(tmp_path)
    assert FileLocator(cwd=initial_dir).cw_dir == initial_dir
