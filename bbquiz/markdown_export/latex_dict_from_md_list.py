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

    
                 
def get_hash(txt):
    return hashlib.md5(txt.encode('utf-8')).hexdigest()
 
def md_combine_list(md_list):
    txt = ""
    for md_entry in md_list:
        txt = txt + "\n\n# " + get_hash(md_entry) + "\n\n" + md_entry
    return txt


def pandoc_md_to_latex(md_content):
    cmd = ['pandoc', '-f', 'markdown',
           '-t', 'latex', '--listings']
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE)

    result = proc.communicate(input=bytes(md_content, 'utf-8'))[0]
    
    return result.decode('utf8')

def get_latex_dict_from_md_list(latex_result, md_list):
    
    md_dict = {}
    i = 0
    for txt in md_list:
        i = i + 1
        h = get_hash(txt)

        latex_section = "\\section{" + h + "}"
        
        start = latex_result.find(latex_section)
        if (start < 0):
            logging.error(
                "couldn't find hash in md_list. This shouldn't happen."
                + "I'm quitting.\n")
            raise()
        else:
            start = latex_result.find("}}\n", start) + 3
            
        end = latex_result.find("\\hypertarget{", start + 1) 
        
        latex_content = latex_result[start:end].strip()
        latex_content = latex_content.replace('.svg}', '.pdf}')
        latex_content = latex_content.replace(',height=\\textheight', '')
        latex_content = latex_content.replace('\\passthrough', '')

        md_dict[txt] = latex_content

    return md_dict


def get_latex_md_dict_from_yaml(yaml_data):

    
    md_list = get_md_list_from_yaml(yaml_data)

    md_combined = md_combine_list(md_list)
    
    with open("stuff.md", "w") as f:
        f.write(md_combined)
    
    
    latex_result = pandoc_md_to_latex(md_combined)  
    
    md_dict = get_latex_dict_from_md_list(latex_result, md_list)

    return md_dict



