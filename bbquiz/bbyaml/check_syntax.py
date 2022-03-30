import os
import sys
import yaml
import logging
from ..utils import *


class BBYamlSyntaxError(Exception):
    pass
  
def syntax_error(msg, entry=None):
    #    logging.error("Syntax Error: " + msg)
    if entry!=None:
        msg = msg + "\n\n" + yaml.dump(entry)

    print_box("Syntax Error: ", msg, color=Fore.RED)

    raise BBYamlSyntaxError

def syntax_warning(msg, entry=None):
    #logging.warning("Syntax Warning: " + msg)

    if entry!=None:
        msg = msg + "\n\n" + yaml.dump(entry)

    print_box("Syntax Warning: ", msg, color=Fore.YELLOW)
   
def check_bbyaml_syntax_ma(entry):
    for k in entry.keys():
        if k not in ['answers', 'question', 'marks', 'type']:
            syntax_warning("unkown key '{}'".format(k), entry)
    if 'answers' not in entry:        
        syntax_error("the question doesn't have 'answers'", entry)
    if 'question' not in entry:
        syntax_error("the question doesn't have 'answers'", entry)
    if type(entry['answers']) != list:
        syntax_error("'answers' should be a list", entry)
    for a in entry['answers']:
        if 'correct' not in a:
            syntax_error("'correct' must be defined for all answers:\n", entry)
        if 'answer' not in a:
            syntax_error("'answer' must be defined for all answers:\n", entry)

def check_bbyaml_syntax_essay(entry):

    for k in entry.keys():
        if k not in ['answer', 'question', 'marks', 'type']:
            syntax_warning("unkown key '{}':\n".format(k), entry)
            
    if 'question' not in entry:        
        syntax_error("the question doesn't have a 'question' field:\n", entry)

    if 'answer' not in entry:        
        syntax_warning("the question doesn't have an 'answer' field:\n", entry)
            
def check_bbyaml_syntax(yaml_data):

    if type(yaml_data) != list:
        syntax_error("this document contains no question")
        raise

    for entry in yaml_data:

        if 'type' not in entry:
            syntax_error("the question doesn't have a 'type'")
            raise

        if entry['type'] not in ['ma', 'essay', 'header']:
            syntax_warning("unkown question type '{}'".format(entry['type']))

        if entry['type'] == 'ma':
            check_bbyaml_syntax_ma(entry)

        if entry['type'] == 'essay':
            check_bbyaml_syntax_essay(entry)

