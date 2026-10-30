"""Mistletoe LaTeX renderer and SVG-to-PDF asset conversion for QuizML."""

import hashlib
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from mistletoe.block_token import HTMLBlock
from mistletoe.latex_renderer import LaTeXRenderer

from ..cache import get_cache_dir, renderer_tool_versions
from ..paths import find_path
from .extensions import ImageWithWidth, MathDisplay, MathInline


def _build_svg_converter_cmd(
    svg_path: str, pdf_path: str, converter: str | Sequence[str] | None
) -> list[str] | None:
    """Build the command-line invocation to convert ``svg_path`` into ``pdf_path``."""
    if converter:
        if isinstance(converter, str):
            if "{input}" in converter or "{output}" in converter:
                return shlex.split(converter.format(input=svg_path, output=pdf_path))
            if converter == "rsvg-convert":
                return ["rsvg-convert", "-f", "pdf", "-o", pdf_path, svg_path]
            if converter == "inkscape":
                return ["inkscape", svg_path, f"--export-filename={pdf_path}"]
            return [*shlex.split(converter), svg_path, pdf_path]
        return [str(part).format(input=svg_path, output=pdf_path) for part in converter]
    if shutil.which("rsvg-convert"):
        return ["rsvg-convert", "-f", "pdf", "-o", pdf_path, svg_path]
    if shutil.which("inkscape"):
        return ["inkscape", svg_path, f"--export-filename={pdf_path}"]
    return None


def convert_svg_to_pdf(
    svg_path: str, pdf_path: str, converter: str | Sequence[str] | None = None
) -> bool:
    """Convert an SVG file to PDF via ``rsvg-convert``, ``inkscape``, or custom tool."""
    cmd = _build_svg_converter_cmd(svg_path, pdf_path, converter)
    if cmd is None:
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


def _convert_svg_with_cache(
    svg_path: Path, svg_converter: str | Sequence[str] | None
) -> str | None:
    """Convert ``svg_path`` to a cached PDF in the application cache directory."""
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
    return None


def resolve_image_path(
    src: str,
    base_dir: str | Path | None = None,
    search_dirs: Sequence[str | Path] | None = None,
    svg_converter: str | Sequence[str] | None = None,
) -> str:
    """Resolve an image path for LaTeX ``\\includegraphics``.

    Prioritizes existing PDF > PNG > JPG/JPEG siblings when given an ``.svg``
    asset, and falls back to converting the SVG to a cached PDF.
    """
    dirs_to_check: list[str | Path] = []
    if not os.path.isabs(src):
        if search_dirs:
            dirs_to_check.extend(search_dirs)
        if base_dir:
            dirs_to_check.append(base_dir)

    exact_match = find_path(src, dirs_to_check)
    actual_src = str(exact_match[0]) if exact_match else src
    found_in_search_dirs = (
        exact_match is not None
        and exact_match[1] is not None
        and exact_match[1] < len(search_dirs or [])
    )

    if not src.lower().endswith(".svg"):
        return src if found_in_search_dirs else actual_src

    src_base_name = os.path.splitext(src)[0]
    for ext in (".pdf", ".png", ".jpg", ".jpeg"):
        if found_in_search_dirs:
            candidate = find_path(src_base_name + ext, [os.path.dirname(actual_src)])
            if candidate:
                return src_base_name + ext
        candidate = find_path(src_base_name + ext, dirs_to_check)
        if candidate:
            if candidate[1] is not None and candidate[1] < len(search_dirs or []):
                return src_base_name + ext
            return str(candidate[0])

    if os.path.exists(actual_src):
        cached_pdf = _convert_svg_with_cache(Path(actual_src).resolve(), svg_converter)
        if cached_pdf is not None:
            return cached_pdf

    return src if found_in_search_dirs else actual_src


_LATEX_INLINE_CODE_ESCAPES: dict[str, str] = {
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
    """Escape special LaTeX characters for inline code inside ``\\texttt{...}``."""
    return _LATEX_CODE_ESCAPE_PATTERN.sub(
        lambda m: _LATEX_INLINE_CODE_ESCAPES[m.group(0)], text
    )


class QuizMLYamlLaTeXRenderer(LaTeXRenderer):
    """Customized Mistletoe renderer for LaTeX output."""

    def __init__(
        self,
        base_dir: str | Path | None = None,
        search_dirs: Sequence[str | Path] | None = None,
        svg_converter: str | Sequence[str] | None = None,
    ) -> None:
        self.base_dir = base_dir
        self.search_dirs: list[str | Path] = list(search_dirs or [])
        self.svg_converter = svg_converter
        super().__init__(MathInline, MathDisplay, ImageWithWidth, HTMLBlock)

    def render_document(self, token: Any) -> str:
        """Render document body without Mistletoe's ``\\begin{document}`` wrapper."""
        return self.render_inner(token)

    def render_inline_code(self, token: Any) -> str:
        """Render inline code with ``\\texttt`` so it works inside macro arguments."""
        code = token.children[0].content if token.children else ""
        return f"\\texttt{{{escape_latex_code(code)}}}"

    def render_math_inline(self, token: MathInline) -> str:
        return token.content.strip()

    def render_math_display(self, token: MathDisplay) -> str:
        return token.content.strip()

    def render_image_with_width(self, token: ImageWithWidth) -> str:
        kwargs = {"svg_converter": self.svg_converter} if self.svg_converter else {}
        src = resolve_image_path(
            token.src,
            self.base_dir,
            self.search_dirs,
            **kwargs,
        )
        return "\\includegraphics[width=" + token.width + "]{" + src + "}"

    def render_html_block(self, token: Any) -> str:
        return ""

    def render_table(self, token: Any) -> str:
        return "\n\\medskip\n" + super().render_table(token) + "\n\\medskip\n"

    def render_image(self, token: Any) -> str:
        original_src = token.src
        try:
            kwargs = {"svg_converter": self.svg_converter} if self.svg_converter else {}
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

    def render_figure(self, token: Any) -> str:
        s = self.render_inner(token)
        if self.caption:
            return s[1:-1]
        return s


def get_latex_dict(
    ast_dict: dict[str, Any],
    base_dir: str | Path | None = None,
    search_dirs: Sequence[str | Path] | None = None,
    opts: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Render a mapping of ``{markdown_text: latex_str}`` from parsed AST documents."""
    opts = opts or {}
    svg_converter = opts.get("svg_converter") or (opts.get("tools") or {}).get(
        "svg_converter"
    )
    md_dict: dict[str, str] = {}
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
