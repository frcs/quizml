"""
Markdown classes requried by mistletoe for parsing 

"""
import re
import mistletoe as mt

# from mistletoe import Document
# from mistletoe.html_renderer import HTMLRenderer
# from mistletoe.ast_renderer import ASTRenderer
# from mistletoe.block_token import HTMLBlock
# from mistletoe.span_token import HTMLSpan
# from mistletoe import span_token

from .utils import md_combine_list
from .latex import get_latex_dict
from .html import get_html_dict
from bbquiz.bbyaml.utils import get_md_list_from_yaml

# from .extensions import MathInline, MathDisplay, ImageWithWidth
import bbquiz.markdown.extensions as mte

from bbquiz.bbyaml.utils import transcode_md_in_yaml


"""
 BBYAMLMarkdownTranscoder
 import bbquiz.markdown as md
 mdconverter = md.MarkdownConverter()

 mdconv.load(yaml_data)
 ...
 for task in task_list:
     ...
     md2fmt_dict = mdconverter.get_dict(opts=task)
     rendered_doc = to_jinja.render(md2fmt_dict, target['template'])



"""

class BBYAMLMarkdownTranscoder:
        
    def __init__(self, yaml_data):
        self.yaml_data = yaml_data
        self.cache_dict = {}
        self.md_list = get_md_list_from_yaml(yaml_data)
        md_combined = md_combine_list(self.md_list)    
        mt.block_token.remove_token(mt.block_token.Paragraph)
        mt.block_token.remove_token(mt.block_token.BlockCode)
        mt.block_token.add_token(mte.MathDisplay)
        mt.block_token.add_token(mt.block_token.HTMLBlock)
        mt.block_token.add_token(mt.block_token.Paragraph, 10)
        mt.span_token.add_token(mte.MathInline)    
        mt.span_token.add_token(mte.ImageWithWidth)    
        self.renderer = mt.ast_renderer.ASTRenderer()
        self.doc_combined = mt.Document(md_combined)

    def html_dict(self, opts={}):
        html_pre = opts.get('html_pre', '')
        html_css = opts.get('html_css', '')
        key = 'HTML:PRE:' + html_pre + 'CSS:' + html_css
        if key in self.cache_dict:
            return self.cache_dict[key]
        d = get_html_dict(self.doc_combined, self.md_list, opts)
        self.cache_dict[key] = d
        return d        
        
    def latex_dict(self, opts={}):        
        key = 'LATEX'
        if key in self.cache_dict:
            return self.cache_dict[key]            
        d = get_latex_dict(self.doc_combined, self.md_list)
        self.cache_dict[key] = d
        return d
        
    def get_dict(self, opts={}):
        if opts['fmt'] == 'html':
            return self.html_dict(opts)
        elif opts['fmt'] == 'latex':
            return self.latex_dict(opts)
        
    def build_target_dict(self, target={}):
        self.get_dict(opts=target)
        
    def transcode_target(self, target={}):
        target_dict = self.get_dict(opts=target)
        return transcode_md_in_yaml(self.yaml_data, target_dict)
        

def print_doc(doc, lead=''):
    print(lead  + str(doc))
    if hasattr(doc, 'children'):
        for a in doc.children:
            print_doc(a, lead + '    ')


# def get_dicts_from_yaml(yaml_data, opts={}):
    
#     md_list     = get_md_list_from_yaml(yaml_data)
#     md_combined = md_combine_list(md_list)
    
#     mt.block_token.remove_token(mt.block_token.Paragraph)
#     mt.block_token.remove_token(mt.block_token.BlockCode)
#     mt.block_token.add_token(mte.MathDisplay)
#     mt.block_token.add_token(mt.block_token.HTMLBlock)
#     mt.block_token.add_token(mt.block_token.Paragraph, 10)
#     mt.span_token.add_token(mte.MathInline)    
#     mt.span_token.add_token(mte.ImageWithWidth)    

#     renderer = mt.ASTRenderer()
#     doc_combined = mt.Document(md_combined)
    
# #    print_doc(doc_combined)
    
#     # convert markdown to HTML 
#     html_dict = get_html_dict(doc_combined, md_list, opts)
    
#     # convert markdown to HTML 
#     latex_dict = get_latex_dict(doc_combined, md_list)
       
#     return (latex_dict, html_dict)
            
