"""Mistletoe HTML renderer and batch equation compilation (PNG, SVG, MathML)."""

import html
import importlib
import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import css_inline
import latex2mathml.converter
from bs4 import BeautifulSoup
from mistletoe import span_token
from mistletoe.html_renderer import HTMLRenderer

from ..cache import (
    compute_hash,
    get_from_cache,
    renderer_tool_versions,
    save_to_cache,
)
from ..exceptions import (
    LatexCompilationError,
    MarkdownAttributeError,
    QuizMLConfigError,
)
from .extensions import ImageWithWidth, MathDisplay, MathInline
from .image_embedding import embed_base64
from .latextools import LatexRunner
from .macros import LatexMacroExpander, preprocess_latex_for_mathml

_DEFAULT_HTML_PREAMBLE = (
    "\\usepackage{amsmath}\n\\usepackage{notomath}\n\\usepackage[OT1]{fontenc}\n"
)

_DEFAULT_INLINE_CSS = """
.math.inline {vertical-align:middle}
pre {
      background:#eee;
      padding: 0.5em;
      max-width: 80em;
      line-height:1em;
}
code {
      font-family: ui-monospace, 'Cascadia Mono', 'Segoe UI Mono',
                   Menlo, Monaco, Consolas, monospace;
      font-size: 80%;
      line-height: 1.5em;
}
"""


def _append_unique(lst1: list[Any], lst2: list[Any]) -> list[Any]:
    """Append items from ``lst2`` into ``lst1`` if not already present."""
    for a in lst2:
        if a not in lst1:
            lst1.append(a)
    return lst1


def get_eq_list_from_doc(doc: Any) -> list[MathInline | MathDisplay]:
    """Return a deduplicated list of ``MathInline``/``MathDisplay`` nodes in ``doc``."""
    eq_list: list[MathInline | MathDisplay] = []
    if hasattr(doc, "children") and doc.children is not None:
        for a in doc.children:
            eq_list = _append_unique(eq_list, get_eq_list_from_doc(a))
    elif isinstance(doc, (MathInline, MathDisplay)):
        eq_list.append(doc)
    return eq_list


def strip_newlines_and_tabs(html_content: str) -> str:
    """Remove raw newlines and tabs from ``html_content`` for tab-delimited exports.

    Inside ``<code>...</code>`` elements, newlines are converted into ``<br>``
    tags so multi-line code blocks preserve line breaks inside Blackboard TSV rows.
    """
    htmlsrc = BeautifulSoup(html_content, "html.parser")
    for code in htmlsrc.find_all(name="code"):
        s = BeautifulSoup(str(code).replace("\n", "<br>"), "html.parser")
        code.replace_with(s)

    html_content = str(htmlsrc)
    return html_content.replace("\n", " ").replace("\t", "  ")


def escape_LaTeX(str_eq: str) -> str:
    r"""HTML-escape a LaTeX equation string for use inside an ``alt`` attribute.

    Transforms:
    - Outer ``$...$`` and ``$$...$$`` delimiters into ``\(...\)`` and ``\[...\]``.
    - Inner ``$`` characters into ``&dollar;``.
    - HTML special characters (``<``, ``>``, ``&``, ``"``, ``'``) into entities.
    - Newlines and tabs into spaces.
    """
    re_single_dollar = r"^\s*\$([^\$]*)\$\s*$"
    re_double_dollar = r"^\s*\$\$([^\$]*)\$\$\s*$"

    m = re.search(re_single_dollar, str_eq)
    if m:
        str_eq = r"\(" + m.group(1) + r"\)"

    m = re.search(re_double_dollar, str_eq)
    if m:
        str_eq = r"\[" + m.group(1) + r"\]"

    replace_with = {
        "<": "&lt;",
        ">": "&gt;",
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#39;",
        "$": "&dollar;",
    }
    quote_pattern = re.compile(r"""([&<>"'$])(?!(amp|lt|gt|quot|#39|dollar);)""")

    str_eq = re.sub(quote_pattern, lambda x: replace_with[x.group(0)], str_eq)
    str_eq = re.sub("\n", " ", str_eq)
    str_eq = re.sub("\t", " ", str_eq)
    return str_eq


def _equation_key(eq: MathInline | MathDisplay) -> str:
    """Return the internal lookup key (``##Inline##...`` or ``##Display##...``)."""
    kind = "Inline" if isinstance(eq, MathInline) else "Display"
    return f"##{kind}##{eq.content}"


def _cache_hash(content: str, settings_str: str) -> str:
    """Compute a cache key from equation content, settings, and tool versions."""
    backend = next(
        (name for name in ("PNG", "SVG", "MathML") if settings_str.endswith(name)),
        "",
    )
    return compute_hash(content, settings_str, renderer_tool_versions(backend))


def _cached_equations(
    eq_list: Sequence[MathInline | MathDisplay], settings_str: str
) -> tuple[dict[str, str], list[MathInline | MathDisplay]]:
    """Split ``eq_list`` into ``(cached_dict, uncached_equations_to_compile)``."""
    if not eq_list:
        return {}, []
    cached: dict[str, str] = {}
    to_compile: list[MathInline | MathDisplay] = []
    for eq in eq_list:
        key = _equation_key(eq)
        rendered = get_from_cache(_cache_hash(key, settings_str))
        if rendered:
            cached[key] = rendered
        else:
            to_compile.append(eq)
    return cached, to_compile


def _store_equation(
    eq: MathInline | MathDisplay,
    settings_str: str,
    rendered: str,
    eq_dict: dict[str, str],
) -> None:
    """Store a rendered equation in ``eq_dict`` and persist it in the disk cache."""
    kind = "inline" if isinstance(eq, MathInline) else "display"
    logging.debug(f"[eq-{kind}] '{rendered}'")
    key = _equation_key(eq)
    eq_dict[key] = rendered
    save_to_cache(_cache_hash(key, settings_str), rendered)


def _build_standalone_tex_preamble(opts: dict[str, Any]) -> str:
    """Build the ``standalone``/``preview`` LaTeX header for equation compilation."""
    template_latex_preamble = opts.get("html_pre", _DEFAULT_HTML_PREAMBLE)
    user_latex_preamble = opts.get("user_pre", "")
    return (
        "\\documentclass{article}\n"
        + template_latex_preamble
        + user_latex_preamble
        + "\\newenvironment{standalone}{\\begin{preview}}{\\end{preview}}\n"
        + "\\PassOptionsToPackage{active,tightpage}{preview}\n"
        + "\\usepackage{preview}\n"
        + "\\begin{document}\n"
    )


def _runner_kwargs(opts: dict[str, Any]) -> dict[str, Any]:
    """Extract ``LatexRunner`` keyword arguments from ``opts``."""
    kwargs: dict[str, Any] = {"tools": opts.get("tools")}
    if opts.get("tex_search_dirs"):
        kwargs["tex_search_dirs"] = opts["tex_search_dirs"]
    return kwargs


def build_eq_dict_PNG(
    eq_list: Sequence[MathInline | MathDisplay], opts: dict[str, Any]
) -> dict[str, str]:
    """Compile ``eq_list`` to base64 PNG ``<img>`` tags via ``pdflatex`` and ``gs``."""
    if not eq_list:
        return {}

    latex_preamble = _build_standalone_tex_preamble(opts)
    dpi = opts.get("png_dpi", 250)
    scale = float(opts.get("png_scale", 0.5))
    tools = opts.get("tools") or {}

    settings_str = (
        f"{latex_preamble}|dpi={dpi}|scale={scale}|tools={sorted(tools.items())}|PNG"
    )
    eq_dict, to_compile = _cached_equations(eq_list, settings_str)
    if not to_compile:
        return eq_dict

    # Emit one standalone page per equation, logging the baseline depth ratio
    # (dp0 / wd0) via \typeout{::: ...} so inline images align with surrounding text.
    latex_body = ""
    for eq in to_compile:
        if isinstance(eq, MathInline):
            latex_body += "\\setbox0=\\hbox{" + eq.content + "}\n"
            latex_body += (
                "\\makeatletter\\typeout{:::"
                " \\strip@pt\\dimexpr 1pt * \\dp0 / \\wd0\\relax}\\makeatother\n"
            )
            latex_body += "\\begin{standalone}\\copy0\\end{standalone}\n"
        if isinstance(eq, MathDisplay):
            latex_body += "\\typeout{::: 0}\n"
            latex_body += "\\begin{standalone}" + eq.content + "\\end{standalone}\n"

    latex_content = latex_preamble + latex_body + "\\end{document}\n"

    try:
        with LatexRunner(**_runner_kwargs(opts)) as latex_runner:
            pdf_filename, depthratio = latex_runner.run_pdflatex(latex_content)
            png_files = (
                latex_runner.run_gs_png(pdf_filename)
                if dpi == 250
                else latex_runner.run_gs_png(pdf_filename, dpi=dpi)
            )

            if len(png_files) != len(to_compile):
                raise LatexCompilationError(
                    f"Mismatch between number of equations and compiled PNG images.\n"
                    f"Expected {len(to_compile)}, got {len(png_files)}."
                )
            if len(depthratio) != len(to_compile):
                raise LatexCompilationError(
                    f"Mismatch between number of equations and depth ratio entries.\n"
                    f"Expected {len(to_compile)}, got {len(depthratio)}."
                )

            for i, (eq, png_file) in enumerate(zip(to_compile, png_files, strict=True)):
                w, h, data64 = embed_base64(png_file)
                d_ = round(depthratio[i] * w * scale, 2)
                w_ = round(w * scale)
                h_ = round(h * scale)

                if isinstance(eq, MathInline):
                    html_img = (
                        f"<img src='{data64}'"
                        f" alt='{escape_LaTeX(eq.content)}'"
                        f" width='{w_}' height='{h_}'"
                        f" style='vertical-align:{-d_}px;'>"
                    )
                else:
                    html_img = (
                        f"<img src='{data64}'"
                        f" alt='{escape_LaTeX(eq.content)}'"
                        f" width='{w_}' height='{h_}'>"
                    )
                _store_equation(eq, settings_str, html_img, eq_dict)

    except LatexCompilationError as e:
        raise LatexCompilationError(f"PNG equation rendering failed: {e}") from e

    return eq_dict


def build_eq_dict_SVG(
    eq_list: Sequence[MathInline | MathDisplay], opts: dict[str, Any]
) -> dict[str, str]:
    """Compile ``eq_list`` to base64 SVG ``<img>`` tags via ``latex`` + ``dvisvgm``."""
    if not eq_list:
        return {}

    latex_preamble = _build_standalone_tex_preamble(opts)
    svg_scale = opts.get("svg_scale", 1.2)
    tools = opts.get("tools") or {}
    settings_str = (
        f"{latex_preamble}|scale={svg_scale}|tools={sorted(tools.items())}|SVG"
    )
    eq_dict, to_compile = _cached_equations(eq_list, settings_str)
    if not to_compile:
        return eq_dict

    latex_body = ""
    for eq in to_compile:
        if isinstance(eq, MathInline):
            latex_body += "\\sbox{0}{" + eq.content + "}\n"
            latex_body += "\\ifdim\\dimexpr\\ht0-\\dp0>4.8pt\n"
            latex_body += "\\dp0\\dimexpr\\ht0-4.8pt\\fi\n"
            latex_body += (
                "\\begin{standalone}\\setlength\\fboxrule{0.00001pt}"
                "\\setlength\\fboxsep{0pt}\\fbox{\\usebox{0}}\\end{standalone}\n"
            )
        if isinstance(eq, MathDisplay):
            latex_body += "\\begin{standalone}" + eq.content + "\\end{standalone}\n"

    latex_content = latex_preamble + latex_body + "\\end{document}\n"

    try:
        with LatexRunner(**_runner_kwargs(opts)) as latex_runner:
            dvi_path = latex_runner.run_latex_dvi(latex_content)
            svg_files = (
                latex_runner.run_dvisvgm_svg(dvi_path)
                if svg_scale == 1.2
                else latex_runner.run_dvisvgm_svg(dvi_path, scale=svg_scale)
            )

            if len(svg_files) != len(to_compile):
                raise LatexCompilationError(
                    f"Mismatch between number of equations and compiled SVG images.\n"
                    f"Expected {len(to_compile)}, got {len(svg_files)}."
                )

            for eq, svg_file in zip(to_compile, svg_files, strict=True):
                _, _, data64 = embed_base64(svg_file)
                html_img = (
                    f"<img src='{data64}' alt='{escape_LaTeX(eq.content)}' "
                    "style='vertical-align:middle;'>"
                )
                _store_equation(eq, settings_str, html_img, eq_dict)

    except LatexCompilationError as e:
        raise LatexCompilationError(f"SVG equation rendering failed: {e}") from e

    return eq_dict


def strip_math_delimiters(content: str) -> str:
    r"""Strip outer math delimiters ($...$, $$...$$, \(...\), \[...\])."""
    s = content.strip()
    if s.startswith("$$") and s.endswith("$$") and len(s) >= 4:
        return s[2:-2].strip()
    if s.startswith(r"\[") and s.endswith(r"\]") and len(s) >= 4:
        return s[2:-2].strip()
    if s.startswith("$") and s.endswith("$") and len(s) >= 2:
        return s[1:-1].strip()
    if s.startswith(r"\(") and s.endswith(r"\)") and len(s) >= 4:
        return s[2:-2].strip()
    return s


def build_eq_dict_MathML(
    eq_list: Sequence[MathInline | MathDisplay], opts: dict[str, Any]
) -> dict[str, str]:
    """Convert ``eq_list`` to MathML strings using ``latex2mathml`` and macros."""
    if not eq_list:
        return {}

    template_latex_preamble = opts.get("html_pre", "\\usepackage{amsmath}\n")
    user_latex_preamble = opts.get("user_pre", "")
    full_preamble = template_latex_preamble + "\n" + user_latex_preamble

    settings_str = f"{full_preamble}|MathML"
    eq_dict, to_compile = _cached_equations(eq_list, settings_str)
    if not to_compile:
        return eq_dict

    expander = LatexMacroExpander(full_preamble)

    for eq in to_compile:
        clean_latex = strip_math_delimiters(eq.content)
        expanded_latex = expander.expand(clean_latex)
        preprocessed_latex = preprocess_latex_for_mathml(expanded_latex)
        disp_mode = "inline" if isinstance(eq, MathInline) else "block"
        try:
            mathml = latex2mathml.converter.convert(
                preprocessed_latex, display=disp_mode
            )
            mathml = re.sub(r"&(?![a-zA-Z0-9#]+;)", "&amp;", mathml)
        except Exception as err:
            raise LatexCompilationError(
                f"latex2mathml failed on equation: {eq.content}\n"
                f"Expanded: {preprocessed_latex}\nError: {err}"
            ) from err

        _store_equation(eq, settings_str, mathml, eq_dict)

    return eq_dict


def build_eq_dict_passthrough(
    eq_list: Sequence[MathInline | MathDisplay],
) -> dict[str, str]:
    """Return pass-through LaTeX equations wrapped in HTML ``<span>``/``<div>`` tags."""
    eq_dict: dict[str, str] = {}
    for eq in eq_list:
        key = _equation_key(eq)
        escaped = escape_LaTeX(eq.content)
        if isinstance(eq, MathInline):
            eq_dict[key] = f'<span class="math inline">{escaped}</span>'
        else:
            eq_dict[key] = f'<div class="math display">{escaped}</div>'
    return eq_dict


def _build_equations_for_format(
    eq_list: Sequence[MathInline | MathDisplay], opts: dict[str, Any]
) -> dict[str, str]:
    """Dispatch equation compilation based on ``opts['fmt']``."""
    fmt = opts.get("fmt", "")
    if fmt == "html-svg":
        return build_eq_dict_SVG(eq_list, opts)
    if fmt == "html-mathml":
        return build_eq_dict_MathML(eq_list, opts)
    if fmt == "html-passthrough":
        return build_eq_dict_passthrough(eq_list)
    return build_eq_dict_PNG(eq_list, opts)


class QuizMLYamlHTMLRenderer(HTMLRenderer):
    """Customized Mistletoe renderer for HTML with base64 images and math lookup."""

    def __init__(
        self,
        eq_dict: dict[str, str],
        base_dir: str | Path | None = None,
        search_dirs: Sequence[str | Path] | None = None,
    ) -> None:
        super().__init__(MathInline, MathDisplay, ImageWithWidth)
        self.eq_dict = eq_dict
        self.base_dir = base_dir
        self.search_dirs: list[str | Path] = list(search_dirs or [])

    def render_math_inline(self, token: MathInline) -> str:
        return self.eq_dict["##Inline##" + token.content]

    def render_math_display(self, token: MathDisplay) -> str:
        return self.eq_dict["##Display##" + token.content]

    def render_image(self, token: span_token.Image) -> str:
        template = '<img src="{}" alt="{}"{} >'
        title = f' title="{html.escape(token.title)}"' if token.title else ""
        _w, _h, data64 = embed_base64(
            token.src, base_dir=self.base_dir, search_dirs=self.search_dirs
        )
        return template.format(data64, self.render_to_plain(token), title)

    def render_image_with_width(self, token: ImageWithWidth) -> str:
        _w, _h, data64_img = embed_base64(
            token.src, base_dir=self.base_dir, search_dirs=self.search_dirs
        )
        width_attr_str = token.width.strip()

        linewidth_match = re.match(r"^(\d*\.?\d*)\s*\\linewidth$", width_attr_str)
        if linewidth_match:
            factor = (
                float(linewidth_match.group(1)) if linewidth_match.group(1) else 1.0
            )
            css_width = f"{factor * 100:.4g}%"
        elif re.match(
            r"^\d*\.?\d+\s*(?:%|px|cm|mm|in|pt|pc|em|rem|vw|vh)$", width_attr_str
        ):
            css_width = width_attr_str
        elif re.match(r"^\d+$", width_attr_str):
            css_width = f"{width_attr_str}px"
        else:
            raise MarkdownAttributeError(f"Sorry, bad width attr: '{width_attr_str}'")

        alt_text = html.escape(token.title) if token.title else ""
        return f'<img src="{data64_img}" alt="{alt_text}" style="width:{css_width};" >'


def get_html(doc: Any, opts: dict[str, Any]) -> str:
    """Render HTML for a single Mistletoe AST ``doc``."""
    eq_list = get_eq_list_from_doc(doc)
    eq_dict = _build_equations_for_format(eq_list, opts)
    with QuizMLYamlHTMLRenderer(eq_dict) as renderer:
        return renderer.render(doc)


def inline_css(html_content: str, opts: dict[str, Any]) -> str:
    """Inline CSS styles into ``html_content`` elements using ``css_inline``."""
    if "html_css" in opts:
        css = re.sub(re.compile(r"/\*.*?\*/", re.DOTALL), "", opts["html_css"])
    else:
        css = _DEFAULT_INLINE_CSS

    css = css.replace("\n", " ").replace("\t", "  ")
    html_payload = (
        f"<html><head><style>{css}</style></head><body>{html_content}</body></html>"
    )
    out = css_inline.inline(html_payload)
    soup = BeautifulSoup(out, "html.parser")
    return soup.body.decode_contents() if soup.body else out


def _apply_html_postprocess(
    html_raw: str, postprocess: Any, opts: dict[str, Any]
) -> str:
    """Apply optional HTML post-processing (``blackboard_html`` or custom callable)."""
    if postprocess is None:
        return html_raw
    if postprocess == "blackboard_html":
        html_inlined = inline_css(html_raw, opts)
        return strip_newlines_and_tabs(html_inlined)
    if callable(postprocess):
        try:
            return postprocess(html_raw, opts)
        except TypeError:
            return postprocess(html_raw)
    if isinstance(postprocess, str) and ":" in postprocess:
        mod_name, attr_name = postprocess.split(":", 1)
        try:
            module = importlib.import_module(mod_name)
            func = getattr(module, attr_name)
        except (ImportError, AttributeError) as err:
            raise QuizMLConfigError(
                f"Could not load HTML postprocessor '{postprocess}': {err}"
            ) from err
        if not callable(func):
            raise QuizMLConfigError(
                f"HTML postprocessor '{postprocess}' is not callable."
            )
        try:
            return func(html_raw, opts)
        except TypeError:
            return func(html_raw)
    raise ValueError(f"Unknown HTML postprocessor: {postprocess}")


def get_html_dict(
    ast_dict: dict[str, Any],
    opts: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
    search_dirs: Sequence[str | Path] | None = None,
) -> dict[str, str]:
    """Batch-compile equations and render HTML for all AST documents in ``ast_dict``."""
    opts = dict(opts) if opts else {}
    if "tex_search_dirs" not in opts:
        tex_dirs: list[str | Path] = []
        if base_dir:
            tex_dirs.append(base_dir)
        if search_dirs:
            tex_dirs.extend(search_dirs)
        if tex_dirs:
            opts["tex_search_dirs"] = tex_dirs

    # 1. Collect all unique equations across all AST documents in batch.
    eq_list: list[MathInline | MathDisplay] = []
    for doc in ast_dict.values():
        eq_list = _append_unique(eq_list, get_eq_list_from_doc(doc))

    # 2. Batch-compile equations for the active math backend.
    eq_dict = _build_equations_for_format(eq_list, opts)

    # 3. Render each document and apply optional postprocessor.
    md_dict: dict[str, str] = {}
    postprocess = opts.get("html_postprocess")
    with QuizMLYamlHTMLRenderer(
        eq_dict, base_dir=base_dir, search_dirs=search_dirs
    ) as renderer:
        for txt, doc in ast_dict.items():
            html_raw = renderer.render(doc)
            md_dict[txt] = _apply_html_postprocess(html_raw, postprocess, opts)

    return md_dict
