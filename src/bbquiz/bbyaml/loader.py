import os
import sys
from pathlib import Path

from bbquiz.bbyaml.utils import filter_yaml

import strictyaml
from strictyaml import Any, Map, Float, Seq, Bool, Int, Str, Optional, MapCombined
from strictyaml import YAMLError

class BBYamlSyntaxError(Exception):
    pass


def load_no_schema(bbyaml_filename):
    """We use StrictYAML (https://pypi.org/project/strictyaml/)
    because we can establish a schema and specify the expected types
    (so that we can avoid the dreaded "Norway problem").

    In this version we do not check the schema. This is for speed only.
    """
    
    schema_overall = Any()

    yaml_txt = Path(bbyaml_filename).read_text()

    try:
        yamldoc = strictyaml.load(yaml_txt, schema_overall, label="myfilename")
    
    except YAMLError as err:
        raise BBYamlSyntaxError(str(err.problem) + '\n' + str(err.problem_mark) )
        
    yaml_data = yamldoc.data

    # rest is same as in load function 
    
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


def load_schema(bbyaml_filename):
    """The parsing of the StrictYaml file is done via a Schema.

    We need to have a two-pass approach: the first pass checks that we
    have a sequence with each element containing a 'type' key. Then,
    in a sceond pass, we re-validate each item of the list with a
    specialised secondary Schema.

    This version is significantly slower than the no-schema version.

    """
    
    schema_overall = Seq(MapCombined({"type": Str()},
                                     Str(), Any()))
    
    schema_item = {
        'ma': Map({"type": Str(),
                   Optional("marks", default=2.5): Float(),
                   "question": Str(),
                   "answers": Seq(
                       Map({ "answer": Str(),
                             "correct": Bool()}))}),
        'mc': Map({"type": Str(),
                   Optional("marks", default=2.5): Float(),
                   "question": Str(),
                   "answers": Seq(
                       Map({ "answer": Str(),
                             "correct": Bool()}))}),
        'essay': Map({"type": Str(),
                      Optional("marks", default=4): Float(),
                      "question": Str(),
                      Optional("answer"): Str()}),
        'matching': Map({"type": Str(),
                      Optional("marks", default=2.5): Float(),
                      "question": Str(),
                      "answers": Seq(Map({"answer": Str(), "correct": Str()}))}),
        'ordering': Map({"type": Str(),
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
                # tricking the validation system to trigger an error
                # by choosing Map({}) as schema. so any key will fail 
                a.revalidate(Map({})) 
                
    except YAMLError as err:
        raise BBYamlSyntaxError(str(err.problem) + '\n' + str(err.problem_mark) )
        
    return yamldoc.data
    

def load_noschema(bbyaml_filename):
    """loading the StrictYAML file without any schema.

    In this version, all keys/vals are, by default, interpreted as
    Strings.

    """
    
    schema_overall = Any()

    yaml_txt = Path(bbyaml_filename).read_text()

    try:
        yamldoc = strictyaml.load(yaml_txt, schema_overall, label="myfilename")
    
    except YAMLError as err:
        raise BBYamlSyntaxError(str(err.problem) + '\n' + str(err.problem_mark) )
        
    return yamldoc.data
    


def load(bbyaml_filename, schema=true):
    """We use StrictYAML (https://pypi.org/project/strictyaml/)
    because we can establish a schema and specify the expected types
    (so that we can avoid the dreaded "Norway problem", where 'coutry:
    no' is translated as 'coutry: False'). Here, we explicitely set
    the types for each key. Hence all statements/answers, etc., are,
    by default strings.

    Note that StrictYAML's validation is a bit slow. Hence
    load_no_schema is proposed for speed, but will not catch syntax
    errors.

    """

    if (schema):
        yaml_data = load_schema(bbyaml_filename)
    else:
        yaml_data = load_no_schema(bbyaml_filename)
        
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

