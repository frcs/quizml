
import sys
from pathlib import Path
import os
import strictyaml
from strictyaml import Any, Map, Float, Seq, Bool, Int, Str, Optional, MapCombined
from strictyaml import YAMLError

from bbquiz.bbyaml.loader import load

from bbquiz.markdown.html_dict_from_md_list import get_md_list_from_yaml
from bbquiz.markdown.html_dict_from_md_list import get_html_md_dict_from_yaml
from bbquiz.markdown.latex_dict_from_md_list import get_latex_md_dict_from_yaml


def test_bbyaml_syntax(capsys):
    
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "test-markdown.yaml")
    basename = os.path.join(pkg_dirname, "test-markdown")

    
    #    yaml_txt = Path(.read_text()
   
    yamldoc = load(yaml_file)
    with capsys.disabled():
        print(yamldoc)
        

    html = get_latex_md_dict_from_yaml(yamldoc)
    
    # md_list = get_md_list_from_yaml(yamldoc)
    # with capsys.disabled():
    #     print(md_list)    
    # md_combined = md_combine_list(md_list)
    with capsys.disabled():
        print(html)

  
    assert(True)
