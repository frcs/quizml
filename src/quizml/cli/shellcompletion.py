from quizml.cli.docs import get_all_topics

COMMANDS = (
    "compile",
    "diff",
    "fmt",
    "clean",
    "init",
    "docs",
    "info",
    "targets",
    "completion",
)
OPTIONS = {
    "compile": "-h --help --config --debug --verbose --quiet -t --target --build -w --watch",
    "diff": "-h --help --config --debug --verbose --quiet",
    "fmt": "-h --help -i --in-place --check --diff --wrap",
    "clean": "-h --help --dry-run",
    "init": "-h --help",
    "docs": "-h --help --no-pager",
    "info": "-h --help",
    "targets": "-h --help --config --debug --verbose --quiet",
    "completion": "-h --help",
}


def _docs_topics():
    return " ".join(sorted(get_all_topics()))


def bash():
    commands = " ".join(COMMANDS)
    options = " ".join(
        sorted({opt for values in OPTIONS.values() for opt in values.split()})
    )
    topics = _docs_topics()
    return f'''_quizml()
{{
    local cur prev command opts topics
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    command="${{COMP_WORDS[1]}}"
    opts="{options}"
    topics="{topics}"
    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "{commands} -h --help -v --version" -- "$cur") $(compgen -f -X "!*.yaml" -- "$cur") $(compgen -f -X "!*.yml" -- "$cur") )
    elif [[ $command == "docs" && $prev == "docs" ]]; then
        COMPREPLY=( $(compgen -W "$topics" -- "$cur") )
    elif [[ $cur == -* ]]; then
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
    else
        COMPREPLY=( $(compgen -f -- "$cur") )
    fi
    return 0
}}
complete -F _quizml quizml'''


def zsh():
    commands = " ".join(COMMANDS)
    lines = [
        "#compdef quizml",
        "_quizml() {",
        "  local -a commands",
        f"  commands=({commands})",
        "  if (( CURRENT == 2 )); then",
        '    _describe "QuizML command" commands',
        "    return",
        "  fi",
        "  case $words[2] in",
    ]
    for command, opts in OPTIONS.items():
        specs = " ".join(f"'{opt}[{opt}]'" for opt in opts.split())
        if command == "docs":
            specs += f" '*:topic:({_docs_topics()})'"
        lines.extend(
            [
                f"    {command})",
                f"      _arguments '*:file:_files' {specs}",
                "      ;;",
            ]
        )
    lines.extend(["  esac", "}", "_quizml"])
    return "\n".join(lines)


def fish():
    lines = [
        f"complete -c quizml -f -n '__fish_use_subcommand' -a '{' '.join(COMMANDS)}'"
    ]
    lines.extend(
        [
            "complete -c quizml -n '__fish_seen_subcommand_from compile diff fmt' -F",
            "complete -c quizml -n '__fish_seen_subcommand_from init' -a 'local user'",
            "complete -c quizml -n '__fish_seen_subcommand_from completion' -a 'bash zsh fish'",
        ]
    )
    for command, opts in OPTIONS.items():
        lines.append(
            f"complete -c quizml -n '__fish_seen_subcommand_from {command}' -f"
        )
        for opt in opts.split():
            if opt.startswith("--"):
                lines.append(
                    f"complete -c quizml -n '__fish_seen_subcommand_from {command}' -l {opt[2:]}"
                )
            elif opt.startswith("-") and len(opt) == 2:
                lines.append(
                    f"complete -c quizml -n '__fish_seen_subcommand_from {command}' -s {opt[1:]}"
                )
    lines.append(
        "complete -c quizml -n '__fish_seen_subcommand_from docs' -a '"
        + _docs_topics()
        + "'"
    )
    return "\n".join(lines)
