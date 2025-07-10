import argparse
from shlex import quote

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

        line = "complete -c bbquiz"
        if s:
            line = line + " -s " + s
        if l:
            line = line + " -l " + l

        line = f"{line:<50} -d \"{a.help}\""    
        txt = txt + line + "\n" 

    txt = txt + 'complete -c bbquiz -k -x -a "(__fish_complete_suffix .yaml .yml)"\n'
    return txt



def zsh(parser):
    txt = "function _bbquiz(){\n  _arguments\\\n"
    for a in parser._action_groups[1]._group_actions:
        help = a.help.replace("'", r"'\''")
        for b in a.option_strings:            
            txt = txt + f"    '{b}[{help}]' \\\n"

    txt = txt + "    '*:yaml file:_files -g \\*.\\(yml\|yaml\\)'\n}"
    return txt

