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
    parser.add_argument("--render", metavar="TEMPLATE", help="render template")
    parser.add_argument("--transcode", metavar="FMT", help="transcode format")
    parser.add_argument("--no-pager", action="store_true", help="disable pager")
    parser.add_argument("-w", "--watch", action="store_true", help="watch files")
    return parser


def test_bash_completion():
    parser = _build_dummy_parser()
    script = bash(parser)
    assert "_quizml()" in script
    assert "complete -F _quizml quizml" in script
    assert 'if [[ ${prev} == "--docs" ]] ; then' in script
    assert 'if [[ ${prev} == "--render" ]] ; then' in script
    assert 'if [[ ${prev} == "--transcode" ]] ; then' in script
    assert "quickstart" in script
    assert "tcd-exam.tex.j2" in script
    assert "all" in script


def test_zsh_completion():
    parser = _build_dummy_parser()
    script = zsh(parser)
    assert script.startswith("#compdef quizml")
    assert "function _quizml(){" in script
    assert "_quizml_templates" in script
    assert "--docs[display documentation topics]:topic:(" in script
    assert "--render[render template]:template:_quizml_templates" in script
    assert "--transcode[transcode format]:format:(latex html html-svg html-mathml)" in script
    assert "quickstart" in script
    assert "tcd-exam.tex.j2" in script
    assert "--shell-completion" in script
    assert "--no-pager" in script
    assert 'if [ "$funcstack[1]" = "_quizml" ]; then' in script
    assert "compdef _quizml quizml" in script

    # Ensure topic list contains no shell metacharacters like & or /
    topics_part = script.split(":topic:(")[1].split(")")[0]
    for topic in topics_part.split():
        assert "&" not in topic
        assert "/" not in topic


def test_fish_completion():
    parser = _build_dummy_parser()
    script = fish(parser)
    assert "complete -c quizml" in script
    assert "-l docs" in script
    assert "-l render" in script
    assert "-l transcode" in script
    assert "tcd-exam.tex.j2" in script
    assert "quickstart" in script
    assert "bash zsh fish" in script
