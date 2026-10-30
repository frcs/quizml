"""Markdown transcoding engine and standalone API for QuizML."""

import os
import threading
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import mistletoe as mt

import quizml.markdown.extensions as mte
from quizml.markdown.options import MarkdownOptions, normalize_markdown_options
from quizml.yaml.schema import MarkdownString

from .html_renderer import get_html_dict
from .latex_renderer import get_latex_dict

_normalize_markdown_options = normalize_markdown_options

_MISTLETOE_TOKEN_LOCK = threading.RLock()


def iter_nodes(
    data: Any, key_filter: Callable[[str], bool] | None = None
) -> Iterator[Any]:
    """Yield all leaf values in a nested dict/list structure."""
    if isinstance(data, list):
        for item in data:
            yield from iter_nodes(item, key_filter)
    elif isinstance(data, dict):
        for k, v in data.items():
            if key_filter and not key_filter(str(k)):
                continue
            yield from iter_nodes(v, key_filter)
    else:
        yield data


def map_nodes(
    data: Any,
    fn: Callable[[Any], Any],
    key_filter: Callable[[str], bool] | None = None,
) -> Any:
    """Recursively apply ``fn`` to all leaf values in a nested dict/list structure."""
    if isinstance(data, list):
        return [map_nodes(item, fn, key_filter) for item in data]
    if isinstance(data, dict):
        new_dict = type(data)()
        for k, v in data.items():
            if key_filter and not key_filter(str(k)):
                new_dict[k] = v
            else:
                new_dict[k] = map_nodes(v, fn, key_filter)
        return new_dict
    return fn(data)


def get_md_list_from_yaml(yaml_data: Any) -> list[str]:
    """Extract all Markdown strings from a QuizML ``yaml_data`` structure.

    In ``questions``, only values tagged as ``MarkdownString`` by JSON Schema
    coercion are collected. In ``header``, all public string values (excluding
    ``type``, ``inputbasename``, and ``_``-prefixed directives) are collected.
    """
    md_list: list[str] = []

    def header_key_filter(key: str) -> bool:
        return key not in ("type", "inputbasename") and not key.startswith("_")

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


def transcode_md_in_yaml(yaml_data: Any, md_dict: dict[str, Any]) -> Any:
    """Replace Markdown strings in ``yaml_data`` with rendered values in ``md_dict``."""

    def transform_questions(node: Any) -> Any:
        if isinstance(node, MarkdownString) and node in md_dict:
            return md_dict[node]
        return node

    def transform_header(node: Any) -> Any:
        if isinstance(node, str) and node in md_dict:
            return md_dict[node]
        return node

    def header_key_filter(key: str) -> bool:
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
    return map_nodes(yaml_data, transform_header, header_key_filter)


def _setup_mistletoe_tokens() -> None:
    """Register QuizML's custom math and image tokens in Mistletoe's global registries.

    Note: ``BlockCode`` (indented 4-space code blocks) is intentionally removed so
    indented lines inside multi-line YAML scalars are parsed as regular paragraphs
    or math blocks rather than accidental code blocks (fenced `` ``` `` blocks
    remain active via ``CodeFence``).
    """
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
def _quizml_token_scope() -> Iterator[None]:
    """Thread-safely register QuizML tokens while Mistletoe parses documents."""
    with _MISTLETOE_TOKEN_LOCK:
        block_tokens = list(mt.block_token._token_types)
        span_tokens = list(mt.span_token._token_types)
        try:
            _setup_mistletoe_tokens()
            yield
        finally:
            mt.block_token._token_types[:] = block_tokens
            mt.span_token._token_types[:] = span_tokens


def _parse_markdown_documents(markdown_texts: Iterable[str]) -> dict[str, Any]:
    """Parse each unique Markdown string into a Mistletoe ``Document`` AST."""
    with _quizml_token_scope():
        return {text: mt.Document(text) for text in markdown_texts}


def _build_target_options(
    target: dict[str, Any] | MarkdownOptions | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Merge keyword overrides into a target configuration dictionary."""
    if isinstance(target, MarkdownOptions):
        opts = normalize_markdown_options(target)
    else:
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
        md_sub = (
            dict(opts.get("markdown") or {})
            if isinstance(opts.get("markdown"), dict)
            else {}
        )
        for k, v in kwargs.items():
            if k in md_keys:
                md_sub[k] = v
            else:
                opts[k] = v
        if md_sub:
            opts["markdown"] = md_sub
    return opts


def _resolve_transcoder_base_dir(
    yaml_data: Any, base_dir: str | Path | None
) -> str | None:
    """Resolve the base directory for relative image/figure lookups."""
    if base_dir is not None:
        return os.path.abspath(str(base_dir))
    if not isinstance(yaml_data, dict):
        return None
    path_context = yaml_data.get("paths", {})
    input_dir = (
        path_context.get("input_dir") if isinstance(path_context, dict) else None
    )
    if input_dir:
        return os.path.abspath(str(input_dir))
    header = yaml_data.get("header", {})
    inputbasename = header.get("inputbasename", "") if isinstance(header, dict) else ""
    if inputbasename:
        return os.path.dirname(os.path.abspath(str(inputbasename)))
    return None


def _resolve_transcoder_search_dirs(
    yaml_data: Any,
    resolved_base_dir: str | None,
    search_dirs: Sequence[str | Path] | None,
) -> list[str]:
    """Resolve the ordered list of figure search directories."""
    if search_dirs is not None:
        figures_rel: list[Any] = list(search_dirs)
    elif isinstance(yaml_data, dict):
        path_context = yaml_data.get("paths", {})
        header = yaml_data.get("header", {})
        raw_figs = (
            path_context.get("figure_dirs")
            if isinstance(path_context, dict) and "figure_dirs" in path_context
            else (header.get("_figures_path", []) if isinstance(header, dict) else [])
        )
        if isinstance(raw_figs, str):
            figures_rel = [raw_figs]
        elif isinstance(raw_figs, list):
            figures_rel = raw_figs
        else:
            figures_rel = []
    else:
        figures_rel = []

    resolved: list[str] = []
    for p in figures_rel:
        p_str = str(p)
        if os.path.isabs(p_str):
            resolved.append(os.path.normpath(p_str))
        elif resolved_base_dir:
            resolved.append(os.path.normpath(os.path.join(resolved_base_dir, p_str)))
        else:
            resolved.append(os.path.normpath(os.path.abspath(p_str)))
    return resolved


class MarkdownTranscoder:
    """Parse all Markdown fields in a quiz once and cache rendered outputs."""

    def __init__(
        self,
        yaml_data: Any,
        base_dir: str | Path | None = None,
        search_dirs: Sequence[str | Path] | None = None,
    ) -> None:
        self.yaml_data = yaml_data
        self.base_dir = _resolve_transcoder_base_dir(yaml_data, base_dir)
        self.search_dirs = _resolve_transcoder_search_dirs(
            yaml_data, self.base_dir, search_dirs
        )
        self.cache_dict: dict[str, dict[str, Any]] = {}
        self.md_list = get_md_list_from_yaml(yaml_data)

        if not self.md_list:
            self.ast_dict: dict[str, Any] = {}
            return

        unique_md = list(dict.fromkeys(self.md_list))
        self.ast_dict = _parse_markdown_documents(unique_md)

    def html_dict(
        self, opts: dict[str, Any] | MarkdownOptions | None = None
    ) -> dict[str, str]:
        """Return a cached ``{markdown: html}`` dictionary for all Markdown entries."""
        if not self.md_list:
            return {}

        norm_opts = normalize_markdown_options(opts)
        html_pre = norm_opts.get("html_pre", "")
        html_css = norm_opts.get("html_css", "")
        tools = norm_opts.get("tools") or {}
        dpi = norm_opts.get("png_dpi", "")
        png_scale = norm_opts.get("png_scale", "")
        svg_scale = norm_opts.get("svg_scale", "")
        key = (
            f"{norm_opts.get('fmt', 'html')}:PRE:{html_pre}CSS:{html_css}"
            f"POSTPROCESS:{norm_opts.get('html_postprocess', '')}"
            f":DPI:{dpi}:SCALE:{png_scale}:{svg_scale}"
            f":TOOLS:{sorted(tools.items())}"
        )
        if key in self.cache_dict:
            return self.cache_dict[key]
        d = get_html_dict(
            self.ast_dict,
            norm_opts,
            base_dir=self.base_dir,
            search_dirs=self.search_dirs,
        )
        self.cache_dict[key] = d
        return d

    def latex_dict(
        self, opts: dict[str, Any] | MarkdownOptions | None = None
    ) -> dict[str, str]:
        """Return a cached ``{markdown: latex}`` dictionary for all Markdown entries."""
        if not self.md_list:
            return {}

        norm_opts = normalize_markdown_options(opts)
        tools = norm_opts.get("tools") or {}
        svg_conv = norm_opts.get("svg_converter") or tools.get("svg_converter", "")
        key = f"{norm_opts.get('fmt', 'latex')}:SVG_CONV:{svg_conv}"
        if key in self.cache_dict:
            return self.cache_dict[key]
        d = get_latex_dict(
            self.ast_dict,
            base_dir=self.base_dir,
            search_dirs=self.search_dirs,
            opts=norm_opts,
        )
        self.cache_dict[key] = d
        return d

    def docx_dict(
        self, opts: dict[str, Any] | MarkdownOptions | None = None
    ) -> dict[str, Any]:
        """Return a cached ``{markdown: openxml}`` dict for all Markdown entries."""
        if not self.md_list:
            return {}

        norm_opts = normalize_markdown_options(opts)
        html_pre = norm_opts.get("html_pre", "")
        user_pre = norm_opts.get("user_pre", "")
        key = f"{norm_opts.get('fmt', 'docx')}:PRE:{html_pre}:USER_PRE:{user_pre}"
        if key in self.cache_dict:
            return self.cache_dict[key]
        from quizml.markdown.docx import get_docx_dict

        d = get_docx_dict(
            self.ast_dict,
            opts=norm_opts,
            base_dir=self.base_dir,
            search_dirs=self.search_dirs,
        )
        self.cache_dict[key] = d
        return d

    def get_dict(
        self, opts: dict[str, Any] | MarkdownOptions | None = None
    ) -> dict[str, Any]:
        """Return a ``{markdown: rendered}`` dictionary for the requested format."""
        norm_opts = normalize_markdown_options(opts)
        fmt = norm_opts.get("fmt")
        if not fmt:
            return {}

        if fmt.startswith("html"):
            return self.html_dict(norm_opts)
        if fmt == "latex":
            return self.latex_dict(norm_opts)
        if fmt == "markdown":
            return {md_str: str(md_str) for md_str in self.ast_dict}
        if fmt == "docx":
            return self.docx_dict(norm_opts)
        return {}

    def transcode_target(
        self, target: dict[str, Any] | MarkdownOptions | None = None
    ) -> Any:
        """Transcode all Markdown fields in ``self.yaml_data`` for ``target``."""
        if target is None:
            target = {}

        if not self.md_list:
            return self.yaml_data

        opts = normalize_markdown_options(target)
        if not opts.get("fmt"):
            return self.yaml_data

        target_dict = self.get_dict(opts=opts)
        return transcode_md_in_yaml(self.yaml_data, target_dict)


def transcode(
    yaml_data: Any,
    target: dict[str, Any] | MarkdownOptions | None = None,
    *,
    base_dir: str | Path | None = None,
    search_dirs: Sequence[str | Path] | None = None,
    **kwargs: Any,
) -> Any:
    """Transcode all Markdown fields in a QuizML document or dictionary."""
    opts = _build_target_options(target, **kwargs)
    transcoder = MarkdownTranscoder(
        yaml_data, base_dir=base_dir, search_dirs=search_dirs
    )
    return transcoder.transcode_target(opts)


def transcode_many(
    markdown_texts: Iterable[str],
    target: dict[str, Any] | MarkdownOptions | None = None,
    *,
    base_dir: str | Path | None = None,
    search_dirs: Sequence[str | Path] | None = None,
    **kwargs: Any,
) -> dict[str, str]:
    """Transcode Markdown strings into a ``{source: rendered}`` mapping."""
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
    target: dict[str, Any] | MarkdownOptions | None = None,
    *,
    base_dir: str | Path | None = None,
    search_dirs: Sequence[str | Path] | None = None,
    **kwargs: Any,
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
