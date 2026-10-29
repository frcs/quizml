from quizml.cli.shellcompletion import bash, fish, zsh


def test_bash_completion():
    script = bash()
    assert "_quizml()" in script
    assert "complete -F _quizml quizml" in script
    assert 'command == "docs"' in script
    assert (
        "compile diff fmt sample clean init docs info targets completion cache"
        in script
    )
    assert "quickstart" in script
    assert "all" in script


def test_zsh_completion():
    script = zsh()
    assert "_quizml() {" in script
    assert "docs)" in script
    assert "quickstart" in script
    assert "--no-pager" in script
    assert "completion)" in script
    assert "yaml-files:yaml file:_files" in script


def test_fish_completion():
    script = fish()
    assert "complete -c quizml" in script
    assert "-l no-pager" in script
    assert "quickstart" in script
    assert "bash zsh fish" in script
