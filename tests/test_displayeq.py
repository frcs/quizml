import sys
from pathlib import Path
import os

from bbquiz.markdown.markdown import get_dicts_from_yaml

import re
import mistletoe
from mistletoe import Document, HTMLRenderer
from mistletoe.ast_renderer import ASTRenderer
from mistletoe.block_token import HTMLBlock
from mistletoe.span_token import HTMLSpan

from mistletoe.latex_token import Math
from mistletoe import span_token
from mistletoe.span_token import Image
from mistletoe.span_token import tokenize_inner
from mistletoe.span_token import SpanToken
from mistletoe.span_token import remove_token
from mistletoe.block_token import BlockCode

from bbquiz.markdown.utils import md_combine_list
from bbquiz.markdown.latex import get_latex_dict
from bbquiz.markdown.html import get_html_dict
from bbquiz.bbyaml.utils import get_md_list_from_yaml

from bbquiz.markdown.extensions import MathInline, MathDisplay, ImageWithWidth

def print_doc(doc, lead=''):
    print(lead  + str(doc))
    if hasattr(doc, 'children'):
        for a in doc.children:
            print_doc(a, lead + '    ')


def test_displayeq(capsys):
    
    pkg_dirname = os.path.dirname(__file__)
    yaml_file = os.path.join(pkg_dirname, "test-markdown.yaml")
    basename = os.path.join(pkg_dirname, "test-markdown")

    
    md_text = r"""
    $$
      E({\bf w}) = \frac{1}{N} \sum_{i=1}^N \|{\bf w}^{\top}{\bf x}_i - {\bf
      y}_i\|^2

    + 0.1 \log( w_i ) + \frac{1}{P} \sum_{j=1}^P w_i \log( w_i )
    $$
"""


    regex = r"""
    (?<!\\)      # negative look-behind to make sure start is not escaped 
    (?:          # start non-capture group for all possible match starts
    ((?<!\$)\${2}(?!\$))| # group 1, match dollar signs only 
    (\\\[)|               # group 2, \[
    (\\begin\{(equation|split|alignat|multline|gather|align|flalign|)(\*?)\}) # group 3, all amsmath
    )
    (?(1)(.*?)(?<!\\)(?<!\$)\1(?!\$)|
    (?(2)(.*?)(?<!\\)\\\]|
    (?(3)(.*?)(?<!\\)\\end\{\4\5\}
    )))
    """

    matches = re.finditer(regex, md_text, re.MULTILINE | re.DOTALL | re.VERBOSE)

    with capsys.disabled():
        print ("MATCHING\n\n\n")
        for matchNum, match in enumerate(matches, start=1):
    
            print ("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum = matchNum, start = match.start(), end = match.end(), match = match.group()))
    
            for groupNum in range(0, len(match.groups())):
                groupNum = groupNum + 1
        
                print ("Group {groupNum} found at {start}-{end}: {group}".format(groupNum = groupNum, start = match.start(groupNum), end = match.end(groupNum), group = match.group(groupNum)))
        print ("GROUP 0<<\n")
        print (match.group(0))
        print ("\n>>GROUP 0\n")
    
    
    with ASTRenderer(MathInline,
                     MathDisplay,
                     ImageWithWidth,
                     HTMLBlock) as renderer:
        # we do not use BlocCode, as it is too easy to have issues with it
        mistletoe.block_token.remove_token(mistletoe.block_token.BlockCode)
        doc_combined = Document(md_text)

    
    # (latex_md_dict, html_md_dict) = get_dicts_from_yaml(yaml_data)
    
    with capsys.disabled():
        print_doc(doc_combined)
       
    # with capsys.disabled():
    #     print(html)

  
    assert(True)


        
