"""
Markdown classes requried by mistletoe for parsing

"""

import os
import threading
from contextlib import contextmanager

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

    target = {'markdown': {'format': 'html', 'math': 'svg'},
              'html_css': user_html_css,
              'html_pre': user_html_pre}
    yaml_transcoded = transcoder.transcode_target(target)

"""


_MISTLETOE_TOKEN_LOCK = threading.RLock()


def _setup_mistletoe_tokens():
    """Configure mistletoe's shared registries for QuizML parsing."""
    for token_type in (
        mt.block_token.Paragraph,
        mt.block_token.BlockCode,
        mte.MathDisplay,
        mt.block_token.HTMLBlock,
    ):
        while token_type in mt.block_token._token_types:
            mt.block_token.remove_token(token_type)
    mt.block_token.add_token(mte.MathDisplay)
    mt.block_token.add_token(mt.block_token.HTMLBlock)
    mt.block_token.add_token(mt.block_token.Paragraph, 10)

    for token_type in (mte.MathInline, mte.ImageWithWidth):
        while token_type in mt.span_token._token_types:
            mt.span_token.remove_token(token_type)
        mt.span_token.add_token(token_type)


@contextmanager
def _quizml_token_scope():
    """Temporarily register QuizML tokens while mistletoe parses documents."""
    with _MISTLETOE_TOKEN_LOCK:
        block_tokens = list(mt.block_token._token_types)
        span_tokens = list(mt.span_token._token_types)
        try:
            _setup_mistletoe_tokens()
            yield
        finally:
            mt.block_token._token_types[:] = block_tokens
            mt.span_token._token_types[:] = span_tokens


def _parse_markdown_documents(markdown_texts):
    with _quizml_token_scope():
        return {text: mt.Document(text) for text in markdown_texts}


def _normalize_markdown_options(options):
    """Translate the public Markdown settings into renderer options."""
    options = dict(options or {})
    markdown = options.get("markdown")
    if isinstance(markdown, dict):
        for key in ("png_dpi", "png_scale", "svg_scale", "svg_converter"):
            if key in markdown and key not in options:
                options[key] = markdown[key]
    if markdown is None or "fmt" in options:
        return options
    if not isinstance(markdown, dict):
        raise ValueError("The markdown option must be a mapping.")

    output_format = markdown.get("format", "html")
    if output_format == "latex":
        options["fmt"] = "latex"
    elif output_format == "html":
        math_backend = markdown.get("math", "png")
        renderer_format = {
            "png": "html",
            "svg": "html-svg",
            "mathml": "html-mathml",
        }.get(math_backend)
        if renderer_format is None:
            raise ValueError(f"Unknown Markdown math backend: {math_backend}")
        options["fmt"] = renderer_format
    else:
        raise ValueError(f"Unknown Markdown output format: {output_format}")
    postprocess = markdown.get("html_postprocess")
    if postprocess not in (None, "blackboard_html"):
        raise ValueError(f"Unknown HTML postprocessor: {postprocess}")
    if output_format == "latex" and postprocess is not None:
        raise ValueError("HTML postprocessing requires Markdown format 'html'.")
    options["html_postprocess"] = postprocess
    return options


class MarkdownTranscoder:
    def __init__(self, yaml_data, schema=None, base_dir=None):
        self.yaml_data = yaml_data
        self.schema = schema
        path_context = (
            yaml_data.get("paths", {}) if isinstance(yaml_data, dict) else {}
        )

        if base_dir is None:
            input_dir = path_context.get("input_dir")
            inputbasename = yaml_data.get("header", {}).get("inputbasename", "")
            if input_dir:
                self.base_dir = os.path.abspath(input_dir)
            elif inputbasename:
                self.base_dir = os.path.dirname(os.path.abspath(inputbasename))
            else:
                self.base_dir = None
        else:
            self.base_dir = os.path.abspath(base_dir)

        figures_rel = path_context.get(
            "figure_dirs", yaml_data.get("header", {}).get("_figures_path", [])
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
                self.search_dirs.append(
                    os.path.normpath(os.path.join(self.base_dir, p))
                )
            else:
                self.search_dirs.append(os.path.normpath(os.path.abspath(p)))

        # the dictionary of rendered entries will be cached
        self.cache_dict = {}

        # read yaml_data and collect all MD entries into a single list
        self.md_list = get_md_list_from_yaml(yaml_data)

        if not self.md_list:
            self.ast_dict = {}
            return

        # Parse each unique markdown string into its own isolated AST Document
        unique_md = list(dict.fromkeys(self.md_list))
        self.ast_dict = _parse_markdown_documents(unique_md)

    def html_dict(self, opts=None):
        """Returns a HTML dictionary of all MD entries in the YAML data

        Note:
            the rendered HTML dictionary is cached

        Args:
            opts (:dict): optional `markdown`, `html_pre`, and `html_css` settings

        Returns:
            a dictionary where each key corresponds to the MD string
            and the value is the rendered HTML
        """
        if not self.md_list:
            return {}

        opts = _normalize_markdown_options(opts)

        html_pre = opts.get("html_pre", "")
        html_css = opts.get("html_css", "")
        tools = opts.get("tools") or {}
        key = (
            opts.get("fmt", "html")
            + ":PRE:"
            + html_pre
            + "CSS:"
            + html_css
            + "POSTPROCESS:"
            + str(opts.get("html_postprocess", ""))
            + f":DPI:{opts.get('png_dpi', '')}:SCALE:{opts.get('png_scale', '')}:{opts.get('svg_scale', '')}"
            + f":TOOLS:{sorted(tools.items())}"
        )
        if key in self.cache_dict:
            return self.cache_dict[key]
        d = get_html_dict(
            self.ast_dict, opts, base_dir=self.base_dir, search_dirs=self.search_dirs
        )
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

        opts = _normalize_markdown_options(opts)
        tools = opts.get("tools") or {}
        svg_conv = opts.get("svg_converter") or tools.get("svg_converter", "")
        key = f"{opts.get('fmt', 'latex')}:SVG_CONV:{svg_conv}"
        if key in self.cache_dict:
            return self.cache_dict[key]
        d = get_latex_dict(
            self.ast_dict,
            base_dir=self.base_dir,
            search_dirs=self.search_dirs,
            opts=opts,
        )
        self.cache_dict[key] = d
        return d

    def get_dict(self, opts=None):
        """Returns a dictionary of all transcoded MD entries in the YAML data

        Args:
            opts (:dict): target options, including a `markdown` settings mapping

        Returns:
            the dictionary where each key corresponds to found MD strings
            and its value is the corresponding rendered HTML or LaTeX
        """

        opts = _normalize_markdown_options(opts)

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
