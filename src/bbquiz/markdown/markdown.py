"""
Markdown classes requried by mistletoe for parsing 

"""
import re
import mistletoe
from mistletoe import Document
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.ast_renderer import ASTRenderer
from mistletoe.block_token import HTMLBlock
from mistletoe.span_token import HTMLSpan
from mistletoe import span_token

from .utils import md_combine_list
from .latex import get_latex_dict
from .html import get_html_dict
from bbquiz.bbyaml.utils import get_md_list_from_yaml

from .extensions import MathInline, MathDisplay, ImageWithWidth


def print_doc(doc, lead=''):
    print(lead  + str(doc))
    if hasattr(doc, 'children'):
        for a in doc.children:
            print_doc(a, lead + '    ')


def get_dicts_from_yaml(yaml_data):
    
    md_list     = get_md_list_from_yaml(yaml_data)
    md_combined = md_combine_list(md_list)

    
    # with open("bbquiz-mdcombine.md", "w") as f:
    #     f.write(md_combined)        

    # converting the markdown text into a mistletoe obj
    # not sure I understand, using AST Renderer here,
    # but maybe we should use a different renderer?

    # renderer = ASTRenderer(MathInline,
    #                        MathDisplay,
    #                        ImageWithWidth,
    #                        HTMLBlock)
    mistletoe.block_token.remove_token(mistletoe.block_token.Paragraph)
    mistletoe.block_token.remove_token(mistletoe.block_token.BlockCode)
    mistletoe.block_token.add_token(MathDisplay)
    mistletoe.block_token.add_token(mistletoe.block_token.HTMLBlock)
    mistletoe.block_token.add_token(mistletoe.block_token.Paragraph, 10)
    mistletoe.span_token.add_token(MathInline)    
    mistletoe.span_token.add_token(ImageWithWidth)    

    renderer = ASTRenderer()
    doc_combined = Document(md_combined)
    
#    print_doc(doc_combined)
    
    # convert markdown to HTML 
    html_dict = get_html_dict(doc_combined, md_list)
    
    # convert markdown to HTML 
    latex_dict = get_latex_dict(doc_combined, md_list)
       
    return (latex_dict, html_dict)
            
