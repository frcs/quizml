from pathlib import Path
import os
import strictyaml
from strictyaml import Any, Map, Float, Seq, Bool, Int, Str, Optional, MapCombined
from strictyaml import YAMLError

from bbquiz.bbyaml.loader import load

def test_bbyaml_syntax():
    
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "test-basic-syntax.yaml")
    basename = os.path.join(pkg_dirname, "test-basic-syntax")
    
    yamldata = [ {"type": "header",
                  "a": "true",
                  "e": ["A", "B", "C"],
                  'inputbasename': basename},
                 {"type": "essay",
                  "question": "another matching question",
                  "answer": "some very long answer" },
                 {"type": "ma",
                  "marks": 2.5,
                  "question": "some multiple answer question",
                  "answers": [{"answer": "A", "correct": True  },
                              {"answer": "B", "correct": False },
                              {"answer": "C", "correct": True  },
                              {"answer": "D", "correct": False }
                              ]},
                 {"type": "mc",
                  "marks": 2.5,
                  "question": "some multiple choice question",
                  "answers": [{"answer": "A", "correct": False },
                              {"answer": "B", "correct": False },
                              {"answer": "C", "correct": True  },
                              {"answer": "D", "correct": False }
                              ]},
                 {"type": "matching",
                  "marks": 2.5,
                  "question": "some matching question",
                  "answers": [{"answer": "A", "correct": "1" },
                              {"answer": "B", "correct": "2" },
                              {"answer": "C", "correct": "3" },
                              {"answer": "D", "correct": "4" }
                              ]},
                 {"type": "ordering",
                  "marks": 2.5,
                  "question": "some ordering question",
                  "answers": [{"answer": "A" },
                              {"answer": "B" },
                              {"answer": "C" },
                              {"answer": "D" }
                              ]}

                ]

    #    yaml_txt = Path(.read_text()
   
    yamldoc = load(yaml_file)
    assert(yamldoc == yamldata)
    print(yamldoc)
    print(yamldata)
        
