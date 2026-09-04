"""
Markdown classes requried by mistletoe for parsing

"""

import os

import mistletoe as mt

import quizml.markdown.extensions as mte
from quizml.utils import get_md_list_from_yaml, transcode_md_in_yaml

from .html_renderer import get_html_dict
from .latex_renderer import get_latex_dict

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


def _setup_mistletoe_tokens():
    """Ensure mistletoe has required block and span tokens without duplicates."""
    if mte.MathInline not in mt.span_token._token_types:
        mt.block_token.remove_token(mt.block_token.Paragraph)
        mt.block_token.remove_token(mt.block_token.BlockCode)
        mt.block_token.add_token(mte.MathDisplay)
        mt.block_token.add_token(mt.block_token.HTMLBlock)
        mt.block_token.add_token(mt.block_token.Paragraph, 10)
        mt.span_token.add_token(mte.MathInline)
        mt.span_token.add_token(mte.ImageWithWidth)


class MarkdownTranscoder:
    def __init__(self, yaml_data, schema=None, base_dir=None):
        self.yaml_data = yaml_data
        self.schema = schema

        if base_dir is None:
            inputbasename = (
                yaml_data.get("header", {}).get("inputbasename", "")
                if isinstance(yaml_data, dict)
                else ""
            )
            if inputbasename:
                self.base_dir = os.path.dirname(os.path.abspath(inputbasename))
            else:
                self.base_dir = None
        else:
            self.base_dir = os.path.abspath(base_dir)

        # the dictionary of rendered entries will be cached
        self.cache_dict = {}

        # read yaml_data and collect all MD entries into a single list
        self.md_list = get_md_list_from_yaml(yaml_data)
        
        if not self.md_list:
            self.ast_dict = {}
            return

        _setup_mistletoe_tokens()

        # Parse each unique markdown string into its own isolated AST Document
        unique_md = list(dict.fromkeys(self.md_list))
        self.ast_dict = {txt: mt.Document(txt) for txt in unique_md}

    def html_dict(self, opts=None):
        """Returns a HTML dictionary of all MD entries in the YAML data

        Note:
            the rendered HTML dictionary is cached

        Args:
            opts (:dict): passing optional val for 'html_pre' and 'html_css'

        Returns:
            a dictionary where each key corresponds to the MD string
            and the value is the rendered HTML
        """
        if not self.md_list:
            return {}

        if opts is None:
            opts = {}
            
        html_pre = opts.get("html_pre", "")
        html_css = opts.get("html_css", "")
        key = opts.get("fmt", "html") + ":PRE:" + html_pre + "CSS:" + html_css
        if key in self.cache_dict:
            return self.cache_dict[key]
        d = get_html_dict(self.ast_dict, opts, base_dir=self.base_dir)
        self.cache_dict[key] = d
        return d

    def latex_dict(self, opts=None):
        """Returns a LaTeX dictionary of all MD entries in the YAML data

        Note:
            the rendered LaTeX dictionary is cached

        Args:

        Returns:
            a dictionary where each key corresponds to the MD string
            and the value is the rendered LaTeX
        """
        if not self.md_list:
            return {}

        if opts is None:
            opts = {}
        
        key = opts.get("fmt", "latex")
        if key in self.cache_dict:
            return self.cache_dict[key]
        d = get_latex_dict(self.ast_dict, base_dir=self.base_dir)
        self.cache_dict[key] = d
        return d

    def get_dict(self, opts=None):
        """Returns a dictionary of all transcoded MD entries in the YAML data

        Args:
            opts (:dict): target format with opts['fmt'] = 'html' or 'latex'

        Returns:
            the dictionary where each key corresponds to found MD strings
            and its value is the corresponding rendered HTML or LaTeX
        """

        if opts is None:
            opts = {}
        
        if opts["fmt"].startswith("html"):
            return self.html_dict(opts)
        elif opts["fmt"] == "latex":
            return self.latex_dict(opts)

    def transcode_target(self, target=None):
        """transcodes MD entries in YAML struct

        Args:
            target (:dict): target format with target['fmt'] = 'html' or 'latex'
            with also optional keys for each render.
        Returns:
            a YAML struct where each MD string has been replaced with its HTML
            or laTeX equivalent.
        """
        if target is None:
            target = {}

        if not self.md_list:
            return self.yaml_data

        target_dict = self.get_dict(opts=target)
        return transcode_md_in_yaml(self.yaml_data, target_dict)
