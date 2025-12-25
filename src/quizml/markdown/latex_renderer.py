import logging
import os
import shutil
import subprocess

import mistletoe
from mistletoe.latex_renderer import LaTeXRenderer
from mistletoe.block_token import HTMLBlock

from .utils import get_hash
from .extensions import MathInline, MathDisplay, ImageWithWidth
from ..exceptions import MarkdownError


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
        logging.warning(f"Could not find rsvg-convert or inkscape to convert {svg_path} to PDF.")
        return False

    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        logging.warning(f"Failed to convert {svg_path} to PDF.")
        return False


def resolve_image_path(src):
    """
    Resolves the image path for LaTeX.
    Prioritizes PDF > PNG > JPG/JPEG.
    If SVG is provided and no compatible format is found, attempts conversion
    if tools are available.
    """
    if not src.lower().endswith(".svg"):
        return src
        
    base = os.path.splitext(src)[0]
    
    # Check for existing compatible formats
    for ext in ['.pdf', '.png', '.jpg', '.jpeg']:
        candidate = base + ext
        if os.path.exists(candidate):
            return candidate
            
    # If no compatible format exists, try conversion
    pdf_path = base + ".pdf"
    if convert_svg_to_pdf(src, pdf_path):
        return pdf_path
        
    # If conversion fails/tools missing, return src (latex will likely complain)
    return src


class QuizMLYamlLaTeXRenderer(LaTeXRenderer):
    """
    customised mistletoe renderer for LaTeX
    implements render for custom spans MathInline, MathDisplay, ImageWithWidth
    """
    
    def __init__(self):
        super().__init__(MathInline,MathDisplay,ImageWithWidth,HTMLBlock)

    def render_document(self, token):
        # we need to redefine this to strip out
        # \begin{document} ... \end{document}        
        return self.render_inner(token)

    def render_math_inline(self, token):
        return token.content.strip()

    def render_math_display(self, token):
        return token.content.strip()

    def render_image_with_width(self, token) -> str:
        src = resolve_image_path(token.src)
        return '\\includegraphics[width=' + token.width + ']{' + src + '}'  

    # def render_command(self, token) -> str:
    #     return '\\' + token.cmdname + '{' + token.cmd + '}'  

    def render_html_block(self, token):
        return ''

    # fixing some default behaviour
    def render_table(self, token):
        return '\n\\medskip\n' + super().render_table(token) + '\n\\medskip\n'

    # fixing some default behaviour
    def render_image(self, token):
        token.src = resolve_image_path(token.src)
        s = super().render_image(token)
        return s[1:-1]

    # fixing some default behaviour
    def render_figure(self, token):
        s = self.render_inner(token)
        
        if self.caption:
            return s[1:-1]

    
    # def render_paragraph(self, token):
    #     s = super().render_paragraph(token.strip()) 
        
def get_latex(doc):
    """
    returns the rendered LaTeX source for mistletoe object
    """
   
    with QuizMLYamlLaTeXRenderer() as renderer:
        latex_content = renderer.render(doc)
       
    # svg is a bit of a problem. replacing .svg extensions with .pdf   
    # latex_content = latex_content.replace('.svg}', '.pdf}') # Removed: handled in renderer
    latex_content = latex_content.replace('\\includesvg', '\\includegraphics')

    # I should check if this is still relevant... (pandoc legacy?)
    latex_content = latex_content.replace(',height=\\textheight', '')
    latex_content = latex_content.replace('\\passthrough', '')

    return latex_content
        

def get_latex_dict(combined_doc, md_list):
    """
    md_list: a list of markdown entries
    combined_doc: the mistletoe object for the collation of all these entries
    
    renders the LaTeX source of a collation of mardown entries
    and build a dictionary of these renders.
    """

    latex_result = get_latex(combined_doc)

    md_dict = {}

    for txt in md_list:
        h = get_hash(txt)
        latex_section = "\\section{" + h + "}"
        start = latex_result.find(latex_section)
        if (start < 0):
            logging.error(
                "couldn't find hash in md_list. This shouldn't happen."
                + "I'm quitting.\n")
            raise MarkdownError("couldn't find hash in md_list")
        else:
            start = latex_result.find("}\n", start) + 1
        end = latex_result.find("\\section{", start + 1)
        if end == -1:
            end = len(latex_result)
        latex_content = latex_result[start:end].strip()

        md_dict[txt] = latex_content

    return md_dict





