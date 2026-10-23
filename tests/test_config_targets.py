from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from quizml.cli.config import get_config, get_target_list
from quizml.exceptions import QuizMLConfigError


@pytest.fixture
def mock_dependencies():
    with (
        patch("quizml.cli.config.FileLocator.path", autospec=True) as mock_path,
        patch("pathlib.Path.read_text") as mock_read,
    ):
        mock_path.side_effect = lambda _self, x: f"/abs/{x}"
        mock_read.return_value = "content"
        yield


def test_get_target_list_defaults(mock_dependencies):
    args = MagicMock()
    args.target = None
    args.yaml_filename = "test.yaml"

    config = {
        "yaml_filename": "test.yaml",
        "default_targets": ["t1"],
        "targets": [
            {"name": "t1", "template": "t1.jinja", "descr": "Target 1"},
            {"name": "t2", "template": "t2.jinja", "descr": "Target 2"},
        ],
    }

    yaml_data = {"header": {}}

    targets = get_target_list(args, config, yaml_data)
    assert len(targets) == 1
    assert targets[0]["name"] == "t1"


def test_get_target_list_cli_override(mock_dependencies):
    args = MagicMock()
    args.target = ["t2"]
    args.yaml_filename = "test.yaml"

    config = {
        "yaml_filename": "test.yaml",
        "default_targets": ["t1"],
        "targets": [
            {"name": "t1", "template": "t1.jinja", "descr": "Target 1"},
            {"name": "t2", "template": "t2.jinja", "descr": "Target 2"},
        ],
    }

    yaml_data = {"header": {}}

    targets = get_target_list(args, config, yaml_data)
    assert len(targets) == 1
    assert targets[0]["name"] == "t2"


def test_get_target_list_no_defaults(mock_dependencies):
    args = MagicMock()
    args.target = None
    args.yaml_filename = "test.yaml"

    config = {
        "yaml_filename": "test.yaml",
        "targets": [
            {"name": "t1", "template": "t1.jinja", "descr": "Target 1"},
            {"name": "t2", "template": "t2.jinja", "descr": "Target 2"},
        ],
    }

    yaml_data = {"header": {}}

    targets = get_target_list(args, config, yaml_data)
    assert len(targets) == 2
    names = sorted([t["name"] for t in targets])
    assert names == ["t1", "t2"]


def test_get_target_list_defaults_with_dependencies(mock_dependencies):
    args = MagicMock()
    args.target = None
    args.yaml_filename = "test.yaml"

    # t1 depends on t2. If t1 is default, t2 should also be included (if logic permits, or just t1 is selected but deps are handled elsewhere?
    # get_required_target_names_set handles dependencies recursively.

    config = {
        "yaml_filename": "test.yaml",
        "default_targets": ["t1"],
        "targets": [
            {"name": "t1", "template": "t1.jinja", "descr": "Target 1", "dep": "t2"},
            {"name": "t2", "template": "t2.jinja", "descr": "Target 2"},
        ],
    }

    yaml_data = {"header": {}}

    targets = get_target_list(args, config, yaml_data)
    # logic: get_required_target_names_set(['t1']) -> {'t1', 't2'}
    # And topological order ensures dependency t2 precedes t1
    assert [t["name"] for t in targets] == ["t2", "t1"]


def test_get_target_list_circular_dependency(mock_dependencies):
    args = MagicMock()
    args.target = ["t1"]
    args.yaml_filename = "test.yaml"

    config = {
        "yaml_filename": "test.yaml",
        "targets": [
            {"name": "t1", "template": "t1.jinja", "descr": "Target 1", "dep": "t2"},
            {"name": "t2", "template": "t2.jinja", "descr": "Target 2", "dep": "t1"},
        ],
    }
    yaml_data = {"header": {}}

    with pytest.raises(QuizMLConfigError, match="Circular dependency"):
        get_target_list(args, config, yaml_data)


@pytest.mark.parametrize(
    ("selected", "aliases"),
    [(["consumer"], {}), (["build"], {"build": "consumer"})],
)
def test_get_target_list_rejects_unknown_dependencies(
    mock_dependencies, selected, aliases
):
    args = MagicMock()
    args.target = selected
    args.yaml_filename = "test.yaml"
    config = {
        "yaml_filename": "test.yaml",
        "aliases": aliases,
        "targets": [
            {
                "name": "consumer",
                "template": "consumer.jinja",
                "descr": "Consumer",
                "dep": "misspelled-producer",
            }
        ],
    }

    with pytest.raises(
        QuizMLConfigError,
        match="Target 'consumer' depends on unknown target 'misspelled-producer'",
    ):
        get_target_list(args, config, {"header": {}})


@pytest.mark.parametrize("contents", ["null\n", "- one\n- two\n", "42\n"])
def test_get_config_rejects_non_mapping_root(tmp_path, contents):
    from types import SimpleNamespace

    config_file = tmp_path / "quizml.cfg"
    config_file.write_text(contents, encoding="utf-8")

    with pytest.raises(QuizMLConfigError, match="YAML mapping at its root"):
        get_config(SimpleNamespace(config=str(config_file), yaml_filename="quiz.yaml"))


def test_get_config_reports_file_read_errors(tmp_path):
    from types import SimpleNamespace

    with pytest.raises(QuizMLConfigError, match="Could not read config file"):
        get_config(SimpleNamespace(config=str(tmp_path), yaml_filename="quiz.yaml"))


def test_get_target_list_with_list_dep(mock_dependencies):
    args = MagicMock()
    args.target = ["t1"]
    args.yaml_filename = "quizzes/final.yaml"

    config = {
        "yaml_filename": "quizzes/final.yaml",
        "targets": [
            {
                "name": "t1",
                "template": "t1.jinja",
                "descr": "Target 1",
                "dep": ["t2", "t3"],
                "out": "${inputdir}/${inputstem}.t1",
            },
            {"name": "t2", "template": "t2.jinja", "descr": "Target 2"},
            {"name": "t3", "template": "t3.jinja", "descr": "Target 3"},
        ],
    }
    yaml_data = {"header": {}}

    targets = get_target_list(args, config, yaml_data)
    names = [t["name"] for t in targets]
    assert "t2" in names
    assert "t3" in names
    assert names[-1] == "t1"
    assert targets[-1]["out"] == f"{Path('quizzes').resolve()}/final.t1"


def test_get_target_list_safe_substitute(mock_dependencies):
    args = MagicMock()
    args.target = ["cmd_target"]
    args.yaml_filename = "quiz.yaml"

    config = {
        "yaml_filename": "quiz.yaml",
        "targets": [
            {
                "name": "cmd_target",
                "descr": "Command",
                "build_cmd": "latexmk -outdir=$HOME/out ${inputbasename}.tex",
            }
        ],
    }
    yaml_data = {"header": {}}

    targets = get_target_list(args, config, yaml_data)
    assert len(targets) == 1
    assert targets[0]["build_cmd"] == "latexmk -outdir=$HOME/out quiz.tex"


def test_get_target_list_normalizes_markdown_transcoding_settings(mock_dependencies):
    args = MagicMock()
    args.target = ["bb"]
    args.yaml_filename = "quiz.yaml"
    config = {
        "yaml_filename": "quiz.yaml",
        "targets": [
            {
                "name": "bb",
                "descr": "Blackboard",
                "template": "bb.j2",
                "markdown": {
                    "format": "html",
                    "math": "svg",
                    "html_postprocess": "blackboard_html",
                },
            }
        ],
    }

    targets = get_target_list(args, config, {"header": {}})

    assert targets[0]["fmt"] == "html-svg"
    assert targets[0]["html_postprocess"] == "blackboard_html"


def test_legacy_html_fmt_keeps_historical_postprocessing(mock_dependencies):
    args = MagicMock()
    args.target = ["legacy"]
    args.yaml_filename = "quiz.yaml"
    config = {
        "yaml_filename": "quiz.yaml",
        "targets": [
            {
                "name": "legacy",
                "descr": "Legacy HTML target",
                "fmt": "html-svg",
            }
        ],
    }

    target = get_target_list(args, config, {"header": {}})[0]

    assert target["fmt"] == "html-svg"
    assert target["html_postprocess"] == "blackboard_html"


def test_get_target_list_substitutes_variables_before_filelocator(mock_dependencies):
    args = MagicMock()
    args.target = ["t1"]
    args.yaml_filename = "quizzes/exam.yaml"
    config = {
        "yaml_filename": "quizzes/exam.yaml",
        "targets": [
            {
                "name": "t1",
                "template": "${inputstem}.j2",
            }
        ],
    }

    targets = get_target_list(args, config, {"header": {}})
    assert targets[0]["template"] == "/abs/exam.j2"
    assert targets[0]["descr"] == "t1"
    assert targets[0]["out"] == ""
    assert targets[0]["descr_cmd"] == ""


def test_get_config_rejects_invalid_targets_list(tmp_path):
    from types import SimpleNamespace

    cfg = tmp_path / "quizml.cfg"
    cfg.write_text("targets: not-a-list\n", encoding="utf-8")
    with pytest.raises(QuizMLConfigError, match="list of target mappings"):
        get_config(SimpleNamespace(config=str(cfg), yaml_filename="quiz.yaml"))


def test_filelocator_prioritizes_base_dir_over_cwd(tmp_path):
    from quizml.cli.filelocator import FileLocator

    cwd_dir = tmp_path / "cwd"
    base_dir = tmp_path / "quiz_dir"
    cwd_dir.mkdir()
    base_dir.mkdir()
    (cwd_dir / "quizml.cfg").write_text("targets: []\n", encoding="utf-8")
    (base_dir / "quizml.cfg").write_text("targets: []\n", encoding="utf-8")

    locator = FileLocator(cwd=str(cwd_dir), base_dir=str(base_dir))
    assert locator.path("quizml.cfg") == str(base_dir / "quizml.cfg")


def test_get_target_list_expands_header_variables_and_vars_alias(mock_dependencies):
    args = MagicMock()
    args.target = ["pdf", "quarto"]
    args.yaml_filename = "quiz.yaml"
    config = {
        "yaml_filename": "quiz.yaml",
        "vars": {"watermark": "DRAFT"},
        "targets": [
            {
                "name": "pdf",
                "template": "exam.tex.j2",
                "out": "${modulecode}-${examyear}-${inputstem}.tex",
                "vars": {"solutions": True},
            },
            {
                "name": "quarto",
                "template": "exam.qmd.j2",
                "out": "${modulecode}.qmd",
                "markdown": {"format": "markdown"},
            },
        ],
    }
    yaml_data = {"header": {"modulecode": "4C16", "examyear": 2026}}
    targets = get_target_list(args, config, yaml_data)
    assert targets[0]["out"] == "4C16-2026-quiz.tex"
    assert targets[0]["context"] == {"watermark": "DRAFT", "solutions": True}
    assert targets[1]["fmt"] == "markdown"


def test_get_target_list_respects_header_targets(mock_dependencies):
    args = MagicMock()
    args.target = None
    args.yaml_filename = "quiz.yaml"
    config = {
        "yaml_filename": "quiz.yaml",
        "default_targets": ["t1"],
        "targets": [
            {"name": "t1", "template": "t1.jinja"},
            {"name": "t2", "template": "t2.jinja"},
        ],
    }
    yaml_data = {"header": {"_targets": ["t2"]}}
    targets = get_target_list(args, config, yaml_data)
    assert [t["name"] for t in targets] == ["t2"]


def test_get_config_respects_header_config_and_version_check(tmp_path):
    from types import SimpleNamespace

    from quizml.cli.config import check_quizml_version

    custom_cfg = tmp_path / "custom.cfg"
    custom_cfg.write_text(
        "quizml_version: '>=0.1'\ntargets:\n  - name: preview\n    template: preview.html.j2\n",
        encoding="utf-8",
    )
    quiz_file = tmp_path / "exam.yaml"
    quiz_file.write_text(
        "_config: custom.cfg\n---\n- type: essay\n  question: Q1\n",
        encoding="utf-8",
    )

    cfg = get_config(SimpleNamespace(config=None, yaml_filename=str(quiz_file)))
    assert cfg["_config_dir"] == str(tmp_path)

    with patch("importlib.metadata.version", return_value="0.12.2"):
        assert check_quizml_version(">=0.12,<0.13", "exam.yaml") is True
        assert check_quizml_version("~=0.12", "exam.yaml") is True
        assert check_quizml_version(">=99.0", "exam.yaml") is False


def test_get_config_resolves_texinputs_relative_to_config_dir(tmp_path):
    from types import SimpleNamespace

    cfg_dir = tmp_path / "cfg_sub"
    cfg_dir.mkdir()
    shared_dir = tmp_path / "shared"
    shared_dir.mkdir()

    cfg_file = cfg_dir / "quizml.cfg"
    cfg_file.write_text(
        "texinputs:\n"
        "  - ../shared\n"
        "  - /absolute/path\n"
        "targets:\n"
        "  - name: dummy\n"
        "    template: dummy.j2\n",
        encoding="utf-8",
    )

    cfg = get_config(SimpleNamespace(config=str(cfg_file), yaml_filename="quiz.yaml"))
    assert cfg["texinputs"] == [
        str(shared_dir.resolve()),
        "/absolute/path",
    ]


def test_default_config_latex_solutions_dependency_chain():
    """Verify that latex-solutions depends on latex and pdf-solutions orders dependencies correctly."""
    args = SimpleNamespace(
        config=None, target=["pdf-solutions"], yaml_filename="exam.yaml", verbose=False
    )
    cfg = get_config(args)
    latex_sol = next(t for t in cfg["targets"] if t.get("name") == "latex-solutions")
    assert latex_sol.get("dep") == "latex"

    yaml_data = {"header": {"inputbasename": "exam"}}
    targets = get_target_list(args, cfg, yaml_data)
    assert [t["name"] for t in targets] == [
        "latex",
        "latex-solutions",
        "pdf-solutions",
    ]


