import argparse

from quizml.cli.shellcompletion import bash, fish, zsh


def _build_dummy_parser():
    parser = argparse.ArgumentParser(prog="quizml")
    parser.add_argument(
        "--docs",
        nargs="?",
        const="",
        metavar="TOPIC",
        help="display documentation topics",
    )
    parser.add_argument(
        "--shell-completion",
        choices=["bash", "zsh", "fish"],
        help="print shell completion script",
    )
    parser.add_argument("--no-pager", action="store_true", help="disable pager")
    parser.add_argument("-w", "--watch", action="store_true", help="watch files")
    return parser


def test_bash_completion():
    parser = _build_dummy_parser()
    script = bash(parser)
    assert "_quizml()" in script
    assert "complete -F _quizml quizml" in script
    assert 'if [[ ${prev} == "--docs" ]] ; then' in script
    assert "quickstart" in script
    assert "all" in script


def test_zsh_completion():
    parser = _build_dummy_parser()
    script = zsh(parser)
    assert "function _quizml(){" in script
    assert "--docs[display documentation topics]::topic:(" in script
    assert "quickstart" in script
    assert "--shell-completion" in script
    assert "--no-pager" in script


def test_fish_completion():
    parser = _build_dummy_parser()
    script = fish(parser)
    assert "complete -c quizml" in script
    assert "-l docs" in script
    assert "quickstart" in script
    assert "bash zsh fish" in script
