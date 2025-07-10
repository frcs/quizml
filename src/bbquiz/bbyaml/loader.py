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
put values into quotes.

Typical usage example:

    yaml_data = load("quiz.yaml", schema=True)

Note that StrictYAML's validation is a bit slow. Hence schema=False is
also proposed for speed, but will not catch syntax errors and all
key/val will be strings:

    yaml_data_str = load("quiz.yaml", schema=False) # quick


"""

import os
import sys
import re
from pathlib import Path
import strictyaml
from strictyaml import Any, Map, Float, Seq, Bool, Int, Str, Regex
from strictyaml import Optional, MapCombined, ScalarValidator
from strictyaml import YAMLError

from bbquiz.bbyaml.utils import filter_yaml
from bbquiz.exceptions import BBYamlSyntaxError


def load_yaml(bbyaml_txt, schema=True):
    if schema:
        return load_with_schema(bbyaml_txt)
    else:
        return load_without_schema(bbyaml_txt)
       

def load_with_schema(bbyaml_txt):
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
        'ma': MapCombined(
            {
                "type": Str(),
                Optional("marks", default=2.5): Float(),
                Optional("comments"): Str(),                   
                Optional("cols", default=1): Int(),
                "question": Str(),
                "choices": Seq(
                    Map({ Optional("x"): Str(),
                          Optional("o"): Str()}))
            },
            Str(),Any(),
        ),
        'mc': MapCombined(
            {
                "type": Str(),
                Optional("marks", default=2.5): Float(),
                Optional("comments"): Str(),                                      
                Optional("cols", default=1): Int(),                   
                "question": Str(),
                "choices": Seq(
                    Map({ Optional("x"): Str(),
                          Optional("o"): Str()}))
            },
            Str(), Any()),
        'tf': MapCombined(
            {
                "type": Str(),
                Optional("marks", default=2.5): Float(),
                Optional("comments"): Str(),                   
                "question": Str(),
                "answer": Bool(),
            }, Str(), Any()),        
        'essay': MapCombined({
            "type": Str(),
            Optional("comments"): Str(),                                         
            Optional("marks", default=4): Float(),
            "question": Str(),
            Optional("answer"): Str(),
        }, Str(), Any()),        
        'matching': MapCombined({
            "type": Str(),
            Optional("comments"): Str(),                                            
            Optional("marks", default=2.5): Float(),
            "question": Str(),
            "choices": Seq(Map({"A": Str(), "B": Str()})),
        }, Str(), Any()),        
        'ordering': MapCombined({
            "type": Str(),
            Optional("comments"): Str(),                                           
            Optional("marks", default=2.5): Float(),
            Optional("cols", default=1): Int(),                          
            "question": Str(),
            "choices": Seq(Str()),
        }, Str(), Any()),        
        'section': MapCombined({
            "type": Str(),
            Optional("title"): Str(),
            Optional("marks"): Float(),
            Optional("question"): Str(),
        }, Str(), Any()),
        'header': Any()
    }
    
    try:
        yamldoc = strictyaml.load(bbyaml_txt, schema_overall,
                                  label="myfilename")
        
        for a in yamldoc:
            if a['type'] in schema_item.keys():
                a.revalidate(schema_item[a['type']])
            else:            
                # the entered 'type' is not valid 
                # we need to trick the validation system to trigger an error
                # by choosing Map({}) as schema. so any key will fail 
                a.revalidate(Map({})) 
                
    except YAMLError as err:
        raise BBYamlSyntaxError(str(err.problem) + '\n' + str(err.problem_mark))
        
    return yamldoc.data
    

def load_without_schema(bbyaml_txt):
    """fast loading of BBYaml file as a StrictYaml without Schema.

    In this version we do not check the schema. This is for speed
    only. All key/val are interpreted as Strings. This version does
    not catch syntax errors.

    """
    
    schema_overall = Any()

    # strictyaml.load("!!python/name:__main__.someval", Loader=yaml.BaseLoader)
    
    try:
        yamldoc = strictyaml.load(bbyaml_txt, schema_overall, label="myfilename")
    
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

    try:
        bbyaml_txt = Path(bbyaml_filename).read_text()
    except FileNotFoundError:
        raise BBYamlSyntaxError(f"File not found: {bbyaml_filename}")

    yamldoc_pattern = re.compile(r"^---\s*$", re.MULTILINE) 
    yamldocs = yamldoc_pattern.split(bbyaml_txt)    
    yamldocs = list(filter(None, yamldocs))

    if len(yamldocs) > 2:
        raise BBYamlSyntaxError(
            ("Yaml file cannot have more than 2 documents: "
             "the header section and the questions sections"))

    doc = {'header': {}, 'questions': []}

    if len(yamldocs) == 1:
        yamldoc_txt = yamldocs[0]
        # if we find line starting with "- " then it's a list
        # thus this would be the questions
        list_pattern = re.compile(r"^- ", re.MULTILINE)        
        if list_pattern.search(yamldoc_txt):
            doc['questions'] = load_yaml(yamldoc_txt, schema)
        else:
            doc['header'] = load_yaml(yamldoc_txt, schema=False)       

    elif len(yamldocs) == 2:
        doc['header'] = load_yaml(yamldocs[0], schema=False)
        doc['questions'] = load_yaml(yamldocs[1], schema=schema)
    
    # trim all the text entries
    f = lambda a : a.strip() if isinstance(a, str) else a
    doc = filter_yaml(doc, f)
    
    # some backwards compatibility step
    # if header defined as first question then it is merged to header
    if ((len(doc['questions'])>0) and
        ('type' in doc['questions'][0]) and 
        (doc['questions'][0]['type'] == 'header')):
        h = doc['questions'][0]
        del h['type']
        doc['header'].update(h)

    # add basename metadata to header 
    (basename, _) = os.path.splitext(bbyaml_filename)
    doc['header']['inputbasename'] = basename
    
    return doc

