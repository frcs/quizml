
import sys
import os
from colorama import Fore, Back, Style


def print_box(title, msg, color=Fore.MAGENTA):

    w, _ = os.get_terminal_size(0)
    
    sys.stdout.write(color + "╭" + title.center(w - 2, "─") + "╮" + '\033[0m\n')

    for line in msg.splitlines():
        if len(line) > w - 4 :
            line = line[0:(w - 4)]
        sys.stdout.write(color + "│ " + '\033[0m' +  line[:].ljust(w - 4) + color + " │" + '\033[0m\n')
    sys.stdout.write(color + "╰" + "─"*(w - 2) + "╯" + '\033[0m\n')           


