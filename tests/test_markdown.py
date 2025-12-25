
import sys
from pathlib import Path
import os
import strictyaml
from strictyaml import Any, Map, Float, Seq, Bool, Int, Str, Optional, MapCombined
from strictyaml import YAMLError

from quizml.loader import load

from quizml.markdown.markdown import QuizMLYAMLMarkdownTranscoder


def test_quizmlyaml_syntax(capsys):
    
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "fixtures", "test-markdown.yaml")
    basename = os.path.join(pkg_dirname, "test-markdown")

    
    #    yaml_txt = Path(.read_text()
   
    yamldoc = load(yaml_file)
    # with capsys.disabled():
    #     print(yamldoc)
        
    quizmlyamltranscoder = QuizMLYAMLMarkdownTranscoder(yamldoc)
    html_md_dict = quizmlyamltranscoder.get_dict(opts={'fmt': 'html'})
    latex_md_dict = quizmlyamltranscoder.get_dict(opts={'fmt': 'latex'})
    
    # md_list = get_md_list_from_yaml(yamldoc)
    # with capsys.disabled():
    #     print(md_list)    
    # md_combined = md_combine_list(md_list)
    # with capsys.disabled():
    #     print(html_md_dict)

  
    assert(True)
