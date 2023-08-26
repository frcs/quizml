
import sys
from pathlib import Path
import os
import strictyaml
from strictyaml import Any, Map, Float, Seq, Bool, Int, Str, Optional, MapCombined
from strictyaml import YAMLError

from bbquiz.bbyaml.loader import load

from bbquiz.markdown.markdown import get_dicts_from_yaml


def test_bbyaml_syntax(capsys):
    
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "test-markdown.yaml")
    basename = os.path.join(pkg_dirname, "test-markdown")

    
    #    yaml_txt = Path(.read_text()
   
    yamldoc = load(yaml_file)
    with capsys.disabled():
        print(yamldoc)
        
    (latex_md_dict, html_md_dict) = get_dicts_from_yaml(yamldoc)
    
    # md_list = get_md_list_from_yaml(yamldoc)
    # with capsys.disabled():
    #     print(md_list)    
    # md_combined = md_combine_list(md_list)
    with capsys.disabled():
        print(html_md_dict)

  
    assert(True)
