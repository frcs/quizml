import os
import jinja2
from pathlib import Path

from bbquiz.utils import *
from bbquiz.bbyaml.stats import get_total_marks
from bbquiz.bbyaml.utils import *

class Jinja2SyntaxError(Exception):
    pass
    

def render(yaml_data, template_filename):

    if not template_filename:
        print_box("Error",
                  "Template filename is missing, can't render jinja.",
                  Fore.RED)
        raise Exception

    if not template_filename:
        print_box("Error",
                  f"latex template file not found:  {template_filename}",
                  Fore.RED)
        raise Exception

    (header, questions) = get_header_questions(yaml_data)

    # some weird bug in default jinja2's loader behaviour, so can't use normal way.    
    
    context = {
        "header" : header,
        "questions" : questions,
        "total_marks": get_total_marks(yaml_data)
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
            msg = msg + print_context(lines, l) + "\n"
            msg = msg + text_wrap(exc.message)                        
            print_box("Template Syntax Error", msg, color=Fore.RED)
            raise Jinja2SyntaxError

            
        except jinja2.UndefinedError as exc:
            msg = "in " + Fore.YELLOW + template_filename + Fore.RESET + "\n\n"
            msg = msg + exc.message + "\n\n"
            msg = msg + "The template tries to access an undefined variable. "
            msg = msg + "Have you checked if the header exits? \n\n"
            print_box("TemplateError" , msg, color=Fore.RED)
                        
            raise Jinja2SyntaxError


        except jinja2.TemplateError as exc:
            msg = "in " + Fore.YELLOW + template_filename + Fore.RESET + "\n\n"
            msg = msg + exc.message + "\n\n"
            print_box("TemplateError" , msg, color=Fore.RED)
                        
            raise Jinja2SyntaxError
            
        except Exception as exc:
            msg = "in " + Fore.YELLOW + template_filename + Fore.RESET + "\n\n"
            msg = msg + "%s" % exc + "\n\n"

            print_box("Exception" , msg, color=Fore.RED)
            raise Jinja2SyntaxError
        
        
        return latex_content
    
        
    return ''


