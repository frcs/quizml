import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from mistletoe.block_token import HTMLBlock
from mistletoe.latex_renderer import LaTeXRenderer

from ..cache import get_cache_dir, renderer_tool_versions
from ..paths import find_path
from .extensions import ImageWithWidth, MathDisplay, MathInline


def convert_svg_to_pdf(svg_path, pdf_path, converter=None):
    """
    Converts an SVG file to PDF using rsvg-convert, inkscape, or a custom converter.
    """
    if converter:
        import shlex

        if isinstance(converter, str):
            if "{input}" in converter or "{output}" in converter:
                cmd = shlex.split(
                    converter.format(input=svg_path, output=pdf_path)
                )
            elif converter == "rsvg-convert":
                cmd = ["rsvg-convert", "-f", "pdf", "-o", pdf_path, svg_path]
            elif converter == "inkscape":
                cmd = ["inkscape", svg_path, "--export-filename=" + pdf_path]
            else:
                cmd = [*shlex.split(converter), svg_path, pdf_path]
        else:
            cmd = [str(part).format(input=svg_path, output=pdf_path) for part in converter]
    elif shutil.which("rsvg-convert"):
        cmd = ["rsvg-convert", "-f", "pdf", "-o", pdf_path, svg_path]
    elif shutil.which("inkscape"):
        # Inkscape 1.0+ CLI
        cmd = ["inkscape", svg_path, "--export-filename=" + pdf_path]
    else:
        logging.warning(
            f"Could not find rsvg-convert or inkscape to convert {svg_path} to PDF."
        )
        return False

    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.CalledProcessError) as err:
        logging.warning(f"Failed to convert {svg_path} to PDF: {err}")
        return False


def resolve_image_path(src, base_dir=None, search_dirs=None, svg_converter=None):
    """
    Resolves the image path for LaTeX.
    Prioritizes PDF > PNG > JPG/JPEG.
    If SVG is provided and no compatible format is found, attempts conversion
    if tools are available.
    """
    dirs_to_check = []
    if not os.path.isabs(src):
        if search_dirs:
            dirs_to_check.extend(search_dirs)
        if base_dir:
            dirs_to_check.append(base_dir)

    # 1. Try finding the exact file first
    exact_match = find_path(src, dirs_to_check)
    actual_src = str(exact_match[0]) if exact_match else src
    found_in_search_dirs = (
        exact_match is not None
        and exact_match[1] is not None
        and exact_match[1] < len(search_dirs or [])
    )

    # If not SVG, return if found or check cwd
    if not src.lower().endswith(".svg"):
        if found_in_search_dirs:
            return src
        return actual_src

    # For SVG, check for existing compatible formats in candidate dirs
    src_base_name = os.path.splitext(src)[0]
    for ext in [".pdf", ".png", ".jpg", ".jpeg"]:
        if found_in_search_dirs:
            candidate = find_path(src_base_name + ext, [os.path.dirname(actual_src)])
            if candidate:
                return src_base_name + ext
        candidate = find_path(src_base_name + ext, dirs_to_check)
        if candidate:
            if candidate[1] is not None and candidate[1] < len(search_dirs or []):
                return src_base_name + ext
            return str(candidate[0])

    # Keep generated conversions in the application cache, away from source assets.
    if os.path.exists(actual_src):
        svg_path = Path(actual_src).resolve()
        hasher = hashlib.sha256(svg_path.read_bytes())
        hasher.update(
            json.dumps(
                {
                    "tools": renderer_tool_versions("SVG_PDF"),
                    "converter": svg_converter or "",
                },
                sort_keys=True,
            ).encode("utf-8")
        )
        digest = hasher.hexdigest()
        cache_dir = get_cache_dir() / "svg-pdf"
        cache_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = cache_dir / f"{digest}.pdf"
        if pdf_path.exists():
            return str(pdf_path)

        with tempfile.NamedTemporaryFile(
            prefix=f"{digest}.", suffix=".pdf", dir=cache_dir, delete=False
        ) as temp_pdf:
            temp_pdf_path = Path(temp_pdf.name)
        try:
            conv_ok = (
                convert_svg_to_pdf(
                    str(svg_path), str(temp_pdf_path), converter=svg_converter
                )
                if svg_converter
                else convert_svg_to_pdf(str(svg_path), str(temp_pdf_path))
            )
            if conv_ok:
                temp_pdf_path.replace(pdf_path)
                return str(pdf_path)
        finally:
            temp_pdf_path.unlink(missing_ok=True)

    return src if found_in_search_dirs else actual_src


_LATEX_INLINE_CODE_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "^": r"\textasciicircum{}",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "%": r"\%",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
    "|": r"\textbar{}",
}
_LATEX_CODE_ESCAPE_PATTERN = re.compile(r"[\\{}$&#\^_~%<>|]")


def escape_latex_code(text: str) -> str:
    """
    Escapes special LaTeX characters for code text within \\texttt{...}.
    """
    return _LATEX_CODE_ESCAPE_PATTERN.sub(
        lambda m: _LATEX_INLINE_CODE_ESCAPES[m.group(0)], text
    )


class QuizMLYamlLaTeXRenderer(LaTeXRenderer):
    """
    customised mistletoe renderer for LaTeX
    implements render for custom spans MathInline, MathDisplay, ImageWithWidth
    """

    def __init__(self, base_dir=None, search_dirs=None, svg_converter=None):
        self.base_dir = base_dir
        self.search_dirs = search_dirs or []
        self.svg_converter = svg_converter
        super().__init__(MathInline, MathDisplay, ImageWithWidth, HTMLBlock)

    def render_document(self, token):
        # we need to redefine this to strip out
        # \begin{document} ... \end{document}
        return self.render_inner(token)

    def render_inline_code(self, token):
        # Use \texttt with escaped characters instead of \verb so inline code can
        # be safely embedded inside macro arguments (\textbf, \textit, headings, etc.)
        code = token.children[0].content if token.children else ""
        return f"\\texttt{{{escape_latex_code(code)}}}"

    def render_math_inline(self, token):
        return token.content.strip()

    def render_math_display(self, token):
        return token.content.strip()

    def render_image_with_width(self, token) -> str:
        kwargs = (
            {"svg_converter": self.svg_converter} if self.svg_converter else {}
        )
        src = resolve_image_path(
            token.src,
            self.base_dir,
            self.search_dirs,
            **kwargs,
        )
        return "\\includegraphics[width=" + token.width + "]{" + src + "}"

    def render_html_block(self, token):
        return ""

    # fixing some default behaviour
    def render_table(self, token):
        return "\n\\medskip\n" + super().render_table(token) + "\n\\medskip\n"

    # fixing some default behaviour
    def render_image(self, token):
        original_src = token.src
        try:
            kwargs = (
                {"svg_converter": self.svg_converter} if self.svg_converter else {}
            )
            token.src = resolve_image_path(
                token.src,
                self.base_dir,
                self.search_dirs,
                **kwargs,
            )
            s = super().render_image(token)
            return s[1:-1]
        finally:
            token.src = original_src

    # fixing some default behaviour
    def render_figure(self, token):
        s = self.render_inner(token)

        if self.caption:
            return s[1:-1]
        return s


def get_latex_dict(ast_dict, base_dir=None, search_dirs=None, opts=None):
    """
    Renders LaTeX for markdown entries from discrete AST documents.
    """
    opts = opts or {}
    svg_converter = opts.get("svg_converter") or (opts.get("tools") or {}).get(
        "svg_converter"
    )
    md_dict = {}
    with QuizMLYamlLaTeXRenderer(
        base_dir=base_dir, search_dirs=search_dirs, svg_converter=svg_converter
    ) as renderer:
        for txt, doc in ast_dict.items():
            latex_content = renderer.render(doc)
            latex_content = latex_content.replace("\\includesvg", "\\includegraphics")
            latex_content = latex_content.replace(",height=\\textheight", "")
            latex_content = latex_content.replace("\\passthrough", "")
            md_dict[txt] = latex_content.strip()
    return md_dict
