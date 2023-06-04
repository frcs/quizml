import logging

import mistletoe
from mistletoe.latex_renderer import LaTeXRenderer

from .utils import get_hash
from .extensions import MathInline, MathDisplay, ImageWithWidth

class BBYamlLaTeXRenderer(LaTeXRenderer):
    """
    customised mistletoe renderer for LaTeX
    implements render for custom spans MathInline, MathDisplay, ImageWithWidth
    """
    
    def __init__(self):
        super().__init__(MathInline,MathDisplay,ImageWithWidth)

    def render_document(self, token):
        # we need to redefine this to strip out
        # \begin{document} ... \end{document}        
        return self.render_inner(token)

    def render_math_inline(self, token):
        return "$" + token.content.strip() + "$"

    def render_math_display(self, token):
        print("token.content")
        return "\\begin{equation}\n" + token.content.strip() + "\n\\end{equation}"

    def render_image_with_width(self, token) -> str:
        return '\\includegraphics[width=' + token.width + ']{' + token.src + '}'  


def get_latex(doc):
    """
    returns the rendered LaTeX source for mistletoe object
    """
   
    with BBYamlLaTeXRenderer() as renderer:
        latex_content = renderer.render(doc)

    # svg is a bit of a problem. replacing .svg extensions with .pdf   
    latex_content = latex_content.replace('.svg}', '.pdf}')
    latex_content = latex_content.replace('\includesvg', '\includegraphics')

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
            raise()
        else:
            start = latex_result.find("}\n", start) + 1            
        end = latex_result.find("\\section{", start + 1)
        latex_content = latex_result[start:end].strip()
        md_dict[txt] = latex_content

    return md_dict





