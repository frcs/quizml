import os
import jinja2
from pathlib import Path
from rich.panel import Panel

from colorama import Fore, Back, Style
import textwrap
import pathlib

from bbquiz.bbyaml.stats import get_total_marks
from bbquiz.bbyaml.utils import get_header_questions
from bbquiz.bbyaml.stats import get_total_marks

class Jinja2SyntaxError(Exception):
    pass
    
def text_wrap(msg):
    w, _ = os.get_terminal_size(0)
    return textwrap.fill(msg, w-5)

def msg_context_line(lines, lineo, charno=None, highlight=False):
    if (lineo < 1 or lineo > len(lines)):
        return ""    
    if highlight:
        s = (f"[red]❱[/][bright_white]{lineo:>4} [/]│" +
             "  [bright_white]{lines[lineo-1]}[/]\n")
    else:
        s = f" {lineo:>4} │ {lines[lineo-1]}\n"
    return s

def msg_context(lines, lineo, charno=None):
    msg = msg_context_line(lines, lineo-1, charno, highlight=False);
    msg = msg + msg_context_line(lines, lineo, charno, highlight=True);
    msg = msg + msg_context_line(lines, lineo+1, charno, highlight=False);
    return msg

def render(yaml_data, template_filename):

    if not template_filename:
        msg = "Template filename is missing, can't render jinja."
        raise Exception(msg)

    (header, questions) = get_header_questions(yaml_data)
    
    context = {
        "header"      : header,
        "questions"   : questions,
        "total_marks" : get_total_marks(yaml_data)
    }
   
    try:
        template_src = pathlib.Path(template_filename).read_text()        
        template = jinja2.Environment(
            comment_start_string  ='<#',
            comment_end_string    ='#>',
            block_start_string    ='<|',
            block_end_string      ='|>',
            variable_start_string ='<<',
            variable_end_string   ='>>').from_string(template_src)
        latex_content = template.render(context, debug=True)

    except jinja2.TemplateSyntaxError as exc:
        l = exc.lineno
        name = exc.name
        filename = exc.filename           
        lines = template_src.split("\n")
        msg = f"in [yellow]{template_filename}[/], line {l}\n\n"
        msg = msg + msg_context(lines, l) + "\n"
        msg = msg + text_wrap(exc.message)
        raise Jinja2SyntaxError(msg)
            
    except jinja2.UndefinedError as exc:
        l = exc.lineno
        msg = f"in [yellow]{template_filename}[/], line {l}\n\n"
        msg = msg + exc.message + "\n\n"
        msg = msg + "The template tries to access an undefined variable. "
        msg = msg + "Have you checked if the header exits? \n\n"
        raise Jinja2SyntaxError(msg)

    except jinja2.TemplateError as exc:
        l = exc.lineno
        msg = f"in [yellow]{template_filename}[/], line {l}\n\n"
        msg = msg + exc.message + "\n\n"
        raise Jinja2SyntaxError(msg)
            
    except Exception as exc:
        msg = f"in [yellow]{template_filename}[/]\n\n"
        msg = msg + "%s" % exc + "\n\n"
        raise Jinja2SyntaxError(msg)
               
    return latex_content
            
    return ''
