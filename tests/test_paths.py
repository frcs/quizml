from quizml.paths import find_path


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
