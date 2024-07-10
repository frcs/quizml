from bbquiz.bbyaml.loader import load_no_schema


import os
import sys

# from rich.traceback import install
# install(show_locals=False)

from rich import print
from rich.panel import Panel
from rich.table import Table
from rich.table import box
from rich.console import Console

# from rich_argparse import *

# import logging
# from rich.logging import RichHandler


# at the moment this is pretty basic
def questions_are_similar(q1, q2):
    return q1 == q2


def diff(args):
    """
    finds if questions can be found in other exams
    called with the --diff flag.
    """
    
    # remove duplicate files from list
    # this is useful when using something like exam*.yaml in arguments
    files = [args.yaml_filename]
    [files.append(item) for item in args.otherfiles if item not in files]

    # we load all the files. For speed, We do not do any schema checking.
    filedata = {}
    for f in files:
        if not os.path.exists(f):
            print(Panel("File " + f + " not found",
                        title="Error", border_style="red"))
            return
        try:
            # we need to turn off schema for speed this is OK because
            # everything will be considered as Strings anyway
            filedata[f] = load(f, schema=False) 
        except BBYamlSyntaxError as err:
            print(Panel(str(err),
                        title=f"BByaml Syntax Error in file {f}",
                        border_style="red"))
            return

    # checking for duplicate questions        
    ref = filedata[files[0]]
    for i, qr in enumerate(ref):
        for f in files[1:]:
            dst = filedata[f]        
            for j, qd in enumerate(dst):
                if questions_are_similar(qr, qd):
                    print(f"found match: Q{i : <2} matches Q{j : <2} in {f}:")
                    print(qr)


