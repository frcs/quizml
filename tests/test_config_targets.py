from unittest.mock import MagicMock, patch

import pytest

from quizml.cli.config import get_target_list


@pytest.fixture
def mock_dependencies():
    with (
        patch("quizml.cli.config.filelocator.locate.path") as mock_path,
        patch("pathlib.Path.read_text") as mock_read,
    ):
        mock_path.side_effect = lambda x: f"/abs/{x}"
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
    from quizml.exceptions import QuizMLConfigError

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
    assert targets[-1]["out"] == "quizzes/final.t1"


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
