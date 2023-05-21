#!/usr/bin/python
import subprocess
import os
import sys
import uuid
import yaml
import markdown
import re
import html
import hashlib

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


from ..utils import *
from ..bbyaml.utils import get_md_list_from_yaml

class PandocError(Exception):
    pass

class LatexError(Exception):
    pass


def get_hash(txt):
    return hashlib.md5(txt.encode('utf-8')).hexdigest()
 
def md_combine_list(md_list):
    """
    Collate all Markdown entries into a single Markdown document.

    Parameters
    ----------
    md_list : list  
        list of markdown entries
    """

    txt = ""
    for md_entry in md_list:
        txt = txt + "\n\n# " + get_hash(md_entry) + "\n\n" + md_entry
    return txt

def append_unique(alist, blist):
    for b in blist:
        if b not in alist:
            alist.append(b)
    return alist

def get_eq_list_from_json(json_data):
    eq_list = []
    if isinstance(json_data, dict):
        for key, val in json_data.items():
            if key == 't' and val == 'Math':
                append_unique(eq_list, [json_data["c"]])
            if isinstance(val, list):
                for i in val:
                    eq_list = append_unique(eq_list, get_eq_list_from_json(i))
    if isinstance(json_data, list):
        for i in json_data:
            eq_list = append_unique(eq_list, get_eq_list_from_json(i))
                    
    return eq_list


def replace_eq_with_image(c, eq_dict):
    [w, h, base64] = eq_dict[c[0]['t'] + c[1]]
    return {
        "t":
            "Image",
        "c": [[
            "", ["math", "inline"],
            [["width", str(w / 2)], ["height", str(h / 2)]]
        ], [], [base64, c[1]]]
    }

def parse_json_replace_maths(json_data, eq_dict):
    if isinstance(json_data, dict):
        for key, val in json_data.items():
            if key == 't' and val == 'Math':
                return replace_eq_with_image(json_data["c"], eq_dict)
            if isinstance(val, list):
                new_val = []
                for i in val:
                    new_val.append(parse_json_replace_maths(i, eq_dict))
                json_data[key] = new_val
    if isinstance(json_data, list):
        new_json_data = []
        for i in json_data:
            new_json_data.append(parse_json_replace_maths(i, eq_dict))
        json_data = new_json_data
    return json_data

def get_image_info(data):
    w, h = struct.unpack('>LL', data[16:24])
    width = int(w)
    height = int(h)
    return width, height

def png_file_to_base64(pngfile):
    with open(pngfile, "rb") as image_file:
        data = image_file.read()
        [w, h] = get_image_info(data)
        data64 = "data:image/png;base64," + \
            base64.b64encode(data).decode('ascii')
    return (w, h, data64)

def pandoc_md_to_json(md_content):
    cmd = ['pandoc', '-f', 'markdown', '-t', 'json']
    proc = subprocess.Popen(cmd,
                            stdout = subprocess.PIPE,
                            stdin  = subprocess.PIPE,
                            stderr = subprocess.PIPE)

    stdout, stderr = proc.communicate(input=bytes(md_content, 'utf-8'))

    if (stderr):
        print_box("Pandoc Error", stderr.decode('utf-8'), Fore.RED)               
        raise PandocError
    
    return json.loads(stdout)



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
    
    html_content = html_content.replace('\n', '').replace('\t', '  ')

    return html_content
    

def get_html_dict_from_md_list(html_result, md_list):
    md_dict = {}
    i = 0
    for txt in md_list:
        i = i + 1
        h = get_hash(txt)
        html_h1 = h + "</h1>"
        start = html_result.find(html_h1) + len(html_h1)
        end = html_result.find("<h1 id", start + 1)
        html_content = html_result[start:end]

        html_content = remove_newline_and_tabs(html_content)
        
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

def pandoc_json_to_sefcontained_html(json_data):
    cmd = [ 'pandoc', '-f', 'json', '-t', 'html', '--wrap=none',
            '--embed-resources', '--standalone',
            '--metadata', 'title="temp"']
    pandoc = subprocess.Popen(cmd,
                              stdout = subprocess.PIPE,
                              stdin  = subprocess.PIPE,
                              stderr = subprocess.PIPE)
    stdout, stderr = pandoc.communicate(input=bytes(json.dumps(json_data), 'utf-8'))

    if (stderr):
        results_fmt = "\nerror while using pandoc to generate self-contained html:\n\n" \
            +  stderr.decode('utf-8')
        print_box("Pandoc Error", results_fmt, Fore.RED)
        raise PandocError

    return stdout.decode('utf-8')

def spinning_cursor():
    """Spinner taken from http://stackoverflow.com/questions/4995733/how-to-create-a-spinning-command-line-cursor-using-python/4995896#4995896."""

    while True:
        for cursor in '|/-\\':
             yield cursor

             
def convert_latex_eqs(data_json):
# Converts all equations in the pandoc json into PNGs using pdflatex and gs
    
    eq_list = get_eq_list_from_json(data_json)

    # if we don't have any equations, exit
    if not eq_list:
        return data_json
    
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
        if eq[0]['t'] == 'InlineMath':
            f.write("\\begin{mymath2}" + eq[1] + "\\end{mymath2}\n")
        if eq[0]['t'] == 'DisplayMath':
            f.write("\\begin{mymath1}" + eq[1] + "\\end{mymath1}\n")

    f.write("\\end{document}\n")
    f.close()

#    sys.stdout.write("compiling the equations using pdflatex...")

    pdflatex = subprocess.Popen(["pdflatex", "-interaction=nonstopmode", latex_filename],
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
    
    it = 0
    eq_dict = {}
    for eq in eq_list:
        it = it + 1
        [w, h, data64] = png_file_to_base64(png_base + "%05d.png" % it)
        eq_dict[eq[0]['t'] + eq[1]] = (w, h, data64)

    os.chdir(olddir)

    json_out = parse_json_replace_maths(data_json, eq_dict)
    
    return json_out




def convert_latex_eqs_old(data_json):
# Converts all equations in the pandoc json into PNGs using pdflatex and gs
    
    eq_list = get_eq_list_from_json(data_json)

    # if we don't have any equations, exit
    if not eq_list:
        return data_json
    
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
        if eq[0]['t'] == 'InlineMath':
            f.write("\\begin{mymath2}" + eq[1] + "\\end{mymath2}\n")
        if eq[0]['t'] == 'DisplayMath':
            f.write("\\begin{mymath1}" + eq[1] + "\\end{mymath1}\n")

    f.write("\\end{document}\n")
    f.close()

    sys.stdout.write("compiling the equations using pdflatex...")

    pdflatex = subprocess.Popen(["pdflatex", "-interaction=nonstopmode", latex_filename],
                                stdout = subprocess.PIPE,
                                universal_newlines = True)
    found_pdflatex_errors = False

    spinner = spinning_cursor()
    
    while pdflatex.poll()==None:
        # Print spinner
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        sys.stdout.write('\b')

        
    # I would need to improve this by making print_box compatible with _io.TextIOWrapper
    
    for line in pdflatex.stdout:
        if line.startswith('!') and not found_pdflatex_errors:
            w, _ = os.get_terminal_size(0)

            sys.stdout.write(Fore.RED + "╭"
                             + "pdflatex Error".center(w - 2, "─")
                             + "╮" + '\033[0m\n')
            found_pdflatex_errors = True
        if found_pdflatex_errors:
            sys.stdout.write(Fore.RED + "│ " + '\033[0m'
                             +  line[:-1].ljust(w - 4)
                             + '\033[91m' + " │" + '\033[0m\n')

    if found_pdflatex_errors:
        sys.stdout.write(Fore.RED + "╰" + "─"*(w-2) + "╯" + '\033[0m\n')
        raise LatexError

    sys.stdout.write(" done\n")

    
    # converting all pages in pdf doc into png files using gs
    
    call(["gs", "-dBATCH", '-q', "-dNOPAUSE", "-sDEVICE=pngalpha", "-r250",
          "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
          "-sOutputFile=" + png_base + "%05d.png", pdf_filename])

    # converting all png files into base64 strings
    
    it = 0
    eq_dict = {}
    for eq in eq_list:
        it = it + 1
        [w, h, data64] = png_file_to_base64(png_base + "%05d.png" % it)
        eq_dict[eq[0]['t'] + eq[1]] = (w, h, data64)

    os.chdir(olddir)

    json_out = parse_json_replace_maths(data_json, eq_dict)
    
    return json_out


def get_html_md_dict_from_yaml(yaml_data):
    
    md_list     = get_md_list_from_yaml(yaml_data)
    md_combined = md_combine_list(md_list)
    data_json   = pandoc_md_to_json(md_combined)
    
    
    for eq in eq_list:
        if eq[0]['t'] == 'InlineMath':
            f.write("\\begin{mymath2}" + eq[1] + "\\end{mymath2}\n")
        if eq[0]['t'] == 'DisplayMath':
            f.write("\\begin{mymath1}" + eq[1] + "\\end{mymath1}\n")

    f.write("\\end{document}\n")
    f.close()

    sys.stdout.write("compiling the equations using pdflatex...")

    pdflatex = subprocess.Popen(["pdflatex", "-interaction=nonstopmode", latex_filename],
                                stdout = subprocess.PIPE,
                                universal_newlines = True)
    found_pdflatex_errors = False

    spinner = spinning_cursor()
    
    while pdflatex.poll()==None:
        # Print spinner
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        sys.stdout.write('\b')
        
    # I would need to improve this by making print_box compatible with _io.TextIOWrapper
    
    for line in pdflatex.stdout:
        if line.startswith('!') and not found_pdflatex_errors:
            w, _ = os.get_terminal_size(0)

            sys.stdout.write(Fore.RED + "╭"
                             + "pdflatex Error".center(w - 2, "─")
                             + "╮" + '\033[0m\n')
            found_pdflatex_errors = True
        if found_pdflatex_errors:
            sys.stdout.write(Fore.RED + "│ " + '\033[0m'
                             +  line[:-1].ljust(w - 4)
                             + '\033[91m' + " │" + '\033[0m\n')

    if found_pdflatex_errors:
        sys.stdout.write(Fore.RED + "╰" + "─"*(w-2) + "╯" + '\033[0m\n')
        raise LatexError

    sys.stdout.write(" done\n")

    
    # converting all pages in pdf doc into png files using gs
    
    call(["gs", "-dBATCH", '-q', "-dNOPAUSE", "-sDEVICE=pngalpha", "-r250",
          "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
          "-sOutputFile=" + png_base + "%05d.png", pdf_filename])

    # converting all png files into base64 strings
    
    it = 0
    eq_dict = {}
    for eq in eq_list:
        it = it + 1
        [w, h, data64] = png_file_to_base64(png_base + "%05d.png" % it)
        eq_dict[eq[0]['t'] + eq[1]] = (w, h, data64)

    os.chdir(olddir)

    json_out = parse_json_replace_maths(data_json, eq_dict)
    
    return json_out


def get_html_md_dict_from_yaml(yaml_data):
    
    md_list     = get_md_list_from_yaml(yaml_data)
    md_combined = md_combine_list(md_list)
    data_json   = pandoc_md_to_json(md_combined)
    
    for eq in eq_list:
        if eq[0]['t'] == 'InlineMath':
            f.write("\\begin{mymath2}" + eq[1] + "\\end{mymath2}\n")
        if eq[0]['t'] == 'DisplayMath':
            f.write("\\begin{mymath1}" + eq[1] + "\\end{mymath1}\n")

    f.write("\\end{document}\n")
    f.close()

    sys.stdout.write("compiling the equations using pdflatex...")

    pdflatex = subprocess.Popen(["pdflatex", "-interaction=nonstopmode", latex_filename],
                                stdout = subprocess.PIPE,
                                universal_newlines = True)
    found_pdflatex_errors = False

    spinner = spinning_cursor()
    
    while pdflatex.poll()==None:
        # Print spinner
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        sys.stdout.write('\b')
        
    # I would need to improve this by making print_box compatible with _io.TextIOWrapper
    
    for line in pdflatex.stdout:
        if line.startswith('!') and not found_pdflatex_errors:
            w, _ = os.get_terminal_size(0)

            sys.stdout.write(Fore.RED + "╭"
                             + "pdflatex Error".center(w - 2, "─")
                             + "╮" + '\033[0m\n')
            found_pdflatex_errors = True
        if found_pdflatex_errors:
            sys.stdout.write(Fore.RED + "│ " + '\033[0m'
                             +  line[:-1].ljust(w - 4)
                             + '\033[91m' + " │" + '\033[0m\n')

    if found_pdflatex_errors:
        sys.stdout.write(Fore.RED + "╰" + "─"*(w-2) + "╯" + '\033[0m\n')
        raise LatexError

    sys.stdout.write(" done\n")

    
    # converting all pages in pdf doc into png files using gs
    
    call(["gs", "-dBATCH", '-q', "-dNOPAUSE", "-sDEVICE=pngalpha", "-r250",
          "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
          "-sOutputFile=" + png_base + "%05d.png", pdf_filename])

    # converting all png files into base64 strings
    
    it = 0
    eq_dict = {}
    for eq in eq_list:
        it = it + 1
        [w, h, data64] = png_file_to_base64(png_base + "%05d.png" % it)
        eq_dict[eq[0]['t'] + eq[1]] = (w, h, data64)

    os.chdir(olddir)

    json_out = parse_json_replace_maths(data_json, eq_dict)
    
    return json_out


def get_html_md_dict_from_yaml(yaml_data):
    
    md_list     = get_md_list_from_yaml(yaml_data)
    md_combined = md_combine_list(md_list)
    data_json   = pandoc_md_to_json(md_combined)
    
    for eq in eq_list:
        if eq[0]['t'] == 'InlineMath':
            f.write("\\begin{mymath2}" + eq[1] + "\\end{mymath2}\n")
        if eq[0]['t'] == 'DisplayMath':
            f.write("\\begin{mymath1}" + eq[1] + "\\end{mymath1}\n")

    f.write("\\end{document}\n")
    f.close()

    sys.stdout.write("compiling the equations using pdflatex...")

    pdflatex = subprocess.Popen(["pdflatex", "-interaction=nonstopmode", latex_filename],
                                stdout = subprocess.PIPE,
                                universal_newlines = True)
    found_pdflatex_errors = False

    spinner = spinning_cursor()
    
    while pdflatex.poll()==None:
        # Print spinner
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        sys.stdout.write('\b')
        
    # I would need to improve this by making print_box compatible with _io.TextIOWrapper
    
    for line in pdflatex.stdout:
        if line.startswith('!') and not found_pdflatex_errors:
            w, _ = os.get_terminal_size(0)

            sys.stdout.write(Fore.RED + "╭"
                             + "pdflatex Error".center(w - 2, "─")
                             + "╮" + '\033[0m\n')
            found_pdflatex_errors = True
        if found_pdflatex_errors:
            sys.stdout.write(Fore.RED + "│ " + '\033[0m'
                             +  line[:-1].ljust(w - 4)
                             + '\033[91m' + " │" + '\033[0m\n')

    if found_pdflatex_errors:
        sys.stdout.write(Fore.RED + "╰" + "─"*(w-2) + "╯" + '\033[0m\n')
        raise LatexError

    sys.stdout.write(" done\n")

    
    # converting all pages in pdf doc into png files using gs
    
    call(["gs", "-dBATCH", '-q', "-dNOPAUSE", "-sDEVICE=pngalpha", "-r250",
          "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
          "-sOutputFile=" + png_base + "%05d.png", pdf_filename])

    # converting all png files into base64 strings
    
    it = 0
    eq_dict = {}
    for eq in eq_list:
        it = it + 1
        [w, h, data64] = png_file_to_base64(png_base + "%05d.png" % it)
        eq_dict[eq[0]['t'] + eq[1]] = (w, h, data64)

    os.chdir(olddir)

    json_out = parse_json_replace_maths(data_json, eq_dict)
    
    return json_out


def get_html_md_dict_from_yaml(yaml_data):
    
    md_list     = get_md_list_from_yaml(yaml_data)
    md_combined = md_combine_list(md_list)

    # with open("bbquiz-mdcombine.md", "w") as f:
    #     f.write(md_combined)        
    
    data_json   = pandoc_md_to_json(md_combined)

    # with open("bbquiz-md.json", "w") as f:
    #     f.write(str(data_json))

    # print(data_json)
    
    data_json   = convert_latex_eqs(data_json)

    # print(data_json)
    
    html_result = pandoc_json_to_sefcontained_html(data_json)

    # print(html_result)
    
    # with open("bbquiz-out.html", "w") as f:
    #     f.write(html_result)    
    
    md_dict     = get_html_dict_from_md_list(html_result, md_list)

    return md_dict




