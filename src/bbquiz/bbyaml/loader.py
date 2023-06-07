import os
import sys
from pathlib import Path

from bbquiz.bbyaml.utils import filter_yaml

import strictyaml
from strictyaml import Any, Map, Float, Seq, Bool, Int, Str, Optional, MapCombined
from strictyaml import YAMLError

class BBYamlSyntaxError(Exception):
    pass



def load(bbyaml_filename):

    schema_overall = Seq(MapCombined({"type": Str()},
                                     Str(), Any()))
    
    schema_item = {
        'ma': Map({"type": Str(),
                   Optional("marks"): Float(),
                   "question": Str(),
                   "answers": Seq(
                       Map({ "answer": Str(),
                             "correct": Bool()}))}),
        'mc': Map({"type": Str(),
                   Optional("marks"): Float(),
                   "question": Str(),
                   "answers": Seq(
                       Map({ "answer": Str(),
                             "correct": Bool()}))}),
        'essay': Map({"type": Str(),
                      Optional("marks"): Float(),
                      "question": Str(),
                      Optional("answer"): Str()}),
        'matching': Map({"type": Str(),
                      Optional("marks"): Float(),
                      "question": Str(),
                      "answers": Seq(Map({"answer": Str(), "correct": Str()}))}),
        'ordering': Map({"type": Str(),
                      Optional("marks"): Float(),
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
        
    yaml_data = yamldoc.data

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

