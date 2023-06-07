"""
Markdown classes requried by mistletoe for parsing 

"""
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

from .utils import md_combine_list
from .latex import get_latex_dict
from .html import get_html_dict
from bbquiz.bbyaml.utils import get_md_list_from_yaml

from .extensions import MathInline, MathDisplay, ImageWithWidth


def get_dicts_from_yaml(yaml_data):
    
    md_list     = get_md_list_from_yaml(yaml_data)
    md_combined = md_combine_list(md_list)

    
    # with open("bbquiz-mdcombine.md", "w") as f:
    #     f.write(md_combined)        

    # converting the markdown text into a mistletoe obj
    # not sure I understand, using AST Renderer here,
    # but maybe we should use a different renderer?
    with ASTRenderer(MathInline,MathDisplay,ImageWithWidth,HTMLBlock) as renderer:
        # we do not use BlocCode, as it is too easy to have issues with it
        mistletoe.block_token.remove_token(mistletoe.block_token.BlockCode)
        doc_combined = Document(md_combined)

    # convert markdown to HTML 
    html_dict = get_html_dict(doc_combined, md_list)

    # convert markdown to HTML 
    latex_dict = get_latex_dict(doc_combined, md_list)
       
    return (latex_dict, html_dict)
            
