def _get_docs_topics() -> str:
    try:
        from quizml.cli.docs import get_all_topics

        return " ".join(sorted(get_all_topics()))
    except Exception:
        return "all list overview llms quickstart usage syntax_yaml syntax_questions targets"


def bash(parser):
    opts_list = []
    for a in parser._action_groups[1]._group_actions:
        for b in a.option_strings:
            opts_list.append(b)

    opts = " ".join(opts_list)
    docs_topics = _get_docs_topics()

    txt = f"""_quizml()
{{
    local cur prev opts docs_topics
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    opts="{opts}"
    docs_topics="{docs_topics}"

    if [[ ${{prev}} == "--docs" ]] ; then
        COMPREPLY=( $(compgen -W "${{docs_topics}}" -- ${{cur}}) )
        return 0
    fi

    if [[ ${{cur}} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${{opts}}" -- ${{cur}}) )
        return 0
    fi
    
    local IFS=$'\\n'
    COMPREPLY=( $(compgen -f -X "!*.yaml" -- ${{cur}}) $(compgen -f -X "!*.yml" -- ${{cur}}) )
}}
complete -F _quizml quizml"""
    return txt


def fish(parser):
    txt = ""
    docs_topics = _get_docs_topics()

    for a in parser._action_groups[1]._group_actions:
        long_option = None
        short_option = None
        for b in a.option_strings:
            if b.startswith("--"):
                long_option = b[2:]
            else:
                short_option = b[1:]

        line = "complete -c quizml"
        if short_option:
            line = line + " -s " + short_option
        if long_option:
            line = line + " -l " + long_option

        if long_option == "docs":
            line = f'{line:<50} -d "{a.help}" -a "{docs_topics}"'
        elif long_option == "shell-completion":
            line = f'{line:<50} -d "{a.help}" -a "bash zsh fish"'
        else:
            line = f'{line:<50} -d "{a.help}"'
        txt = txt + line + "\n"

    txt = txt + 'complete -c quizml -k -x -a "(__fish_complete_suffix .yaml .yml)"\n'
    return txt


def zsh(parser):
    txt = "function _quizml(){\n  _arguments\\\n"
    docs_topics = _get_docs_topics()

    for a in parser._action_groups[1]._group_actions:
        help = a.help.replace("'", r"'\''")
        for b in a.option_strings:
            if b == "--docs":
                txt = (
                    txt
                    + f"    '--docs[display documentation topics]::topic:({docs_topics})' \\\n"
                )
            elif b == "--shell-completion":
                txt = (
                    txt
                    + "    '--shell-completion[print shell completion script for the specified shell]:shell:(bash zsh fish)' \\\n"
                )
            else:
                txt = txt + f"    '{b}[{help}]' \\\n"

    txt = txt + r"    '*:yaml file:_files -g \*.\(yml\|yaml\)'" + "\n}\n"
    return txt
