import argparse
from shlex import quote

def bash(parser):
    opts_list = []
    for a in parser._action_groups[1]._group_actions:
        for b in a.option_strings:
            opts_list.append(b)
    
    opts = " ".join(opts_list)
    
    txt = f"""_quizml()
{{
    local cur prev opts
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    opts="{opts}"

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
    for a in parser._action_groups[1]._group_actions:
        l = None
        s = None
        for b in a.option_strings:
            if b.startswith('--'):
                l = b[2:]
            else:
                s = b[1:]

        line = "complete -c quizml"
        if s:
            line = line + " -s " + s
        if l:
            line = line + " -l " + l

        line = f"{line:<50} -d \"{a.help}\""    
        txt = txt + line + "\n" 

    txt = txt + 'complete -c quizml -k -x -a "(__fish_complete_suffix .yaml .yml)"\n'
    return txt



def zsh(parser):
    txt = "function _quizml(){\n  _arguments\\\n"
    for a in parser._action_groups[1]._group_actions:
        help = a.help.replace("'", r"'\''")
        for b in a.option_strings:            
            txt = txt + f"    '{b}[{help}]' \\\n"

    txt = txt + r"    '*:yaml file:_files -g \*.\(yml\|yaml\)'" + "\n}\n"
    return txt

