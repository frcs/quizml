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

from ..utils import *
from ..bbyaml.utils import get_md_list_from_yaml

import mistletoe
from mistletoe.latex_renderer import LaTeXRenderer
    
                 
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


def mistletoe_md_to_latex(md_content):
    """
    using mistletoe to convert markdown to LaTeX
    """

    rendered = mistletoe.markdown(md_content, LaTeXRenderer)

    # cmd = ['pandoc', '-f', 'markdown',
    #        '-t', 'latex', '--listings']
    # proc = subprocess.Popen(cmd,
    #                         stdout=subprocess.PIPE,
    #                         stdin=subprocess.PIPE)

    # result = proc.communicate(input=bytes(md_content, 'utf-8'))[0]
    
    return rendered


def get_latex_dict_from_md_list_mistletoe(latex_result, md_list):
    """
    For each text entry in md_list,
    find section with title as hash(text) in latex document,
    and use content of section (till next hypertarget tag) as latex value
    """
    md_dict = {}


    # this pattern is to remove {width=30em} after includegraphics
    # I'm in two minds about how to deal wit hthis leagcy pandoc feature
    # maybe I should remove this
    regex = r"\\includegraphics{(.*)}\n\\{.*\}"
    subst = "\\\\includegraphics{\\1}"

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
        # svg support doesn't work in latex at the moment... so defaulting to pdf
        latex_content = latex_content.replace('.svg}', '.pdf}')
        latex_content = latex_content.replace('\includesvg', '\includegraphics')

        latex_content = re.sub(regex, subst, latex_content, 0, re.MULTILINE)
        
        latex_content = latex_content.replace(',height=\\textheight', '')
        latex_content = latex_content.replace('\\passthrough', '')
        md_dict[txt] = latex_content

    return md_dict



# def pandoc_md_to_latex(md_content):
#     """
#     calling pandoc program to convert markdown to LaTeX
#     """
    
#     cmd = ['pandoc', '-f', 'markdown',
#            '-t', 'latex', '--listings']
#     proc = subprocess.Popen(cmd,
#                             stdout=subprocess.PIPE,
#                             stdin=subprocess.PIPE)

#     result = proc.communicate(input=bytes(md_content, 'utf-8'))[0]
    
#     return result.decode('utf8')




# def get_latex_dict_from_md_list(latex_result, md_list):
#     """
#     For each text entry in md_list,
#     find section with title as hash(text) in latex document,
#     and use content of section (till next hypertarget tag) as latex value
#     """
#     md_dict = {}
#     for txt in md_list:
#         h = get_hash(txt)
#         latex_section = "\\section{" + h + "}"
#         start = latex_result.find(latex_section)
#         if (start < 0):
#             logging.error(
#                 "couldn't find hash in md_list. This shouldn't happen."
#                 + "I'm quitting.\n")
#             raise()
#         else:
#             start = latex_result.find("}}\n", start) + 3            
#         end = latex_result.find("\\hypertarget{", start + 1)
#         latex_content = latex_result[start:end].strip()
#         # svg support doesn't work in latex at the moment... so defaulting to pdf
#         latex_content = latex_content.replace('.svg}', '.pdf}')
#         latex_content = latex_content.replace('\includesvg', '\includegraphics')

#         latex_content = latex_content.replace(',height=\\textheight', '')
#         latex_content = latex_content.replace('\\passthrough', '')
#         md_dict[txt] = latex_content

#     return md_dict


def get_latex_md_dict_from_yaml(yaml_data):
    md_list = get_md_list_from_yaml(yaml_data)
    md_combined = md_combine_list(md_list)
    # latex_result = pandoc_md_to_latex(md_combined)
    # md_dict = get_latex_dict_from_md_list(latex_result, md_list)

    latex_result2 = mistletoe_md_to_latex(md_combined)      
    md_dict2 = get_latex_dict_from_md_list_mistletoe(latex_result2, md_list)

    # for k in md_dict:
    #     print(k)
    #     print('-- md_dict')
    #     print(md_dict[k])
    #     print('-- md_dict2')
    #     print(md_dict2[k])      
    
    return md_dict2



