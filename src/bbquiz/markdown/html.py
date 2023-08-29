import subprocess
import os
import sys
import yaml
import html

from bs4 import BeautifulSoup

from subprocess import call
import tempfile
import base64
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

from .utils import append_unique, get_image_info, get_hash
from .extensions import MathInline, MathDisplay, ImageWithWidth
from .exceptions import LatexEqError

from mistletoe import span_token


def embed_base64(path):
    """
    returns a base64 string of an image file.
    """
    
    filename, ext = os.path.splitext(path)
    ext = ext[1:]
    if ext=='svg':
        ext = 'svg+xml'
    with open(path, "rb") as image_file:
        data = image_file.read()
        [w, h] = get_image_info(data)
        data64 = f"data:image/{ext};base64," + \
            base64.b64encode(data).decode('ascii')
    return (w, h, data64)


def get_eq_list_from_doc(doc):
    """
    returns a list of all the LaTeX equations (as mistletoe objects) in a mardown document (mistletoe object).    
    """

    eq_list = []
    if hasattr(doc, 'children'):
        for a in doc.children:
            eq_list = append_unique(eq_list, get_eq_list_from_doc(a))
    elif isinstance(doc, MathInline) or isinstance(doc, MathDisplay):
        eq_list.append(doc)
    return eq_list
   

def get_eq_dict(eq_list):
    """
    returns a dictionary of images from a list of LaTeX equations.
   
    LaTeX equations are compiled into a PDF document using pdflatex,
    with one equation per page.

    The PDF is then converted into PNG images using ghostscript (gs).
    
    """
    
    eq_dict = {}
    
    # if we don't have any equations, exit with empty dict
    if not eq_list:
        return eq_list
    
    latex_preamble = \
        "\\documentclass{article}\n" + \
        "\\usepackage{amsmath}\n"+ \
        "\\newenvironment{standalone}{\\begin{preview}}{\\end{preview}}"+\
        "\\PassOptionsToPackage{active,tightpage}{preview}"+\
        "\\usepackage{preview}"+\
        "\\begin{document}\n"

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
            f.write("\\setbox0=\\hbox{" + eq.content + "}\n")
            f.write("\\makeatletter\\typeout{::: \\strip@pt\\dimexpr 1pt * \\dp0 / \\wd0\\relax}\\makeatother")
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


    pdflatex_progress =  Spinner("simpleDotsScrolling", "pdflatex compilation")

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
    
    call(["gs", "-dBATCH", '-q', "-dNOPAUSE", "-sDEVICE=pngalpha", "-r250",
          "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
          "-sOutputFile=" + png_base + "%05d.png", pdf_filename])

    # converting all png files into base64 strings
    
    for it, eq in enumerate(eq_list,start=1):
        [w, h, data64] = embed_base64(png_base + "%05d.png" % it)
        d = depthratio[it-1]
        if isinstance(eq,MathInline):
            key = "##Inline##" + eq.content
        else:
            key = "##Display##" + eq.content

        eq_dict[key] = (w, h, d, data64)

    os.chdir(olddir)
    
    return eq_dict

def strip_newlines_and_tabs(html_content):
    """
    Problem: we need to remove any tab or any newline 
    from the string as it must be passed as a CSV entry
    for blackboard exams.

    replace \n with <br> inside <code> </code> blocks so as
    preserve formatting inside these verbatim blocks
    """
    
    htmlsrc = BeautifulSoup(html_content, "html.parser")
    for code in htmlsrc.findAll(name="code"):
        s = BeautifulSoup(str(code).replace('\n', '<br>'),
                          "html.parser")
        code.replace_with(s)
        
    html_content = str(htmlsrc)

    # now we can delete any spurious \n or \t
    
    html_content = html_content.replace('\n', ' ').replace('\t', '  ')

    return html_content   

class BBYamlHTMLRenderer(HTMLRenderer):
    """
    customised mistletoe renderer for HTML
    implements render for custom spans MathInline, MathDisplay, ImageWithWidth
    also reimplements Image to embbed the image as base64
    """
    
    def __init__(self, eq_dict):
        super().__init__(MathInline,MathDisplay,ImageWithWidth)
        self.eq_dict = eq_dict
        
    def render_math_inline(self, token):
        [w, h, dr, data64] = self.eq_dict['##Inline##' + token.content]
        d_ = round(dr * w * 0.5 , 2)
        w_ = round(w/2, 2)
        h_ = round(h/2, 2)        
        return f"<img src='{data64}' alt='{token.content}' width='{w_}' height='{h_}' style='vertical-align:{-d_}px;'>"
    
    def render_math_display(self, token):
        [w, h, d, data64] = self.eq_dict['##Display##' + token.content]
        return f"<img src='{data64}' alt='{token.content}' width='{int(w/2):d}' height='{int(h/2):d}'>"
    
    def render_image(self, token: span_token.Image) -> str:       
        template = '<img src="{}" alt="{}"{} />'
        if token.title:
            title = ' title="{}"'.format(html.escape(token.title))
        else:
            title = ''
        [w, h, data64] = embed_base64(token.src)            
        return template.format(data64, self.render_to_plain(token), title)
    
    def render_image_with_width(self, token) -> str:
        template = '<img src="{}" alt="{}"{} style="width:{}"/>'
        if token.title:
            title = ' title="{}"'.format(html.escape(token.title))
        else:
            title = ''
        [w, h, data64] = embed_base64(token.src)
        return template.format(data64,
                               self.render_to_plain(token),
                               title,
                               token.width)
    

def get_html(doc):
    """
    returns the rendered HTML source for mistletoe object
    """

    eq_list = get_eq_list_from_doc(doc)
    eq_dict = get_eq_dict(eq_list)

    with BBYamlHTMLRenderer(eq_dict) as renderer:
        html_result = renderer.render(doc)

    return html_result

def get_html_dict(combined_doc, md_list):
    """
    md_list: a list of markdown entries
    combined_doc: the mistletoe object for the collation of all these entries
    
    renders the HTML source of a collation of mardown entries
    and build a dictionary of these renders.
    """
   
    html_result = get_html(combined_doc)
    
    md_dict = {}
    for i, txt in enumerate(md_list, start=1):
        h = get_hash(txt)
        html_h1 = "<h1>" + h + "</h1>"
        start = html_result.find(html_h1) + len(html_h1)
        end = html_result.find("<h1>", start + 1)
        if end == -1:
            end = len(html_result)
            
        html_content = html_result[start:end]
        html_content = strip_newlines_and_tabs(html_content)
        html_content = html_content.replace(
            'class="math inline"',
            'class="math inline" style="vertical-align:middle"')
        html_content = html_content.replace(
            '<code>',
            '<code style="font-family:\'Courier New\'; font-size:80%">')
        html_content = html_content.replace(
            '<pre>',
            '<pre style="background:#eee; padding: 1em; max-width: 80em;">')
        md_dict[txt] = html_content
    return md_dict
    

        
