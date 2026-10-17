from quizml.cli.filelocator import FileLocator
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


def test_file_locator_captures_explicit_command_directory(tmp_path, monkeypatch):
    initial_dir = FileLocator().cw_dir
    monkeypatch.chdir(tmp_path)

    assert FileLocator().cw_dir == str(tmp_path)
    assert FileLocator(cwd=initial_dir).cw_dir == initial_dir


def test_file_locator_walks_up_to_parent_quizml_dir(tmp_path, monkeypatch):
    module_root = tmp_path / "ee4c16"
    root_quizml = module_root / "_quizml"
    root_quizml.mkdir(parents=True)
    (root_quizml / "quizml.cfg").write_text("root-cfg", encoding="utf-8")
    (root_quizml / "shared.tex.j2").write_text("root-template", encoding="utf-8")

    year_dir = module_root / "2025-26"
    year_quizml = year_dir / "_quizml"
    year_quizml.mkdir(parents=True)
    (year_quizml / "shared.tex.j2").write_text("year-override", encoding="utf-8")

    monkeypatch.chdir(year_dir)
    locator = FileLocator(base_dir=str(year_dir))

    # Inherits quizml.cfg from parent module_root/_quizml
    assert locator.path("quizml.cfg") == str((root_quizml / "quizml.cfg").resolve())
    # Local year_dir/_quizml overrides parent module_root/_quizml
    assert locator.path("shared.tex.j2") == str(
        (year_quizml / "shared.tex.j2").resolve()
    )


def test_file_locator_includes_explicit_config_dir(tmp_path):
    custom_cfg_dir = tmp_path / "dept-templates"
    custom_cfg_dir.mkdir()
    (custom_cfg_dir / "dept.tex.j2").write_text("dept", encoding="utf-8")

    exam_dir = tmp_path / "2025-26"
    exam_dir.mkdir()

    locator = FileLocator(base_dir=str(exam_dir), config_dir=str(custom_cfg_dir))
    assert locator.path("dept.tex.j2") == str(
        (custom_cfg_dir / "dept.tex.j2").resolve()
    )

