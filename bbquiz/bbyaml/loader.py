import os
import sys
import yaml
import logging

from . import check_syntax

def load_yaml_file(yaml_filename):
    try:
        with open(yaml_filename) as yaml_file:
            yaml_data = yaml.load(yaml_file, Loader=yaml.FullLoader)
    except yaml.YAMLError as exc:
        logging.error("Error while parsing YAML file")
        if hasattr(exc, 'problem_mark'):
            with open(yaml_filename) as f:
                lines = f.readlines()                
            l = exc.problem_mark.line
            c = exc.problem_mark.column
            ctx = str(exc.context) if exc.context!=None else ''
            print("in {}, line {}, column {}".format(yaml_filename, str(l+1), str(c+1)))
            print("  " + lines[l][0:-1])
            if (c > 4):
                print("  " + "~"*(c-1) + "^")
            else:
                print("  " + " "*(c-1) + "^~~~~")
                
            print("Parsing Error: " + str(exc.problem) + ctx )
        else:
            print ("Something went wrong while parsing yaml file")
        pass

    return yaml_data


def load(bbyaml_filename):
    yaml_data = load_yaml_file(bbyaml_filename)
    check_syntax.check_bbyaml_syntax(yaml_data)

    return yaml_data

    
