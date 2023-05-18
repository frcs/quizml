import os
import jinja2
from pathlib import Path

from bbquiz.utils import *


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
        template = jinja2.Environment(
            comment_start_string  ='<#',
            comment_end_string    ='#>',
            block_start_string    ='<|',
            block_end_string      ='|>',
            variable_start_string ='<<',
            variable_end_string   ='>>').from_string(template_file.read())

        latex_content = jinja2.Template(template_file.read()).render(context)
    return latex_content
    
        


