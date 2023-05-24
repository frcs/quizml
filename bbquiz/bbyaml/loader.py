import os
import sys
import yaml
import logging

from . import check_syntax
from .check_syntax import BBYamlSyntaxError
from ..utils import *


def load_yaml_file(yaml_filename):
    try:
        with open(yaml_filename) as yaml_file:
            yaml_data = yaml.load(yaml_file, Loader=yaml.FullLoader)
    except yaml.YAMLError as exc:
        #        logging.error("Error while parsing YAML file")
        if hasattr(exc, 'problem_mark'):
            with open(yaml_filename) as f:
                lines = f.readlines()                
            l = exc.problem_mark.line
            c = exc.problem_mark.column
            ctx = str(exc.context) if exc.context!=None else ''

            msg = f"in {yaml_filename}, line {l+1}, column {c+1}:\n\n"
            msg = msg + "  " + lines[l][0:-1] + "\n"
            if (c > 4):
                msg = msg + "  " + "~"*(c-1) + "^" + "\n"
            else:
                msg = msg + "  " + " "*(c-1) + "^~~~~" + "\n"
                
            msg = msg + "\nParsing Error: \n" + str(exc.problem) + "\n" + ctx + "\n"
            print_box("Syntax Error", msg, Fore.RED)

            raise BBYamlSyntaxError
        else:
            print ("Something went wrong while parsing yaml file")
            raise BBYamlSyntaxError
            
        pass

    return yaml_data


def load(bbyaml_filename):
    yaml_data = load_yaml_file(bbyaml_filename)
    check_syntax.check_bbyaml_syntax(yaml_data)

    # add header if it doesn't already exist
    if (not yaml_data) or (yaml_data[0]['type'] != 'header'):
        yaml_data.insert(0, {'type': 'header'})

    # add basename metadata to header 
    (basename, _) = os.path.splitext(bbyaml_filename)
    yaml_data[0]['inputbasename'] = basename
    
    return yaml_data

    
