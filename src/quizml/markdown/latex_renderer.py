import logging
import os
import shutil
import subprocess

from mistletoe.block_token import HTMLBlock
from mistletoe.latex_renderer import LaTeXRenderer

from .extensions import ImageWithWidth, MathDisplay, MathInline


def convert_svg_to_pdf(svg_path, pdf_path):
    """
    Converts an SVG file to PDF using rsvg-convert or inkscape.
    """
    if shutil.which("rsvg-convert"):
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
    except subprocess.CalledProcessError:
        logging.warning(f"Failed to convert {svg_path} to PDF.")
        return False


def resolve_image_path(src, base_dir=None, search_dirs=None):
    """
    Resolves the image path for LaTeX.
    Prioritizes PDF > PNG > JPG/JPEG.
    If SVG is provided and no compatible format is found, attempts conversion
    if tools are available.
    """
    actual_src = src
    found_in_search_dirs = False

    dirs_to_check = []
    if not os.path.isabs(src):
        if search_dirs:
            dirs_to_check.extend([(d, True) for d in search_dirs])
        if base_dir:
            dirs_to_check.append((base_dir, False))

    # 1. Try finding the exact file first
    for d, is_search_dir in dirs_to_check:
        candidate = os.path.normpath(os.path.join(d, src))
        if os.path.exists(candidate):
            actual_src = candidate
            found_in_search_dirs = is_search_dir
            break

    # If not SVG, return if found or check cwd
    if not src.lower().endswith(".svg"):
        if found_in_search_dirs:
            return src
        return actual_src

    # For SVG, check for existing compatible formats in candidate dirs
    src_base_name = os.path.splitext(src)[0]
    for ext in [".pdf", ".png", ".jpg", ".jpeg"]:
        if found_in_search_dirs:
            candidate = os.path.splitext(actual_src)[0] + ext
            if os.path.exists(candidate):
                return src_base_name + ext
        for d, is_search_dir in dirs_to_check:
            candidate = os.path.normpath(os.path.join(d, src_base_name + ext))
            if os.path.exists(candidate):
                return src_base_name + ext if is_search_dir else candidate

    # If no compatible format exists, try converting the SVG if found
    if os.path.exists(actual_src):
        base = os.path.splitext(actual_src)[0]
        pdf_path = base + ".pdf"
        if convert_svg_to_pdf(actual_src, pdf_path):
            return src_base_name + ".pdf" if found_in_search_dirs else pdf_path

    return src if found_in_search_dirs else actual_src


class QuizMLYamlLaTeXRenderer(LaTeXRenderer):
    """
    customised mistletoe renderer for LaTeX
    implements render for custom spans MathInline, MathDisplay, ImageWithWidth
    """

    def __init__(self, base_dir=None, search_dirs=None):
        self.base_dir = base_dir
        self.search_dirs = search_dirs or []
        super().__init__(MathInline, MathDisplay, ImageWithWidth, HTMLBlock)

    def render_document(self, token):
        # we need to redefine this to strip out
        # \begin{document} ... \end{document}
        return self.render_inner(token)

    def render_math_inline(self, token):
        return token.content.strip()

    def render_math_display(self, token):
        return token.content.strip()

    def render_image_with_width(self, token) -> str:
        src = resolve_image_path(token.src, self.base_dir, self.search_dirs)
        return "\\includegraphics[width=" + token.width + "]{" + src + "}"

    def render_html_block(self, token):
        return ""

    # fixing some default behaviour
    def render_table(self, token):
        return "\n\\medskip\n" + super().render_table(token) + "\n\\medskip\n"

    # fixing some default behaviour
    def render_image(self, token):
        token.src = resolve_image_path(token.src, self.base_dir, self.search_dirs)
        s = super().render_image(token)
        return s[1:-1]

    # fixing some default behaviour
    def render_figure(self, token):
        s = self.render_inner(token)

        if self.caption:
            return s[1:-1]


def get_latex_dict(ast_dict, base_dir=None, search_dirs=None):
    """
    Renders LaTeX for markdown entries from discrete AST documents.
    """
    md_dict = {}
    with QuizMLYamlLaTeXRenderer(base_dir=base_dir, search_dirs=search_dirs) as renderer:
        for txt, doc in ast_dict.items():
            latex_content = renderer.render(doc)
            latex_content = latex_content.replace("\\includesvg", "\\includegraphics")
            latex_content = latex_content.replace(",height=\\textheight", "")
            latex_content = latex_content.replace("\\passthrough", "")
            md_dict[txt] = latex_content.strip()
    return md_dict
