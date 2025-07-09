import argparse

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
    txt = "function _bbquiz(){\n  _arguments\n"
    for a in parser._action_groups[1]._group_actions:
        for b in a.option_strings:
            txt = txt + f"    '{b}[{a.help}]' \\\n"

    txt = txt + "    '*:yaml file:_files -g \\*.\\(yml\|yaml\\)'\n}"
    return txt



# ## not correctly implemented
# def bash():
#     return (
# """
#     _bbquiz()
# {
#     # init bash-completion's stuff
#     _init_completion || return

#     # fill COMPREPLY using bash-completion's routine
#     _filedir '@(yaml|yml)'
# }
# complete -F _bbquiz bbquiz
# """)

# def zsh():
#     return ( 
# """
# function _bbquiz(){
#   _arguments \\
#     "-h[Show help information]"\\
#     "--help[Show help information]"\\
#     "-w[continuously watch for file updates and recompile on change]"\\
#     "--watch[continuously watch for file updates and recompile on change]"\\
#     "-v[version]"\\
#     "--version[version]"\\
#     "--zsh[A helper command used for exporting the command completion code in zsh]"\\
#     "--fish[A helper command used for exporting the command completion code in fish]"\\
# '*:yaml file:_files -g \\*.\\(yml\|yaml\\)'
# }

# compdef _bbquiz bbquiz
# """)


# def fish():
#     return ( 
# """
# complete -c bbquiz -s h -l help     -d 'show help information' 
# complete -c bbquiz -s v -l version  -d 'version' 
# complete -c bbquiz -l debug         -d 'Print lots of debugging statements' 
# complete -c bbquiz -l verbose       -d 'set verbose on' 
# complete -c bbquiz -l quiet         -d 'turn off info statements'
# complete -c bbquiz -l target-list   -d 'lits all targets in config file'
# complete -c bbquiz -s w -l watch    -d 'continuously watch for file updates and recompile on change'
# complete -c bbquiz -l zsh           -d 'A helper command used for exporting the command completion code in zsh'
# complete -c bbquiz -l fish          -d 'A helper command used for exporting the command completion code in fish'
# complete -c bbquiz -k -x -a "(__fish_complete_suffix .yaml .yml)"
# """)
