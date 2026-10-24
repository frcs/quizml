"""Markdown transcoding engine and standalone API for QuizML."""

import os
import threading
from collections.abc import Iterable
from contextlib import contextmanager
from typing import Any

import mistletoe as mt

import quizml.markdown.extensions as mte
from quizml.markdown.options import normalize_markdown_options
from quizml.yaml.schema import MarkdownString

from .html_renderer import get_html_dict
from .latex_renderer import get_latex_dict

_normalize_markdown_options = normalize_markdown_options

_MISTLETOE_TOKEN_LOCK = threading.RLock()


def iter_nodes(data, key_filter=None):
    """Generator that yields all leaf nodes in the data structure."""
    if isinstance(data, list):
        for item in data:
            yield from iter_nodes(item, key_filter)
    elif isinstance(data, dict):
        for k, v in data.items():
            if key_filter and not key_filter(k):
                continue
            yield from iter_nodes(v, key_filter)
    else:
        yield data


def map_nodes(data, fn, key_filter=None):
    """Recursively applies fn to all leaf nodes in the data structure."""
    if isinstance(data, list):
        return [map_nodes(item, fn, key_filter) for item in data]
    elif isinstance(data, dict):
        new_dict = type(data)()
        for k, v in data.items():
            if key_filter and not key_filter(k):
                new_dict[k] = v
            else:
                new_dict[k] = map_nodes(v, fn, key_filter)
        return new_dict
    else:
        return fn(data)


def get_md_list_from_yaml(yaml_data):
    """List all Markdown entries in the YAML document."""
    md_list = []

    def header_key_filter(key):
        non_md_keys = ["type", "inputbasename"]
        return (key not in non_md_keys) and not key.startswith("_")

    if isinstance(yaml_data, dict) and (
        "header" in yaml_data or "questions" in yaml_data
    ):
        if "header" in yaml_data:
            for node in iter_nodes(yaml_data["header"], header_key_filter):
                if isinstance(node, str):
                    md_list.append(str(node))

        if "questions" in yaml_data:
            for node in iter_nodes(yaml_data["questions"]):
                if isinstance(node, MarkdownString):
                    md_list.append(str(node))
    else:
        for node in iter_nodes(yaml_data, header_key_filter):
            if isinstance(node, str):
                md_list.append(str(node))

    return md_list


def transcode_md_in_yaml(yaml_data, md_dict):
    """Translate all Markdown strings in yaml_data using md_dict."""

    def transform_questions(node):
        if isinstance(node, MarkdownString) and node in md_dict:
            return md_dict[node]
        return node

    def transform_header(node):
        if isinstance(node, str) and node in md_dict:
            return md_dict[node]
        return node

    def header_key_filter(key):
        return key != "inputbasename" and not key.startswith("_")

    if isinstance(yaml_data, dict) and (
        "header" in yaml_data or "questions" in yaml_data
    ):
        new_doc = type(yaml_data)()
        for k, v in yaml_data.items():
            if k == "header":
                new_doc[k] = map_nodes(v, transform_header, header_key_filter)
            elif k == "questions":
                new_doc[k] = map_nodes(v, transform_questions)
            else:
                new_doc[k] = v
        if hasattr(yaml_data, "schema") and hasattr(new_doc, "schema"):
            new_doc.schema = yaml_data.schema
        return new_doc
    else:
        return map_nodes(yaml_data, transform_header, header_key_filter)


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


def _build_target_options(target: dict[str, Any] | None = None, **kwargs) -> dict[str, Any]:
    opts = dict(target or {})
    if kwargs:
        md_keys = {
            "format",
            "math",
            "html_postprocess",
            "png_dpi",
            "png_scale",
            "svg_scale",
            "svg_converter",
        }
        md_sub = dict(opts.get("markdown") or {}) if isinstance(opts.get("markdown"), dict) else {}
        for k, v in kwargs.items():
            if k in md_keys:
                md_sub[k] = v
            else:
                opts[k] = v
        if md_sub:
            opts["markdown"] = md_sub
    return opts


class MarkdownTranscoder:
    def __init__(self, yaml_data, base_dir=None, search_dirs=None):
        self.yaml_data = yaml_data
        path_context = (
            yaml_data.get("paths", {}) if isinstance(yaml_data, dict) else {}
        )

        if base_dir is None:
            input_dir = path_context.get("input_dir")
            inputbasename = (
                yaml_data.get("header", {}).get("inputbasename", "")
                if isinstance(yaml_data, dict)
                else ""
            )
            if input_dir:
                self.base_dir = os.path.abspath(input_dir)
            elif inputbasename:
                self.base_dir = os.path.dirname(os.path.abspath(inputbasename))
            else:
                self.base_dir = None
        else:
            self.base_dir = os.path.abspath(base_dir)

        if search_dirs is not None:
            figures_rel = list(search_dirs)
        else:
            figures_rel = path_context.get(
                "figure_dirs",
                yaml_data.get("header", {}).get("_figures_path", [])
                if isinstance(yaml_data, dict)
                else [],
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

        self.cache_dict = {}
        self.md_list = get_md_list_from_yaml(yaml_data)

        if not self.md_list:
            self.ast_dict = {}
            return

        unique_md = list(dict.fromkeys(self.md_list))
        self.ast_dict = _parse_markdown_documents(unique_md)

    def html_dict(self, opts=None):
        """Returns a cached HTML dictionary of all MD entries in the YAML data."""
        if not self.md_list:
            return {}

        opts = normalize_markdown_options(opts)

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
        """Returns a cached LaTeX dictionary of all MD entries in the YAML data."""
        if not self.md_list:
            return {}

        opts = normalize_markdown_options(opts)
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

    def docx_dict(self, opts=None):
        """Returns a cached Word OpenXML dictionary of all MD entries in the YAML data."""
        if not self.md_list:
            return {}

        opts = normalize_markdown_options(opts)
        html_pre = opts.get("html_pre", "")
        user_pre = opts.get("user_pre", "")
        key = f"{opts.get('fmt', 'docx')}:PRE:{html_pre}:USER_PRE:{user_pre}"
        if key in self.cache_dict:
            return self.cache_dict[key]
        from quizml.markdown.docx import get_docx_dict

        d = get_docx_dict(
            self.ast_dict,
            opts=opts,
            base_dir=self.base_dir,
            search_dirs=self.search_dirs,
        )
        self.cache_dict[key] = d
        return d

    def get_dict(self, opts=None):
        """Returns a dictionary of all transcoded MD entries in the YAML data."""
        opts = normalize_markdown_options(opts)
        fmt = opts.get("fmt")
        if not fmt:
            return {}

        if fmt.startswith("html"):
            return self.html_dict(opts)
        elif fmt == "latex":
            return self.latex_dict(opts)
        elif fmt == "markdown":
            return {md_str: str(md_str) for md_str in self.ast_dict}
        elif fmt == "docx":
            return self.docx_dict(opts)
        return {}

    def transcode_target(self, target=None):
        """Transcodes MD entries in YAML struct for a target."""
        if target is None:
            target = {}

        if not self.md_list:
            return self.yaml_data

        opts = normalize_markdown_options(target)
        if not opts.get("fmt"):
            return self.yaml_data

        target_dict = self.get_dict(opts=opts)
        return transcode_md_in_yaml(self.yaml_data, target_dict)


def transcode(yaml_data, target=None, *, base_dir=None, search_dirs=None, **kwargs):
    """Transcode all Markdown fields in a QuizML document or dict."""
    opts = _build_target_options(target, **kwargs)
    transcoder = MarkdownTranscoder(
        yaml_data, base_dir=base_dir, search_dirs=search_dirs
    )
    return transcoder.transcode_target(opts)


def transcode_many(
    markdown_texts: Iterable[str],
    target=None,
    *,
    base_dir=None,
    search_dirs=None,
    **kwargs,
) -> dict[str, str]:
    """Transcode a collection of Markdown strings into a `{source: rendered}` mapping."""
    texts = [MarkdownString(str(t)) for t in markdown_texts]
    if not texts:
        return {}
    opts = _build_target_options(target, **kwargs)
    if "fmt" not in opts and "markdown" not in opts:
        opts["markdown"] = {"format": "html"}
    doc = {"questions": texts}
    transcoder = MarkdownTranscoder(doc, base_dir=base_dir, search_dirs=search_dirs)
    return transcoder.get_dict(opts)


def transcode_text(
    markdown_text: str,
    target=None,
    *,
    base_dir=None,
    search_dirs=None,
    **kwargs,
) -> str:
    """Transcode a single Markdown string into HTML, LaTeX, or Word OpenXML."""
    text = str(markdown_text)
    rendered_map = transcode_many(
        [text],
        target=target,
        base_dir=base_dir,
        search_dirs=search_dirs,
        **kwargs,
    )
    return rendered_map.get(text, text)
