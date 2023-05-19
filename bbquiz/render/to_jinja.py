import os
import jinja2
from pathlib import Path

from bbquiz.utils import *


class Jinja2SyntaxError(Exception):
    pass


def get_header_info(yaml_data):
    header = None
    for entry in yaml_data:
        if entry['type'] == 'header':
            header = yaml_data[0]
            break
    return header


def get_solutions(yaml_data):
    solutions = []
    for entry in yaml_data:
        if entry['type'] == 'essay':
            solutions.append({'type': 'essay'})
        if entry['type'] == 'ma':
            s = []
            for a in entry['answers']:
                s.append(a['correct'])
            solutions.append({'type': 'ma', 'solutions': s})
        if entry['type'] == 'matching':
            s = []
            for a in entry['answers']:
                s.append(a['correct'])
            solutions.append({'type': 'ma', 'solutions': s})

    return solutions


    

def render(yaml_data, template_filename=''):
      

    if not template_filename:
        dirname = os.path.dirname(__file__)
        template_filename = os.path.join(
            dirname, '../templates/tcd-eleceng-latex.jinja')
    
    if not os.path.exists(template_filename):
        print_box("Error", f"latex template file not found:  {template_filename}", color=Fore.RED)
        return ''

    header_info = get_header_info(yaml_data)

    # some weird bug in default jinja2's loader behaviour, so can't use normal way. 
    


    
    context = {
        "header" : header_info,
        "questions" : yaml_data[1:]
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
        
        # try:
        #     latex_content = template.render(context, debug=True)


        # except jinja2.TemplateSyntaxError as exc:
        #     error_context.update(filename=exc.filename, line_no=exc.lineno)
        #     error_message = exc.message
        #     print(error_message)            
        # except jinja2.TemplateError as exc:
        #     error_message = exc.message
        #     print(error_message)            
        # except Exception as exc:
        #     error_message = "%s" % exc
        #     print(error_message)            

        
        return latex_content
    
        
    return ''


