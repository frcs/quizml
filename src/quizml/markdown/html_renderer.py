import subprocess
import os
import sys
import yaml
import html
import re

from bs4 import BeautifulSoup
import css_inline

from subprocess import call
import tempfile
from collections import defaultdict
import logging

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

from rich.columns import Columns
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.spinner import Spinner

from mistletoe.html_renderer import HTMLRenderer

from .utils import append_unique, get_hash
from .image_embedding import embed_base64

from .extensions import MathInline, MathDisplay, ImageWithWidth
from .latextools import LatexRunner
from ..exceptions import LatexCompilationError, MarkdownAttributeError
from ..cache import compute_hash, get_from_cache, save_to_cache
from mistletoe import span_token


import base64


def get_eq_list_from_doc(doc):
    """returns a list of all the LaTeX equations (as mistletoe
    objects) in a mardown document (mistletoe object).

    """

    eq_list = []
    if hasattr(doc, 'children'):
        for a in doc.children:
            eq_list = append_unique(eq_list, get_eq_list_from_doc(a))
    elif isinstance(doc, MathInline) or isinstance(doc, MathDisplay):
        eq_list.append(doc)
    return eq_list


def strip_newlines_and_tabs(html_content):
    """removes all newline and tab characters from an HTML string.
    
    Problem: we need to remove any tab or any newline 
    from the string as it must be passed as a CSV entry
    for blackboard exams.

    Solution: we remove these characters everywhere. We need, however,
    to take care of <code> </code> blocks. There we need to replace
    '\n' with <br> so as preserve formatting inside these verbatim
    blocks.

    """
    
    htmlsrc = BeautifulSoup(html_content, "html.parser")
    for code in htmlsrc.findAll(name="code"):
        s = BeautifulSoup(str(code).replace('\n', '<br>'),
                          "html.parser")
        code.replace_with(s)
        
    html_content = str(htmlsrc)

    # now we can delete any spurious '\n' or '\t'
    
    html_content = html_content.replace('\n', ' ').replace('\t', '  ')

    return html_content   


def escape_LaTeX(str_eq):
    r"""HTML escape the LaTeX string defining an equation. This is to
    be used in the `alt` tag of the corresponding rendered image

    It applies the following transformations:    
    * convert main `$` and `$$` sign to `\(` and `\[`
    * convert other `$` into `&dollar;`
    * escape HTML
    * remove '\n' and '\t'

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
        '<': '&lt;',
        '>': '&gt;',
        '&': '&amp;',
        '"': '&quot;',
        "'": '&#39;',
        "$": '&dollar;'
    }
    quote_pattern = re.compile(
        r"""([&<>"'$])(?!(amp|lt|gt|quot|#39|dollar);)""")

    str_eq = re.sub(quote_pattern,
                    lambda x: replace_with[x.group(0)], str_eq)
    str_eq = re.sub('\n', ' ', str_eq)
    str_eq = re.sub('\t', ' ', str_eq)

    return str_eq


def build_eq_dict_PNG(eq_list, opts):
    """returns a dictionary of images from a list of LaTeX equations.

    LaTeX equations are compiled into a PDF document using pdflatex,
    with one equation per page.

    The PDF is then converted into PNG images using ghostscript (gs).

    """
    eq_dict = {}

    # if we don't have any equations, exit with empty dict
    if not eq_list:
        return eq_list

    if 'html_pre' in opts:
        template_latex_preamble = opts['html_pre']
    else:
        template_latex_preamble = (
            "\\usepackage{amsmath}\n"
            "\\usepackage{notomath}\n"
            "\\usepackage[OT1]{fontenc}\n"
        )

    user_latex_preamble = opts.get('user_pre', '')

    latex_preamble = (
        "\\documentclass{article}\n"
        + template_latex_preamble
        + user_latex_preamble
        + "\\newenvironment{standalone}{\\begin{preview}}{\\end{preview}}\n"
        + "\\PassOptionsToPackage{active,tightpage}{preview}\n"
        + "\\usepackage{preview}\n"
        + "\\begin{document}\n"
    )

    # Check cache first
    settings_str = latex_preamble + "PNG"
    to_compile = []
    
    for eq in eq_list:
        h = compute_hash(eq.content, settings_str)
        cached_html = get_from_cache(h)
        
        if isinstance(eq, MathInline):
            key = "##Inline##" + eq.content
        else:
            key = "##Display##" + eq.content
            
        if cached_html:
            eq_dict[key] = cached_html
        else:
            to_compile.append(eq)

    if not to_compile:
        return eq_dict

    latex_body = ""
    for eq in to_compile:
        if isinstance(eq, MathInline):
            latex_body += "\\setbox0=\\hbox{" + eq.content + "}\n"
            latex_body += ("\\makeatletter\\typeout{:::"
                           " \\strip@pt\\dimexpr 1pt * \\dp0 / \\wd0\\relax}\\makeatother\n")
            latex_body += "\\begin{standalone}\\copy0\\end{standalone}\n"
        if isinstance(eq, MathDisplay):
            latex_body += "\\typeout{::: 0}\n"
            latex_body += "\\begin{standalone}" + eq.content + "\\end{standalone}\n"

    latex_content = latex_preamble + latex_body + "\\end{document}\n"

    try:
        with LatexRunner() as latex_runner:
            pdf_filename, depthratio = latex_runner.run_pdflatex(latex_content)
            png_files = latex_runner.run_gs_png(pdf_filename)

            for i, (eq, png_file) in enumerate(zip(to_compile, png_files)):
                w, h, data64 = embed_base64(png_file)
                d = depthratio[i]
                d_ = round(d * w * 0.5, 2)
                w_ = round(w / 2)
                h_ = round(h / 2)
                
                html_img = ""
                if isinstance(eq, MathInline):
                    key = "##Inline##" + eq.content
                    html_img = (
                        f"<img src='{data64}'"
                        f" alt='{escape_LaTeX(eq.content)}'"
                        f" width='{w_}' height='{h_}'"
                        f" style='vertical-align:{-d_}px;'>"
                    )
                    logging.debug(f"[eq-inline] '{html_img}'")
                    eq_dict[key] = html_img
                else:
                    key = "##Display##" + eq.content
                    html_img = (
                        f"<img src='{data64}'"
                        f" alt='{escape_LaTeX(eq.content)}'"
                        f" width='{w_}' height='{h_}'>"
                    )
                    logging.debug(f"[eq-display] '{html_img}'")
                    eq_dict[key] = html_img
                
                # Save to cache
                h = compute_hash(eq.content, settings_str)
                save_to_cache(h, html_img)

    except (LatexCompilationError) as e:
        # Re-raise to be caught by the CLI
        raise e

    return eq_dict



def build_eq_dict_SVG(eq_list, opts):
    """returns a dictionary of images from a list of LaTeX equations.

    LaTeX equations are compiled into a DVI document using latex,
    with one equation per page.

    The DVI is then converted into SVG images using dvisvgm.
    """
    eq_dict = {}

    if not eq_list:
        return eq_list

    template_latex_preamble = opts.get('html_pre',
                                       "\\usepackage{amsmath}\n"
                                       "\\usepackage{notomath}\n"
                                       "\\usepackage[OT1]{fontenc}\n")
    user_latex_preamble = opts.get('user_pre', '')

    latex_preamble = (
        "\\documentclass{article}\n"
        + template_latex_preamble
        + user_latex_preamble
        + "\\newenvironment{standalone}{\\begin{preview}}{\\end{preview}}\n"
        + "\\PassOptionsToPackage{active,tightpage}{preview}\n"
        + "\\usepackage{preview}\n"
        + "\\begin{document}\n"
    )

    settings_str = latex_preamble + "SVG"
    to_compile = []

    for eq in eq_list:
        h = compute_hash(eq.content, settings_str)
        cached_html = get_from_cache(h)
        if isinstance(eq, MathInline):
            key = "##Inline##" + eq.content
        else:
            key = "##Display##" + eq.content
            
        if cached_html:
            eq_dict[key] = cached_html
        else:
            to_compile.append(eq)
            
    if not to_compile:
        return eq_dict

    latex_body = ""
    for eq in to_compile:
        if isinstance(eq, MathInline):
            latex_body += "\\sbox{0}{" + eq.content + "}\n"
            latex_body += "\\ifdim\\dimexpr\\ht0-\\dp0>4.8pt\n"
            latex_body += "\\dp0\\dimexpr\\ht0-4.8pt\\fi\n"
            latex_body += ("\\begin{standalone}\\setlength\\fboxrule{0.00001pt}"
                           "\\setlength\\fboxsep{0pt}\\fbox{\\usebox{0}}\\end{standalone}\n")
        if isinstance(eq, MathDisplay):
            latex_body += "\\begin{standalone}" + eq.content + "\\end{standalone}\n"

    latex_content = latex_preamble + latex_body + "\\end{document}\n"

    try:
        with LatexRunner() as latex_runner:
            dvi_path = latex_runner.run_latex_dvi(latex_content)
            svg_files = latex_runner.run_dvisvgm_svg(dvi_path)

            for eq, svg_file in zip(to_compile, svg_files):
                _, _, data64 = embed_base64(svg_file)
                alt_text = escape_LaTeX(eq.content)
                style = "vertical-align:middle;"

                html_img = ""
                if isinstance(eq, MathInline):
                    key = "##Inline##" + eq.content
                    html_img = f"<img src='{data64}' alt='{alt_text}' style='{style}'>"
                    logging.debug(f"[eq-inline] '{html_img}'")
                    eq_dict[key] = html_img
                else:
                    key = "##Display##" + eq.content
                    html_img = f"<img src='{data64}' alt='{alt_text}' style='{style}'>"
                    logging.debug(f"[eq-display] '{html_img}'")
                    eq_dict[key] = html_img
                
                # Save cache
                h = compute_hash(eq.content, settings_str)
                save_to_cache(h, html_img)

    except LatexCompilationError as e:
        raise e

    return eq_dict


def build_eq_dict_MathML(eq_list, opts):
    """returns a dictionary of MATHML eqs from a list of LaTeX equations.

    LaTeX equations are compiled into MATHML using make4ht.
    """
    eq_dict = {}

    if not eq_list:
        return eq_list

    template_latex_preamble = opts.get('html_pre', "\\usepackage{amsmath}\n")
    user_latex_preamble = opts.get('user_pre', '')

    latex_preamble = (
        "\\documentclass{article}\n"
        + template_latex_preamble
        + user_latex_preamble
        + "\\begin{document}\n"
    )

    settings_str = latex_preamble + "MathML"
    to_compile = []
    
    for eq in eq_list:
        h = compute_hash(eq.content, settings_str)
        cached_html = get_from_cache(h)
        if isinstance(eq, MathInline):
            key = "##Inline##" + eq.content
        else:
            key = "##Display##" + eq.content
        
        if cached_html:
            eq_dict[key] = cached_html
        else:
            to_compile.append(eq)
            
    if not to_compile:
        return eq_dict

    latex_body = "\n".join(eq.content for eq in to_compile)
    latex_content = latex_preamble + latex_body + "\n\\end{document}\n"

    try:
        with LatexRunner() as latex_runner:
            html_path = latex_runner.run_make4ht_mathml(latex_content)
            make4ht_out = html_path.read_text()

            regex = r"(<math.*?<\/math>)"
            eq_list_str = re.findall(regex, make4ht_out, re.DOTALL)

            if len(eq_list_str) != len(to_compile):
                raise LatexCompilationError(
                    "Mismatch between number of equations and make4ht output.\n"
                    f"Expected {len(to_compile)}, got {len(eq_list_str)}."
                )

            for i, eq in enumerate(to_compile):
                mathml = eq_list_str[i]
                h = compute_hash(eq.content, settings_str)
                save_to_cache(h, mathml)
                
                if isinstance(eq, MathInline):
                    key = "##Inline##" + eq.content
                    logging.debug(f"[eq-inline] '{mathml}'")
                    eq_dict[key] = mathml
                else:
                    key = "##Display##" + eq.content
                    logging.debug(f"[eq-display] '{mathml}'")
                    eq_dict[key] = mathml

    except LatexCompilationError as e:
        raise e

    return eq_dict




def strip_newlines_and_tabs(html_content):
    """removes all newline and tab characters from an HTML string.
    
    Problem: we need to remove any tab or any newline 
    from the string as it must be passed as a CSV entry
    for blackboard exams.

    Solution: we remove these characters everywhere. We need, however,
    to take care of <code> </code> blocks. There we need to replace
    '\n' with <br> so as preserve formatting inside these verbatim
    blocks.

    """
    
    htmlsrc = BeautifulSoup(html_content, "html.parser")
    for code in htmlsrc.find_all(name="code"):
        s = BeautifulSoup(str(code).replace('\n', '<br>'),
                          "html.parser")
        code.replace_with(s)
        
    html_content = str(htmlsrc)

    # now we can delete any spurious '\n' or '\t'
    
    html_content = html_content.replace('\n', ' ').replace('\t', '  ')

    return html_content   


def escape_LaTeX(str_eq):
    r"""HTML escape the LaTeX string defining an equation. This is to
    be used in the `alt` tag of the corresponding rendered image

    It applies the following transformations:    
    * convert main `$` and `$$` sign to `\(` and `\[`
    * convert other `$` into `&dollar;`
    * escape HTML
    * remove '\n' and '\t'

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
        '<': '&lt;',
        '>': '&gt;',
        '&': '&amp;',
        '"': '&quot;',
        "'": '&#39;',
        "$": '&dollar;'
    }
    quote_pattern = re.compile(
        r"""([&<>"'$])(?!(amp|lt|gt|quot|#39|dollar);)""")

    str_eq = re.sub(quote_pattern,
                    lambda x: replace_with[x.group(0)], str_eq)
    str_eq = re.sub('\n', ' ', str_eq)
    str_eq = re.sub('\t', ' ', str_eq)

    return str_eq
    
    

class QuizMLYamlHTMLRenderer(HTMLRenderer):
    """customised mistletoe renderer for HTML

    implements render for custom spans MathInline, MathDisplay,
    ImageWithWidth also reimplements Image to embbed the image as
    base64

    """
    
    def __init__(self, eq_dict):
        super().__init__(MathInline,MathDisplay,ImageWithWidth)
        self.eq_dict = eq_dict
        
    def render_math_inline(self, token):
        return self.eq_dict['##Inline##' + token.content]
    
    def render_math_display(self, token):
        return self.eq_dict['##Display##' + token.content]
    
    def render_image(self, token: span_token.Image) -> str:       
        template = '<img src="{}" alt="{}"{} >'
        if token.title:
            title = ' title="{}"'.format(html.escape(token.title))
        else:
            title = ''
        [w, h, data64] = embed_base64(token.src)            
        return template.format(data64, self.render_to_plain(token), title)
    
    def render_image_with_width(self, token) -> str:

        [w, h, data64_img] = embed_base64(token.src)

        width_attr_str = token.width.strip()

        width_attr_pattern = r"(\d+\.?\d+)\s*([a-zA-Z]+)"
        match = re.match(width_attr_pattern, width_attr_str)
        if match:
            width_attr_val = match.group(1)
            width_attr_ext = match.group(2)
        else:
            raise MarkdownAttributeError("Sorry, bad width attr")

        if width_attr_ext=='em':
            width_attr = float(width_attr_val) * 16
        else:
            width_attr = float(width_attr_val)
        
        height_attr = width_attr/w * h
        
        template = (f'<svg width="{width_attr}" height="{height_attr}" '
                    f'xmlns="http://www.w3.org/2000/svg">'
                    f'<image href="{data64_img}" x="0" y="0" '
                    f'width="{width_attr}" height="{height_attr}" /></svg>')

        data64_svg = f"data:image/svg+xml;base64," + \
                      base64.b64encode(str.encode(template)).decode('ascii')

        template = (f'<img src="{data64_svg}" '
                    f'width={width_attr} height="{height_attr}">')
        
        return template

        ## don't delete as yet, this is SVG free code
        ## but not playing great with BB2, maybe it's just a matter
        ## of inserting height and width to image tag
        #
        # template = '<img src="{}" alt="{}"{} style="width:{}">'
        # if token.title:
        #     title = ' title="{}"'.format(html.escape(token.title))
        # else:
        #     title = ''
        # [w, h, data64] = embed_base64(token.src)
        # return template.format(data64,
        #                        self.render_to_plain(token),
        #                        title,
        #                        token.width)
    


    
    
def get_html(doc, opts):
    """
    returns the rendered HTML source for mistletoe object
    """

    eq_list = get_eq_list_from_doc(doc)

    if opts.get('fmt', '') == 'html-svg':
        eq_dict = build_eq_dict_SVG(eq_list, opts)
    elif opts.get('fmt', '') == 'html-mathml':
        eq_dict = build_eq_dict_MathML(eq_list, opts)
    else:
        eq_dict = build_eq_dict_PNG(eq_list, opts)
        

    with QuizMLYamlHTMLRenderer(eq_dict) as renderer:
        html_result = renderer.render(doc)

    return html_result


def inline_css(html_content, opts):

    if 'html_css' in opts:
        css = opts['html_css']
        # remove all comments (/*COMMENT */) from string
        css = re.sub(re.compile(r"/\*.*?\*/", re.DOTALL), "", css)
    else:
        css = """
        .math.inline {vertical-align:middle}
        pre {
              background:#eee;
              padding: 0.5em;
              max-width: 80em;
              line-height:1em;
        }
        code { 
              font-family: ui-monospace,‘Cascadia Mono’,‘Segoe UI Mono’,
                           ‘Segoe UI Mono’, Menlo, Monaco, Consolas, monospace;
              font-size:80%;
              line-height:1.5em;
        }
        """

    css = css.replace('\n', ' ').replace('\t', '  ')
        
    html_payload = "<html><head><style>" + css + "</style>" + html_content + "</html>"
    out = css_inline.inline( html_payload )
    out = out[26:-15]

    return out


def get_html_dict(combined_doc, md_list, opts):
    """
    md_list: a list of markdown entries
    combined_doc: the mistletoe object for the collation of all these entries
    
    renders the HTML source of a collation of mardown entries
    and build a dictionary of these renders.
    """
    
    html_result = get_html(combined_doc, opts)

    
    md_dict = {}
    for i, txt in enumerate(md_list, start=1):
        h = get_hash(txt)
        html_h1 = "<h1>" + h + "</h1>"
        start = html_result.find(html_h1) + len(html_h1)
        end = html_result.find("<h1>", start + 1)
        if end == -1:
            end = len(html_result)
            
        html_content = html_result[start:end]
        html_content = inline_css(html_content, opts)
        html_content = strip_newlines_and_tabs(html_content)
        md_dict[txt] = html_content
    return md_dict
    

