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
from ..exceptions import LatexEqError, MarkdownAttributeError

from mistletoe import span_token

import latex2mathml
import shutil
from pathlib import Path

import base64


import time

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
            "\\usepackage{amsmath}\n" +
            "\\usepackage{notomath}\n" +
            "\\usepackage[OT1]{fontenc}\n")

    user_latex_preamble = opts.get('user_pre','')
        
    latex_preamble = (
        "\\documentclass{article}\n" + 
        template_latex_preamble + 
        user_latex_preamble + 
        "\\newenvironment{standalone}{\\begin{preview}}{\\end{preview}}" +
        "\\PassOptionsToPackage{active,tightpage}{preview}" +
        "\\usepackage{preview}" +
        "\\begin{document}\n")

    tmpdir = tempfile.mkdtemp()
    olddir = os.getcwd()
    os.chdir(tmpdir)

    latex_filename = "eq_list.tex"
    pdf_filename = "eq_list.pdf"
    png_base = "eq_img_"

    f = open(latex_filename, 'w')
    f.write(latex_preamble)

    for eq in eq_list:
        if isinstance(eq, MathInline):
            # we want to also save the depth (drop below baseline)
            # of the inline equation.
            f.write("\\setbox0=\\hbox{" + eq.content + "}\n")
            f.write("\\makeatletter\\typeout{" +
                    "::: \\strip@pt\\dimexpr 1pt * \\dp0 / \\wd0\\relax}" +
                    "\\makeatother")
            f.write("\\begin{standalone}\\copy0\\end{standalone}\n")
        if isinstance(eq, MathDisplay):
            f.write("\\typeout{::: 0}")            
            f.write("\\begin{standalone}" + eq.content + "\\end{standalone}\n")

    f.write("\\end{document}\n")
    
    f.close()
    
    pdflatex = subprocess.Popen(
        ["pdflatex", "-interaction=nonstopmode",
         latex_filename],
        stdout = subprocess.PIPE,
        universal_newlines = True)
    found_pdflatex_errors = False

    pdflatex_progress =  Spinner("simpleDotsScrolling", "latex compilation")

    with Live(pdflatex_progress) as live:
        while pdflatex.poll()==None:
            pdflatex_progress.update()
    
    err_msg = ''
    depthratio = []
    for line in pdflatex.stdout:
        if line.startswith(':::') and not found_pdflatex_errors:
            depthratio.append(float(line[4:-1]))
        if line.startswith('!') and not found_pdflatex_errors:
            sys.stdout.write("\n")            
            found_pdflatex_errors = True
        if found_pdflatex_errors:
            err_msg = err_msg + line

    if found_pdflatex_errors:
        raise LatexEqError(err_msg)
   
    # converting all pages in pdf doc into png files using gs
    
    call(["gs",
          "-dBATCH", '-q', "-dNOPAUSE",
          "-sDEVICE=pngalpha",
          "-r250",
          "-dTextAlphaBits=4",
          "-dGraphicsAlphaBits=4",
          "-sOutputFile=" + png_base + "%05d.png",
          pdf_filename])

    ##   edit and uncomment this line if we need to look at the generated files
    #    shutil.copyfile(latex_filename, "/path/to/debug/temp.tex")
    
    # converting all png files into base64 strings
    
    for it, eq in enumerate(eq_list,start=1):
        [w, h, data64] = embed_base64(png_base + "%05d.png" % it)
        d = depthratio[it-1]
        d_ = round(d * w * 0.5 , 2)
        w_ = round(w/2)
        h_ = round(h/2)        
        # w_ = round(w/2, 2)
        # h_ = round(h/2, 2)        
        
        if isinstance(eq,MathInline):
            key = "##Inline##" + eq.content           
            html = (
                f"<img src='{data64}'" +
                f" alt='{escape_LaTeX(eq.content)}'" +
                f" width='{w_}' height='{h_}'" +
                f" style='vertical-align:{-d_}px;'>")            
            logging.debug(f"[eq-inline] '{html}'")
            eq_dict[key] = html
        else:
            key = "##Display##" + eq.content
            html = (
                f"<img src='{data64}'" +
                f" alt='{escape_LaTeX(eq.content)}'" +
                f" width='{w_}' height='{h_}'>")
            logging.debug(f"[eq-display] '{html}'")
            eq_dict[key] = html

    os.chdir(olddir)
            
    return eq_dict


def build_eq_dict_SVG(eq_list, opts):
    """returns a dictionary of images from a list of LaTeX equations.
   
    LaTeX equations are compiled into a DVI document using latex,
    with one equation per page.

    The DVI is then converted into SVG images using dvisvgm.

    """
    eq_dict = {}
    
    # if we don't have any equations, exit with empty dict
    if not eq_list:
        return eq_list

    if 'html_pre' in opts:
        template_latex_preamble = opts['html_pre']
    else:
        template_latex_preamble = (
            "\\usepackage{amsmath}\n" +
            "\\usepackage{notomath}\n" +
            "\\usepackage[OT1]{fontenc}\n")

    user_latex_preamble = opts.get('user_pre','')
        
    latex_preamble = (
        "\\documentclass{article}\n" + 
        template_latex_preamble + 
        user_latex_preamble + 
        "\\newenvironment{standalone}{\\begin{preview}}{\\end{preview}}" +
        "\\PassOptionsToPackage{active,tightpage}{preview}" +
        "\\usepackage{preview}" +
        "\\begin{document}\n")

    tmpdir = tempfile.mkdtemp()
    olddir = os.getcwd()
    os.chdir(tmpdir)

    latex_filename = "eq_list.tex"
    dvi_filename = "eq_list.dvi"
    svg_base = "eq_list"

    f = open(latex_filename, 'w')
    f.write(latex_preamble)

    for eq in eq_list:
        if isinstance(eq, MathInline):
            # this code is for the poor's man version with vertical-align: middle 
            f.write("\\typeout{::: 0}")
            f.write("\\sbox{0}{" + eq.content + "}\n")
            f.write("\\ifdim\\dimexpr\\ht0-\\dp0>4.8pt\n")
            f.write("\\dp0\\dimexpr\\ht0-4.8pt\n")
            f.write("\\else\\ht0\\dimexpr\\dp0+4.8pt\\fi\n")
            f.write("\\begin{standalone}\\setlength\\fboxrule{0.00001pt}")
            f.write("\\setlength\\fboxsep{0pt}\\fbox{\\usebox{0}}\\end{standalone}\n")

            
        if isinstance(eq, MathDisplay):
            f.write("\\typeout{::: 0}")            
            f.write("\\begin{standalone}" + eq.content + "\\end{standalone}\n")

    f.write("\\end{document}\n")
    
    f.close()

    console = Console()

    with console.status(f"latex..", spinner="dots") as status:
        command =  ["latex", "-interaction=nonstopmode", latex_filename]
        latexprocess = subprocess.Popen(
            command,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,                
            universal_newlines = True)
        found_latex_errors = False

        # Loop while the subprocess is still running
        while latexprocess.poll() is None:
            status.update(f"...pdflatex")
                
    # Subprocess has finished, get output
    stdout, stderr = latexprocess.communicate()
    return_code = latexprocess.returncode
    
    err_msg = ''
    depthratio = []
    for line in stdout:
        if line.startswith(':::') and not found_latex_errors:
            depthratio.append(float(line[4:-1]))
        if line.startswith('!') and not found_latex_errors:
            sys.stdout.write("\n")            
            found_latex_errors = True
        if found_latex_errors:
            err_msg = err_msg + line

    if found_latex_errors:
        raise LatexEqError(err_msg)                
   
    # converting all pages in pdf doc into png files using gs

    # dvisvgm -n -p 1- -c 1.2,1.2 eq_list.dvi
    call(["dvisvgm",
          "-n",
          '-v', '1',
          '-p', "1-",
          "-c", "1.2,1.2",
          "-o", f"{svg_base}-%5p.svg",          
          dvi_filename])

    ##   edit and uncomment this line if we need to look at the generated files
    #    shutil.copyfile(latex_filename, "/path/to/debug/temp.tex")
    
    # converting all png files into base64 strings

    #####################################################
    # IMPORTANT:
    #
    # In this version we use the dirty depth approach
    # so depth is not recorded but baked in the svg image
    # this is to be able to cope with the limited CSS
    # capabilities of BlackBoard
    #####################################################
    
    for it, eq in enumerate(eq_list,start=1):
        [w, h, data64] = embed_base64(svg_base + "-%05d.svg" % it)
        
        if isinstance(eq,MathInline):
            key = "##Inline##" + eq.content           
            html = (
                f"<img src='{data64}'" +
                f" alt='{escape_LaTeX(eq.content)}'" +
                f" style='vertical-align:middle;'>")            
            logging.debug(f"[eq-inline] '{html}'")
            eq_dict[key] = html
        else:
            key = "##Display##" + eq.content
            html = (
                f"<img src='{data64}'" +
                f" alt='{escape_LaTeX(eq.content)}'" +
                f" style='vertical-align:middle;'>")            
            logging.debug(f"[eq-display] '{html}'")
            eq_dict[key] = html

    os.chdir(olddir)
            
    return eq_dict




def build_eq_dict_MathML(eq_list, opts):
    """returns a dictionary of MATHML eqs from a list of LaTeX equations.
   
    LaTeX equations are compiled into MATHML using make4ht.

    """
    eq_dict = {}
    
    # if we don't have any equations, exit with empty dict
    if not eq_list:
        return eq_list

    if 'html_pre' in opts:
        template_latex_preamble = opts['html_pre']
    else:
        template_latex_preamble = (
            "\\usepackage{amsmath}\n")

    user_latex_preamble = opts.get('user_pre','')
        
    latex_preamble = (
        "\\documentclass{article}\n" + 
        template_latex_preamble + 
        user_latex_preamble + 
        "\\begin{document}\n")

    tmpdir = "." #tempfile.mkdtemp()
    olddir = os.getcwd()
    os.chdir(tmpdir)

    latex_filename = "eq_list.tex"
    out_filename = "eq_list.html"

    f = open(latex_filename, 'w')
    f.write(latex_preamble)

    for eq in eq_list:
        f.write("" + eq.content + "\n")

    f.write("\\end{document}\n")
    
    f.close()
    
    make4ht = subprocess.Popen(
        ["make4ht", "-x",
         latex_filename, "xhtml,html5,mathml"],
        stdout = subprocess.PIPE,
        universal_newlines = True)
    found_make4ht_errors = False

    make4ht_progress =  Spinner("simpleDotsScrolling", "make4ht compilation")

    with Live(make4ht_progress) as live:
        while make4ht.poll()==None:
            make4ht_progress.update()
           
    err_msg = ''
    for line in make4ht.stdout:
        sys.stdout.write(line)            
        
        if line.startswith('[ERROR]') and not found_make4ht_errors:
            sys.stdout.write("\n")            
            found_make4ht_errors = True
        if found_make4ht_errors:
            err_msg = err_msg + line

    if found_make4ht_errors:
        raise LatexEqError(err_msg)

    make4ht_out = Path(out_filename).read_text()

    regex = r"(<math .+?>.*?<\/math>)"
    eq_list_str = re.findall(regex, make4ht_out, re.DOTALL)
    
    # converting all pages in pdf doc into png files using gs
    
    # call(["gs",
    #       "-dBATCH", '-q', "-dNOPAUSE",
    #       "-sDEVICE=pngalpha",
    #       "-r250",
    #       "-dTextAlphaBits=4",
    #       "-dGraphicsAlphaBits=4",
    #       "-sOutputFile=" + png_base + "%05d.png",
    #       pdf_filename])

    # shutil.copyfile(latex_filename, "/Users/fpitie/ttt.tex")   
    # # converting all png files into base64 strings
    
    for it, eq in enumerate(eq_list,start=0):
        
        eq_list_str
        if isinstance(eq,MathInline):
            key = "##Inline##" + eq.content           
            mathml = eq_list_str[it]
            logging.debug(f"[eq-inline] '{mathml}'")
            eq_dict[key] = mathml
        else:
            key = "##Display##" + eq.content
            mathml = eq_list_str[it]
            logging.debug(f"[eq-display] '{mathml}'")
            eq_dict[key] = mathml

    os.chdir(olddir)
            
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
    for code in htmlsrc.findAll(name="code"):
        s = BeautifulSoup(str(code).replace('\n', '<br>'),
                          "html.parser")
        code.replace_with(s)
        
    html_content = str(htmlsrc)

    # now we can delete any spurious '\n' or '\t'
    
    html_content = html_content.replace('\n', ' ').replace('\t', '  ')

    return html_content   


def escape_LaTeX(str_eq):
    """HTML escape the LaTeX string defining an equation. This is to
    be used in the `alt` tag of the corresponding rendered image

    It applies the following transformations:    
    * convert main $ and $$ sign to \( and \[
    * convert other $ into &dollar;
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
    
    

class BBYamlHTMLRenderer(HTMLRenderer):
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
        

    with BBYamlHTMLRenderer(eq_dict) as renderer:
        html_result = renderer.render(doc)

    return html_result


def inline_css(html_content, opts):

    if 'html_css' in opts:
        css = opts['html_css']
        # remove all comments (/*COMMENT */) from string
        css = re.sub(re.compile("/\*.*?\*/",re.DOTALL ) ,"" , css)        
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
    

