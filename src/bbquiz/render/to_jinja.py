import os
import jinja2
from pathlib import Path
from rich.panel import Panel

from colorama import Fore, Back, Style
import textwrap

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
        s = Fore.RED + "❱" + Fore.RESET + f"{lineo:>4} " + Style.DIM + " │ " + Style.RESET_ALL + lines[lineo-1] + "\n"
    else:
        s = Style.DIM + " " + f"{lineo:>4}" + lines[lineo-1] +  Style.RESET_ALL + "\n"
    return s

def msg_context(lines, lineo, charno=None):
    msg = msg_context_line(lines, lineo-1, charno, highlight=False);
    msg = msg + msg_context_line(lines, lineo, charno, highlight=True);
    msg = msg + msg_context_line(lines, lineo+1, charno, highlight=False);
    return msg

def render(yaml_data, template_filename):

    if not template_filename:
        print(Panel("Template filename is missing, can't render jinja.",
                    title="Error",border_style="red"))
        raise Exception

    (header, questions) = get_header_questions(yaml_data)
    
    context = {
        "header"      : header,
        "questions"   : questions,
        "total_marks" : get_total_marks(yaml_data)
    }  
   
    with open(template_filename, 'r') as template_file:
        try:
            template_src = template_file.read();
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
            msg = "in " + Fore.YELLOW + template_filename + Fore.RESET + f", line {l}\n\n"
            msg = msg + msg_context(lines, l) + "\n"
            msg = msg + text_wrap(exc.message)
            print(Panel(msg, "Template Syntax Error",border_style="red"))
            raise Jinja2SyntaxError
            
        except jinja2.UndefinedError as exc:
            msg = "in " + Fore.YELLOW + template_filename + Fore.RESET + "\n\n"
            msg = msg + exc.message + "\n\n"
            msg = msg + "The template tries to access an undefined variable. "
            msg = msg + "Have you checked if the header exits? \n\n"
            print(Panel(msg, "Template Error",border_style="red"))                       
            raise Jinja2SyntaxError

        except jinja2.TemplateError as exc:
            msg = "in " + Fore.YELLOW + template_filename + Fore.RESET + "\n\n"
            msg = msg + exc.message + "\n\n"
            print(Panel(msg, "Template Error",border_style="red"))                        
            raise Jinja2SyntaxError
            
        except Exception as exc:
            msg = "in " + Fore.YELLOW + template_filename + Fore.RESET + "\n\n"
            msg = msg + "%s" % exc + "\n\n"
            print(Panel(msg, "Template Exception",border_style="red"))
            raise Jinja2SyntaxError
               
        return latex_content
    
        
    return ''


