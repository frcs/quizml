"""BBYaml load file

This module provides the function for loading BBYaml files as a
list/dict structure.

BBYaml files are simply a form of YAML file. YAML has well known
issues. One is the dreaded "Norway problem", where 'country: No' is
translated as 'country: False' because YAML specification assumes
automatic type conversion.

To remidy this, we use StrictYAML, a subset of YAML
(https://pypi.org/project/strictyaml/).

StrictYAML also uses schemas to specify the allowed structure and
expected types. This enables us to validate BBYaml files and parse
syntax errors (throwing BBYamlSyntaxError).

This also avoids any unwanted type conversion and avoids us having to
put values into quotes. For instance,

    - answer: yes
      correct: false

will be correctly understood as answer="yes" and correct=False.

Typical usage example:

    yaml_data = load("quiz.yaml", schema=True)

Note that StrictYAML's validation is a bit slow. Hence schema=False is
also proposed for speed, but will not catch syntax errors and all
key/val will be strings:

    yaml_data_str = load("quiz.yaml", schema=False) # quick

but 
    - answer: yes
      correct: false

will then be understood as answer="yes" and correct="False".


"""

import os
import sys
from pathlib import Path
import strictyaml
from strictyaml import Any, Map, Float, Seq, Bool, Int, Str, Optional, MapCombined
from strictyaml import YAMLError

from bbquiz.bbyaml.utils import filter_yaml

class BBYamlSyntaxError(Exception):
    pass


def load_with_schema(bbyaml_filename):
    """load a BBYaml file as a StrictYaml with Schema.

    We need to have a two-pass approach: the first pass checks that we
    have a sequence with each element containing a 'type' key. Then,
    in a second pass, we re-validate each item of the list with a
    specialised secondary Schema.

    This version is significantly slower than the no-schema version
    but does catch syntax errors.

    """
    
    schema_overall = Seq(MapCombined({"type": Str()},
                                     Str(), Any()))
    
    schema_item = {
        'ma': Map({"type": Str(),
                   Optional("marks", default=2.5): Float(),
                   Optional("comments"): Str(),                   
                   "question": Str(),
                   "answers": Seq(
                       Map({ "answer": Str(),
                             "correct": Bool()}))}),
        'mc': Map({"type": Str(),
                   Optional("marks", default=2.5): Float(),
                   Optional("comments"): Str(),                                      
                   "question": Str(),
                   "answers": Seq(
                       Map({ "answer": Str(),
                             "correct": Bool()}))}),
        'essay': Map({"type": Str(),
                      Optional("comments"): Str(),                                         
                      Optional("marks", default=4): Float(),
                      "question": Str(),
                      Optional("answer"): Str()}),
        'matching': Map({"type": Str(),
                      Optional("comments"): Str(),                                            
                      Optional("marks", default=2.5): Float(),
                      "question": Str(),
                      "answers": Seq(Map({"answer": Str(), "correct": Str()}))}),
        'ordering': Map({"type": Str(),
                      Optional("comments"): Str(),                                           
                      Optional("marks", default=2.5): Float(),
                      "question": Str(),
                      "answers": Seq(Map({"answer": Str()}))}),
        'section': Map({"type": Str(),
                        Optional("title"): Str(),
                        Optional("marks"): Float(),
                        Optional("question"): Str()}),
        'header': Any()
    }

    yaml_txt = Path(bbyaml_filename).read_text()
    
    try:
        yamldoc = strictyaml.load(yaml_txt, schema_overall, label="myfilename")
        
        for a in yamldoc:
            if a['type'] in schema_item.keys():
                a.revalidate(schema_item[a['type']])
            else:            
                # entered 'type' is not valid 
                # we trick the validation system to trigger an error
                # by choosing Map({}) as schema. so any key will fail 
                a.revalidate(Map({})) 
                
    except YAMLError as err:
        raise BBYamlSyntaxError(str(err.problem) + '\n' + str(err.problem_mark) )
        
    return yamldoc.data
    

def load_without_schema(bbyaml_filename):
    """fast loading of BBYaml file as a StrictYaml without Schema.

    In this version we do not check the schema. This is for speed
    only. All key/val are interpreted as Strings. This version does
    not catch syntax errors.

    """
    
    schema_overall = Any()

    yaml_txt = Path(bbyaml_filename).read_text()

    try:
        yamldoc = strictyaml.load(yaml_txt, schema_overall, label="myfilename")
    
    except YAMLError as err:
        raise BBYamlSyntaxError(str(err.problem) + '\n' + str(err.problem_mark) )
        
    return yamldoc.data
    


def load(bbyaml_filename, schema=True):
    """load a BBYaml file as a StrictYaml file. 

    We use StrictYAML (https://pypi.org/project/strictyaml/) because
    we can establish a schema and specify the expected types (so that
    we can avoid the dreaded "Norway problem", where 'country: No' is
    translated as 'country: False').

    If schema=True, we explicitely set the possible keys and their
    types. Hence all statements/answers, etc., are, by default
    strings, marks are floats, etc.

    Note that StrictYAML's validation is a bit slow. Hence
    schema=False is proposed for speed, but will not catch syntax
    errors.

    """

    if (schema):
        yaml_data = load_with_schema(bbyaml_filename)
    else:
        yaml_data = load_without_schema(bbyaml_filename)
    
    # trim all the text entries
    f = lambda a : a.strip() if isinstance(a, str) else a
    yaml_data = filter_yaml(yaml_data, f)
    
    # add header if it doesn't already exist
    if (not yaml_data) or (yaml_data[0]['type'] != 'header'):
        yaml_data.insert(0, {'type': 'header'})

    # add basename metadata to header 
    (basename, _) = os.path.splitext(bbyaml_filename)
    yaml_data[0]['inputbasename'] = basename
    
    return yaml_data

