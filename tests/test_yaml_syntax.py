from pathlib import Path
import os
import strictyaml
from quizml.loader import load

def test_yaml_syntax():
    
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-basic-syntax.yaml")
    basename = os.path.join(pkg_dirname, "test-basic-syntax")
    
    yamldata = [{"type": "essay",
                     "marks": 4.0,
                     "question": "answer this question",
                     "answer": "some very long answer",
                     },
                    {"type": "ma",
                     "marks": 2.5,
                     "question": "some multiple answer question",
                     "choices": [{"x": "A"},
                                 {"o": "B"},
                                 {"x": "C"},
                                 {"o": "D"}
                                 ],
                     "cols": 1},
                    {"type": "mc",
                     "marks": 2.5,
                     "question": "some multiple choice question",
                     "choices": [{"o": "A"},
                                 {"o": "B"},
                                 {"x": "C"},
                                 {"o": "D"}
                                 ],
                     "cols": 1},
                    {"type": "matching",
                     "marks": 2.5,
                     "question": "some matching question",
                     "choices": [{"A": "1", "B": "2"},
                                 {"A": "3", "B": "4"}
                                 ],
                     },
                    {"type": "ordering",
                     "marks": 2.5,
                     "question": "some ordering question",
                     "choices": ["A", "B", "C", "D"],
                     "cols": 1},
                    ]
    #    yaml_txt = Path(.read_text()
   
    yamldoc = load(yaml_file)
    # print(yamldoc['questions'])
    # print(yamldata)

    assert(yamldoc['questions'] == yamldata)
    # print(yamldoc)
    # print(yamldata)
        
