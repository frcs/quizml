import argparse
from pathlib import Path


def _get_docs_topics() -> str:
    try:
        from quizml.cli.docs import get_docs_dir, parse_sidebar

        docs_dir = get_docs_dir()
        items = parse_sidebar(docs_dir)
        topics = ["all", "list", "overview"]
        for item in items:
            topics.append(item.path.stem.lower())
        return " ".join(sorted(set(topics)))
    except Exception:
        return "all list overview quickstart usage syntax_yaml syntax_questions targets"


def _get_available_templates() -> list[str]:
    try:
        from quizml.filelocator import locate

        templates = set()
        for d in [locate.pkg_template_dir, locate.user_template_dir, locate.local_template_dir]:
            p = Path(d)
            if p.is_dir():
                for f in p.glob("*"):
                    if f.is_file() and (f.suffix == ".docx" or f.name.endswith(".j2")):
                        templates.add(f.name)
        return sorted(templates)
    except Exception:
        return [
            "blackboard.txt.j2",
            "preview.html.j2",
            "prototype.docx",
            "stats.txt.j2",
            "tcd-exam-solutions.tex.j2",
            "tcd-exam.tex.j2",
        ]


def bash(parser):
    opts_list = []
    for a in parser._action_groups[1]._group_actions:
        for b in a.option_strings:
            opts_list.append(b)

    opts = " ".join(opts_list)
    docs_topics = _get_docs_topics()
    templates_str = " ".join(_get_available_templates())

    txt = f"""_quizml()
{{
    local cur prev opts docs_topics render_templates
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    opts="{opts}"
    docs_topics="{docs_topics}"
    render_templates="{templates_str}"

    if [[ ${{prev}} == "--docs" ]] ; then
        COMPREPLY=( $(compgen -W "${{docs_topics}}" -- ${{cur}}) )
        return 0
    fi

    if [[ ${{prev}} == "--render" ]] ; then
        COMPREPLY=( $(compgen -W "${{render_templates}}" -- ${{cur}}) $(compgen -f -X "!*.j2" -- ${{cur}}) $(compgen -f -X "!*.docx" -- ${{cur}}) )
        return 0
    fi

    if [[ ${{prev}} == "--transcode" ]] ; then
        COMPREPLY=( $(compgen -W "latex html html-svg html-mathml" -- ${{cur}}) )
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


DOCS_FALLBACK_DESCRIPTIONS = {
    "all": "Full documentation guide",
    "list": "List available topics",
    "overview": "Architecture and workflow overview",
    "quickstart": "Quick start tutorial",
    "usage": "Command-line usage reference",
    "syntax_yaml": "Quiz YAML document syntax",
    "syntax_questions": "Question syntax and types",
    "targets": "Build targets and formats",
}

BUILTIN_TEMPLATE_DESCRIPTIONS = {
    "blackboard.txt.j2": "Blackboard quiz format",
    "preview.html.j2": "HTML test preview",
    "prototype.docx": "Word document (docx)",
    "stats.txt.j2": "Quiz statistics summary",
    "tcd-exam.tex.j2": "TCD LaTeX exam paper",
    "tcd-exam-solutions.tex.j2": "TCD LaTeX exam solutions",
}


def _get_docs_topics_with_descriptions() -> list[tuple[str, str]]:
    topics = dict(DOCS_FALLBACK_DESCRIPTIONS)
    try:
        from quizml.cli.docs import get_docs_dir, parse_sidebar

        docs_dir = get_docs_dir()
        items = parse_sidebar(docs_dir)
        for item in items:
            slug = item.path.stem.lower()
            title = item.title.replace("&", "and").replace('"', r"\"").replace("'", "")
            topics[slug] = title
    except Exception:
        pass
    return sorted(topics.items())


def fish(parser):
    docs_items = _get_docs_topics_with_descriptions()
    docs_printf_args = " \\\n        ".join(
        f'{slug} "{desc}"' for slug, desc in docs_items
    )

    templates = _get_available_templates()
    template_pairs = []
    for t in templates:
        desc = BUILTIN_TEMPLATE_DESCRIPTIONS.get(
            t, "Jinja2 template" if t.endswith(".j2") else "Word template"
        )
        template_pairs.append(f'{t} "{desc}"')
    templates_printf_args = " \\\n        ".join(template_pairs)

    txt = f"""# quizml fish completion
complete -e -c quizml

function __fish_quizml_shells
    printf "%s\\t%s\\n" \\
        bash "Bash completion script" \\
        fish "Fish completion script" \\
        zsh "Zsh completion script"
end

function __fish_quizml_transcode_formats
    printf "%s\\t%s\\n" \\
        latex "LaTeX markup" \\
        html "HTML markup" \\
        html-svg "HTML with SVG equations" \\
        html-mathml "HTML with MathML equations"
end

function __fish_quizml_docs
    printf "%s\\t%s\\n" \\
        {docs_printf_args}
end

function __fish_quizml_templates
    printf "%s\\t%s\\n" \\
        {templates_printf_args}
    for f in *.j2 *.docx quizml-templates/*.j2 quizml-templates/*.docx
        if test -f "$f"
            printf "%s\\t%s\\n" (basename "$f") "Custom template"
        end
    end
    set -l token (commandline -ct)
    if string match -q "*/*" -- $token
        for f in $token*.j2 $token*.docx
            if test -f "$f"
                printf "%s\\t%s\\n" "$f" "Template file"
            end
        end
        for d in $token*/
            if test -d "$d"
                echo "$d"
            end
        end
    end
end
"""

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

        help_desc = (a.help or "").replace('"', r"\"")

        if long_option == "docs":
            line = f'{line:<50} -x -d "{help_desc}" -a "(__fish_quizml_docs)"'
        elif long_option == "shell-completion":
            line = f'{line:<50} -x -d "{help_desc}" -a "(__fish_quizml_shells)"'
        elif long_option == "render":
            line = f'{line:<50} -x -d "{help_desc}" -a "(__fish_quizml_templates)"'
        elif long_option == "transcode":
            line = f'{line:<50} -x -d "{help_desc}" -a "(__fish_quizml_transcode_formats)"'

        elif a.nargs != 0 and not isinstance(
            a,
            (
                argparse._StoreTrueAction,
                argparse._StoreFalseAction,
                argparse._CountAction,
                argparse._HelpAction,
                argparse._VersionAction,
            ),
        ):
            line = f'{line:<50} -r -d "{help_desc}"'
        else:
            line = f'{line:<50} -d "{help_desc}"'
        txt = txt + line + "\n"

    txt = txt + 'complete -c quizml -k -x -a "(__fish_complete_suffix .yaml .yml)"\n'
    return txt



def zsh(parser):
    docs_topics = _get_docs_topics()
    templates = _get_available_templates()
    templates_str = " ".join(templates)

    txt = f"""#compdef quizml

(( $+functions[_quizml_templates] )) ||
_quizml_templates() {{
  local -a templates
  templates=({templates_str})
  templates+=( *.(j2|docx)(N) )
  if [[ -d quizml-templates ]]; then
    templates+=( quizml-templates/*.(j2|docx)(N:t) )
  fi
  _describe -t templates "template" templates
}}

function _quizml(){{
  _arguments\\
"""

    for a in parser._action_groups[1]._group_actions:
        help = a.help.replace("'", r"'\''")
        for b in a.option_strings:
            if b == "--docs":
                txt = (
                    txt
                    + f"    '--docs[display documentation topics]:topic:({docs_topics})' \\\n"
                )
            elif b == "--shell-completion":
                txt = (
                    txt
                    + "    '--shell-completion[print shell completion script for the specified shell]:shell:(bash zsh fish)' \\\n"
                )
            elif b == "--render":
                txt = (
                    txt
                    + f"    '--render[{help}]:template:_quizml_templates' \\\n"
                )
            elif b == "--transcode":
                txt = (
                    txt
                    + f"    '--transcode[{help}]:format:(latex html html-svg html-mathml)' \\\n"
                )
            else:
                txt = txt + f"    '{b}[{help}]' \\\n"

    txt = (
        txt
        + r"    '*:yaml file:_files -g \*.\(yml\|yaml\)'"
        + "\n}\n\n"
        + 'if [ "$funcstack[1]" = "_quizml" ]; then\n'
        + '    _quizml "$@"\n'
        + "else\n"
        + "    compdef _quizml quizml\n"
        + "fi\n"
    )
    return txt
