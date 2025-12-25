"""
Markdown classes requried by mistletoe for parsing 

"""
import re
import mistletoe as mt

from .utils import md_combine_list
from .latex_renderer import get_latex_dict
from .html_renderer import get_html_dict
from quizml.utils import get_md_list_from_yaml

import quizml.markdown.extensions as mte

from quizml.utils import transcode_md_in_yaml


"""
 MarkdownTranscoder 

 This modules defines the MarkdownTranscoder class, that can be
 used to render markdown entries in a YAML struct into HTML or LaTeX
 targets.

 Example:

    import quizml.markdown as md
    import quizml.loader as loader

    yaml_data = loader.load("test.yaml", schema=True)
    
    transcoder = md.MarkdownTranscoder(yaml_data)

    target = {'fmt': 'html',
              'html_css': user_html_css,
              'html_pre': user_html_pre}
    yaml_transcoded = transcoder.transcode_target(target)

"""

class MarkdownTranscoder:
        
    def __init__(self, yaml_data):
        self.yaml_data = yaml_data

        # the dictionary of rendered entries will be cached
        self.cache_dict = {}

        # read yaml_data and collect all MD entries into a single list
        self.md_list = get_md_list_from_yaml(yaml_data)

        # combine this into a single MD string,
        # with entries separated by sections
        md_combined = md_combine_list(self.md_list)

        # The MD parser is a Mistletoe AST renderer 
                
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
        """Returns a HTML dictionary of all MD entries in the YAML data

        Note:
            the rendered HTML dictionary is cached
        
        Args:
            opts (:dict): passing optional val for 'html_pre' and 'html_css'
        
        Returns:
            a dictionary where each key corresponds to the MD string
            and the value is the rendered HTML
        """
        html_pre = opts.get('html_pre', '')
        html_css = opts.get('html_css', '')
        key = opts['fmt'] + ':PRE:' + html_pre + 'CSS:' + html_css
        if key in self.cache_dict:
            return self.cache_dict[key]
        d = get_html_dict(self.doc_combined, self.md_list, opts)
        self.cache_dict[key] = d
        return d        
        
    def latex_dict(self, opts={}):        
        """Returns a LaTeX dictionary of all MD entries in the YAML data

        Note:
            the rendered HTML dictionary is cached
        
        Args:
    
        Returns:
            a dictionary where each key corresponds to the MD string
            and the value is the rendered LaTeX
        """
        key = opts['fmt']
        if key in self.cache_dict:
            return self.cache_dict[key]            
        d = get_latex_dict(self.doc_combined, self.md_list)
        self.cache_dict[key] = d
        return d
        
    def get_dict(self, opts={}):
        """Returns a dictionary of all transcoded MD entries in the YAML data
       
        Args:
            opts (:dict): target format with opts['fmt'] = 'html' or 'latex'
        
        Returns:
            the dictionary where each key corresponds to found MD strings
            and its value is the corresponding rendered HTML or LaTeX
        """

        if opts['fmt'].startswith('html'):
            return self.html_dict(opts)
        elif opts['fmt'] == 'latex':
            return self.latex_dict(opts)
        
    def build_target_dict(self, target={}):
        """precomputes a dictionary of all transcoded MD entries in the YAML data
       
        Args:
            opts (:dict): target format with 'fmt' key set to either 'html'
            or 'latex'. See latex_dict and html_dict for other optional
            options.
        
        Returns:
            computes and caches the dictionary where each key
            corresponds to found MD strings and its value is the
            corresponding rendered HTML or LaTeX
        """
        
        self.get_dict(opts=target)
        
    def transcode_target(self, target={}):
        """transcodes MD entries in YAML struct 
       
        Args:
            target (:dict): target format with target['fmt'] = 'html' or 'latex'
            with also optional keys for each render. 
        Returns:
            a YAML struct where each MD string has been replaced with its HTML
            or laTeX equivalent.
        """
        
        target_dict = self.get_dict(opts=target)
        return transcode_md_in_yaml(self.yaml_data, target_dict)
        

def print_doc(doc, lead=''):
    """Pretty Prints a Mistletoe document

    Args:
        doc: the mistletoe document.
        lead: a string that is used to indent the depth of the elt

    Returns:
        prints the document
    """
    
    print(lead  + str(doc))
    if hasattr(doc, 'children'):
        for a in doc.children:
            print_doc(a, lead + '    ')

            
