"""Markdown AST Transcoder for HTML and LaTeX compilation targets."""

import os

import mistletoe as mt

from quizml.transcoder.html import get_html_dict
from quizml.transcoder.latex import get_latex_dict
from quizml.transcoder.nodes import get_md_list_from_yaml, transcode_md_in_yaml
from quizml.transcoder.tokens import ImageWithWidth, MathDisplay, MathInline


def _setup_mistletoe_tokens():
    """Ensure mistletoe has required block and span tokens without duplicates."""
    if MathInline not in mt.span_token._token_types:
        mt.block_token.remove_token(mt.block_token.Paragraph)
        mt.block_token.remove_token(mt.block_token.BlockCode)
        mt.block_token.add_token(MathDisplay)
        mt.block_token.add_token(mt.block_token.HTMLBlock)
        mt.block_token.add_token(mt.block_token.Paragraph, 10)
        mt.span_token.add_token(MathInline)
        mt.span_token.add_token(ImageWithWidth)


class MarkdownTranscoder:
    """Renders markdown entries in a QuizML YAML structure into HTML or LaTeX targets."""

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

        figures_rel = (
            yaml_data.get("header", {}).get("_figures_path", [])
            if isinstance(yaml_data, dict)
            else []
        )
        if isinstance(figures_rel, str):
            figures_rel = [figures_rel]
        elif not isinstance(figures_rel, list):
            figures_rel = []

        self.search_dirs = []
        for p in figures_rel:
            if os.path.isabs(p):
                self.search_dirs.append(os.path.normpath(p))
            elif self.base_dir:
                self.search_dirs.append(os.path.normpath(os.path.join(self.base_dir, p)))
            else:
                self.search_dirs.append(os.path.normpath(os.path.abspath(p)))

        self.cache_dict = {}
        self.md_list = get_md_list_from_yaml(yaml_data)

        if not self.md_list:
            self.ast_dict = {}
            return

        _setup_mistletoe_tokens()

        unique_md = list(dict.fromkeys(self.md_list))
        self.ast_dict = {txt: mt.Document(txt) for txt in unique_md}

    def html_dict(self, opts=None):
        """Returns an HTML dictionary of all MD entries in the YAML data."""
        if not self.md_list:
            return {}

        if opts is None:
            opts = {}

        html_pre = opts.get("html_pre", "")
        html_css = opts.get("html_css", "")
        key = opts.get("fmt", "html") + ":PRE:" + html_pre + "CSS:" + html_css
        if key in self.cache_dict:
            return self.cache_dict[key]
        d = get_html_dict(
            self.ast_dict, opts, base_dir=self.base_dir, search_dirs=self.search_dirs
        )
        self.cache_dict[key] = d
        return d

    def latex_dict(self, opts=None):
        """Returns a LaTeX dictionary of all MD entries in the YAML data."""
        if not self.md_list:
            return {}

        if opts is None:
            opts = {}

        key = opts.get("fmt", "latex")
        if key in self.cache_dict:
            return self.cache_dict[key]
        d = get_latex_dict(
            self.ast_dict, base_dir=self.base_dir, search_dirs=self.search_dirs
        )
        self.cache_dict[key] = d
        return d

    def get_dict(self, opts=None):
        """Returns a dictionary of all transcoded MD entries for the target format."""
        if opts is None:
            opts = {}

        if opts.get("fmt", "html").startswith("html"):
            return self.html_dict(opts)
        elif opts.get("fmt") == "latex":
            return self.latex_dict(opts)
        return {}

    def transcode_target(self, target=None):
        """Transcodes MD entries in the YAML document into target format representations."""
        if target is None:
            target = {}

        if not self.md_list:
            return self.yaml_data

        target_dict = self.get_dict(opts=target)
        return transcode_md_in_yaml(self.yaml_data, target_dict)
