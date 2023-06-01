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

from .utils import *
from ..utils import *
from ..bbyaml.utils import get_md_list_from_yaml

import mistletoe
from mistletoe.latex_renderer import LaTeXRenderer
    
                 
def capture_width_in_img_tags(latex_content):
    """
    Problem: we can allow for width parameters to passed to image:
    ![a pic](fig/pic.jpeg){width=40em}
    so we need to capture the width 
    """
    
    regex = r"\\includegraphics{(.*)}\s*\\\{\s*width\s*=\s*(.*)\\\}"
    subst = "\\\\includegraphics[width=\\2]{\\1}"
    result = re.sub(regex, subst, latex_content, 0, re.MULTILINE | re.DOTALL)
    return result


def mistletoe_md_to_latex(md_content):
    """
    using mistletoe to convert markdown to LaTeX
    """

    rendered = mistletoe.markdown(md_content, LaTeXRenderer)
    
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

        latex_content = capture_width_in_img_tags(latex_content) #re.sub(regex, subst, latex_content, 0, re.MULTILINE)
        
        latex_content = latex_content.replace(',height=\\textheight', '')
        latex_content = latex_content.replace('\\passthrough', '')
        md_dict[txt] = latex_content

    return md_dict


def get_latex_md_dict_from_yaml(yaml_data):
    md_list = get_md_list_from_yaml(yaml_data)
    md_combined = md_combine_list(md_list)
    latex_result = mistletoe_md_to_latex(md_combined)      
    md_dict = get_latex_dict_from_md_list_mistletoe(latex_result, md_list)
    
    return md_dict



