
import sys
import os
from colorama import Fore, Back, Style
import textwrap


def text_wrap(msg):
    w, _ = os.get_terminal_size(0)
    return textwrap.fill(msg, w-5)


def print_context_line(lines, lineo, charno=None, highlight=False):
    if (lineo < 1 or lineo > len(lines)):
        return ""    
    if highlight:
        s = Fore.RED + "❱" + Fore.RESET + f"{lineo:>4} " + Style.DIM + " │ " + Style.RESET_ALL + lines[lineo-1] + "\n"
    else:
        s = Style.DIM + " " + f"{lineo:>4}" + lines[lineo-1] +  Style.RESET_ALL + "\n"
    return s

def print_context(lines, lineo, charno=None):

    msg = print_context_line(lines, lineo-1, charno, highlight=False);
    msg = msg + print_context_line(lines, lineo, charno, highlight=True);
    msg = msg + print_context_line(lines, lineo+1, charno, highlight=False);
   
    return msg

def print_box(title, msg, color=Fore.MAGENTA):

    w, _ = os.get_terminal_size(0)
    title = " " + title + " "
    sys.stdout.write(color + "╭" + title.center(w - 2, "─") + "╮" + '\033[0m\n')

    for line in msg.splitlines():
        if len(line) > w - 4 :
            line = line[0:(w - 5)] + '…'
            
        sys.stdout.write(color + "│ " + '\033[0m'
                         +  line[:].ljust(w - 4)
                         + color + " │" + '\033[0m\n')
    sys.stdout.write(color + "╰" + "─"*(w - 2) + "╯" + '\033[0m\n')           



