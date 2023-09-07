## not correctly implemented
def bash():
    return (
"""
    _bbquiz()
{
    # init bash-completion's stuff
    _init_completion || return

    # fill COMPREPLY using bash-completion's routine
    _filedir '@(yaml|yml)'
}
complete -F _bbquiz bbquiz
""")

def zsh():
    return ( 
"""
function _bbquiz(){
  _arguments \\
    "-h[Show help information]"\\
    "--help[Show help information]"\\
    "-w[continuously watch for file updates and recompile on change]"\\
    "--watch[continuously watch for file updates and recompile on change]"\\
    "-v[version]"\\
    "--version[version]"\\
    "--zsh[A helper command used for exporting the command completion code in zsh]"\\
    "--fish[A helper command used for exporting the command completion code in fish]"\\
'*:yaml file:_files -g \\*.\\(yml\|yaml\\)'
}

compdef _bbquiz bbquiz
""")


def fish():
    return ( 
"""
complete -c bbquiz -s h -l help     -d 'show help information' 
complete -c bbquiz -s v -l version  -d 'version' 
complete -c bbquiz -s w -l watch    -d 'continuously watch for file updates and recompile on change'
complete -c bbquiz -l zsh           -d 'A helper command used for exporting the command completion code in zsh'
complete -c bbquiz -l fish          -d 'A helper command used for exporting the command completion code in fish'
complete -c bbquiz -k -x -a "(__fish_complete_suffix .yaml .yml)"
""")
