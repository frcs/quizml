#!/usr/bin/python
import subprocess
import os
import sys
import uuid
import yaml
import markdown
import re
import html

from bs4 import BeautifulSoup

import json
import struct

import argparse

# import colorama

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

from .utils import *
from ..utils import *
from ..bbyaml.utils import get_md_list_from_yaml

class PandocError(Exception):
    pass

class LatexError(Exception):
    pass


import mistletoe
from mistletoe import Document, HTMLRenderer
from mistletoe.ast_renderer import ASTRenderer
from mistletoe.latex_token import Math
from mistletoe import span_token
from mistletoe.span_token import Image
from mistletoe.span_token import tokenize_inner
from mistletoe.span_token import SpanToken


class MathInline(SpanToken):
    content = ''
    parse_group = 1
    parse_inner = False
#    precedence = 6    
    pattern = re.compile(r"""
	(?<!\\)    # negative look-behind to make sure start is not escaped 
	(?:        # start non-capture group for all possible match starts
	  # group 1, match dollar signs only 
	  # single or double dollar sign enforced by look-arounds
	  ((?<!\$)\${1}(?!\$))|
	  # group 2, match escaped parenthesis
	  (\\\()
	)
	# if group 1 was start
	(?(1)
	  # non greedy match everything in between
	  # group 1 matches do not support recursion
	  (.*?)(?<!\\)
	  # match ending double or single dollar signs
	  (?<!\$)\1(?!\$)|  
	# else
	(?:
	  # greedily and recursively match everything in between
	  # groups 2, 3 and 4 support recursion
	  (.*)(?<!\\)\\\)
	))
	""", re.MULTILINE | re.VERBOSE | re.DOTALL)
    def __init__(self, match):
        if match.group(3):
            self.content = match.group(3)
        else:
            self.content = match.group(4)


class MathDisplay(SpanToken):
    content = ''
    parse_group = 1
    parse_inner = False
#    precedence = 6    
    pattern = re.compile(r"""
	(?<!\\)    # negative look-behind to make sure start is not escaped 
	(?:        # start non-capture group for all possible match starts
	  # group 1, match dollar signs only 
	  # single or double dollar sign enforced by look-arounds
	  ((?<!\$)\${2}(?!\$))|
	  # group 2, match escaped bracket
	  (\\\[)|                 
	  # group 3, match begin equation
	  (\\begin\{equation\})
	)
	# if group 1 was start
	(?(1)
	  # non greedy match everything in between
	  # group 1 matches do not support recursion
	  (.*?)(?<!\\)
	  # match ending double or single dollar signs
	  (?<!\$)\1(?!\$)|  
	# else
	(?:
	  # greedily and recursively match everything in between
	  # groups 2, 3 and 4 support recursion
	  (.*)(?<!\\)
	  (?:
	    # if group 2 was start, escaped bracket is end
	    (?(2)\\\]|     
	    # else group 3 was start, match end equation
	    (?(3)\\end\{equation\})
            ))))
	""", re.MULTILINE | re.VERBOSE | re.DOTALL)
    def __init__(self, match):
        if match.group(4):
            self.content = match.group(4)
        else:
            self.content = match.group(5)


def embed_base64(path):
    filename, ext = os.path.splitext(path)
    ext = ext[1:]
    if ext=='svg':
        ext = 'svg+xml'
    print(ext)
    with open(path, "rb") as image_file:
        data = image_file.read()
        [w, h] = get_image_info(data)
        data64 = f"data:image/{ext};base64," + \
            base64.b64encode(data).decode('ascii')
    return (w, h, data64)


def get_eq_list_from_doc(doc):
    eq_list = []
    if hasattr(doc, 'children'):
        for a in doc.children:
            eq_list = append_unique(eq_list, get_eq_list_from_doc(a))
    elif isinstance(doc, MathInline) or isinstance(doc, MathDisplay):
        eq_list.append(doc)
    return eq_list


def print_doc(doc):
    print(doc)
    if hasattr(doc, 'children'):
        for a in doc.children:
            print_doc(a)
    

def get_eq_dict(doc):
# Converts all equations in the pandoc json into PNGs using pdflatex and gs

    eq_dict = {}
    
    eq_list = get_eq_list_from_doc(doc)

    # if we don't have any equations, exit with empty dict
    if not eq_list:
        return eq_list
    
    latex_preamble = \
        "\\documentclass[multi={mymath1,mymath2},border=1pt]{standalone}\n" + \
        "\\usepackage{amsmath}\n"+ \
        "\\newenvironment{mymath1}{$\displaystyle}{$}\n" +\
        "\\newenvironment{mymath2}{$}{$}\n" +\
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
            f.write("\\begin{mymath2}" + eq.content + "\\end{mymath2}\n")
        if isinstance(eq, MathDisplay):
            f.write("\\begin{mymath1}" + eq.content + "\\end{mymath1}\n")

    f.write("\\end{document}\n")
    f.close()

    pdflatex = subprocess.Popen(
        ["pdflatex", "-interaction=nonstopmode",
         latex_filename],
        stdout = subprocess.PIPE,
        universal_newlines = True)
    found_pdflatex_errors = False


    pdflatex_progress =  Spinner("dots", "pdflatex compilation")

    with Live(pdflatex_progress) as live:
        while pdflatex.poll()==None:
            pdflatex_progress.update()
    
    err_msg = ''
    for line in pdflatex.stdout:
        if line.startswith('!') and not found_pdflatex_errors:
            sys.stdout.write("\n")            
            found_pdflatex_errors = True
        if found_pdflatex_errors:
            err_msg = err_msg + line

    if found_pdflatex_errors:
        print(Panel(err_msg, title="Latex Error",border_style="red"))
        raise LatexError
   
    # converting all pages in pdf doc into png files using gs
    
    call(["gs", "-dBATCH", '-q', "-dNOPAUSE", "-sDEVICE=pngalpha", "-r250",
          "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
          "-sOutputFile=" + png_base + "%05d.png", pdf_filename])

    # converting all png files into base64 strings
    
    for it, eq in enumerate(eq_list,start=1):
        [w, h, data64] = embed_base64(png_base + "%05d.png" % it)

        if isinstance(eq,MathInline):
            key = "##Inline##" + eq.content
        else:
            key = "##Display##" + eq.content

        eq_dict[key] = (w, h, data64)

    os.chdir(olddir)
    
    return eq_dict


def remove_newline_and_tabs(html_content):
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


def capture_width_in_img_tags(html_content):
    """
    Problem: we can allow for width parameters to passed to image:
    ![a pic](fig/pic.jpeg){width=40em}
    so we need to capture the width 
    """

    #    <p><img alt="" src="figures/rd-multires.png"/>{width=30em}</p>
    regex = r"<p><img\s*alt=\"(.*)\"\s*src=\"(.*)\"\s*[/]?>{\s*width\s*=\s*(.*)}\s*</p>"
    subst = "<p><img alt=\"\\1\" src=\"\\2\" style=\"width:\\3\"></p>"
    result = re.sub(regex, subst, html_content, 0, re.MULTILINE | re.DOTALL)  
    return result


def get_html_dict_from_md_list(html_result, md_list):
    md_dict = {}
    for i, txt in enumerate(md_list, start=1):
        h = get_hash(txt)
        html_h1 = "<h1>" + h + "</h1>"
        start = html_result.find(html_h1) + len(html_h1)
        end = html_result.find("<h1>", start + 1)
        html_content = html_result[start:end]
        html_content = remove_newline_and_tabs(html_content)
        html_content = capture_width_in_img_tags(html_content)       
        # in the future, this styling should be done outside
        html_content = html_content.replace(
            'class="math inline"',
            'class="math inline" style="vertical-align:middle"')
        html_content = html_content.replace(
            '<code>',
            '<code style="font-family:\'Courier New\'">')
        html_content = html_content.replace(
            '<pre>',
            '<pre style="background:#eee; padding: 1em; max-width: 80em;">')
        md_dict[txt] = html_content
    return md_dict

class MathRenderer(HTMLRenderer):
    def __init__(self, eq_dict):
        super().__init__(MathInline,MathDisplay)
        self.eq_dict = eq_dict
    def render_math_inline(self, token):
        [w, h, data64] = self.eq_dict['##Inline##' + token.content]
        return f"<img src='{data64}' alt='{token.content}' width='{w/2}' height='{h/2}' style='vertical-align:middle;'>"
    def render_math_display(self, token):
        [w, h, data64] = self.eq_dict['##Display##' + token.content]
        return f"<img src='{data64}' alt='{token.content}' width='{w/2}' height='{h/2}'>"
    def render_image(self, token: span_token.Image) -> str:       
        template = '<img src="{}" alt="{}"{} />'
        if token.title:
            title = ' title="{}"'.format(html.escape(token.title))
        else:
            title = ''
        [w, h, data64] = embed_base64(token.src)            
        return template.format(data64, self.render_to_plain(token), title)
    

def get_html_md_dict_from_yaml(yaml_data):
    
    md_list     = get_md_list_from_yaml(yaml_data)
    md_combined = md_combine_list(md_list)

    # with open("bbquiz-mdcombine.md", "w") as f:
    #     f.write(md_combined)        

    with ASTRenderer(MathInline,MathDisplay) as renderer:
        doc = Document(md_combined)

    eq_dict = get_eq_dict(doc)

    with MathRenderer(eq_dict) as renderer:
        html_result = renderer.render(doc)
       
    md_dict  = get_html_dict_from_md_list(html_result, md_list)

    return md_dict




