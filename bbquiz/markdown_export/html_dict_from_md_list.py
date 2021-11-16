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

import json
import struct

import argparse

from subprocess import call
import tempfile
import base64
from collections import defaultdict
import logging
    

def get_md_list_from_yaml(yaml_data, md_list=None):
    """
    List all Markdown entries in the yaml file.

    Parameters
    ----------
    yaml_data : list  
        yaml file content, as decoded by bbyaml.load
    md_list : list
        output list of markdown entries
    """
    if md_list is None:
        md_list = []
        
    non_md_keys = ['type']
    for i in yaml_data:
        for key, val in i.items():
            if isinstance(val, list):
                md_list = get_md_list_from_yaml(val, md_list)
            elif isinstance(val, str) and key not in non_md_keys:
                if val not in md_list:
                    md_list.append(val)
    return md_list


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
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    result = proc.communicate(input=bytes(md_content, 'utf-8'))[0]
    return json.loads(result)

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

        regex = r"([\n]*)([ ]*<[/]?[a-zA-Z \'=\"]+>[ ]*)([\n]*)"
        subst = "\\2"
        html_content = re.sub(regex, subst, html_content, 0, re.MULTILINE)
        html_content = html_content.replace('\n', '<br>').replace(
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
    cmd = [ 'pandoc', '-f', 'json', '-t', 'html', '--self-contained',
            '--metadata', 'title="temp"']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    
    result = proc.communicate(input=bytes(json.dumps(json_data), 'utf-8'))[0]
    return result.decode('utf-8')

def convert_latex_eqs(data_json):

    eq_list = get_eq_list_from_json(data_json)
    
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

    print("compiling the equations using pdflatex...")

#    call(["pdflatex", latex_filename], stdout=sys.stderr)
    pdflatex = subprocess.Popen(["pdflatex", latex_filename],
                                stdout = subprocess.PIPE,
                                universal_newlines = True)
    latex_verb = False
    for line in pdflatex.stdout:
        if line.startswith('!') and not latex_verb:
            sys.stdout.write('\033[91m' + "╭" + "pdflatex Error".center(81, "─") + "╮" + '\033[0m\n')
            latex_verb = True
        if latex_verb:
            sys.stdout.write('\033[91m' + "│ " + '\033[0m' +  line[:-1].ljust(79) + '\033[91m' + " │" + '\033[0m\n')

    if latex_verb:
        sys.stdout.write('\033[91m' + "╰" + "─"*81 + "╯" + '\033[0m\n')           

    call(["gs", "-dBATCH", '-q', "-dNOPAUSE", "-sDEVICE=pngalpha", "-r250",
          "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
          "-sOutputFile=" + png_base + "%05d.png", pdf_filename])

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
    
    md_list = get_md_list_from_yaml(yaml_data)

    md_combined = md_combine_list(md_list)

    data_json = pandoc_md_to_json(md_combined)

    data_json = convert_latex_eqs(data_json)
    
    html_result = pandoc_json_to_sefcontained_html(data_json)
    
    md_dict = get_html_dict_from_md_list(html_result, md_list)

    return md_dict




