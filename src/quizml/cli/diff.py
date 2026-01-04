import os
import sys

from rich import print
from rich.panel import Panel
from rich.table import Table
from rich.table import box
from rich.console import Console

import difflib

from quizml.loader import load
# from quizml.stats import get_questions
# from quizml.stats import get_stats
from quizml.exceptions import QuizMLYamlSyntaxError

# from rich_argparse import *

# import logging
# from rich.logging import RichHandler


def normalize_text(text):
    """Normalize whitespace and case."""
    if not isinstance(text, str):
        return str(text)
    return ' '.join(text.strip().lower().split())

def get_choices_content(q):
    """Extracts choices content as a sorted list of strings."""
    choices = q.get('choices', [])
    content = []
    if isinstance(choices, list):
        for c in choices:
            # Handle list of dicts or strings
            if isinstance(c, dict):
                for v in c.values():
                    content.append(normalize_text(v))
            else:
                content.append(normalize_text(str(c)))
    return sorted(content)

def questions_are_similar(q1, q2):
    # Check type first
    if q1.get('type') != q2.get('type'):
        return False
        
    # Compare question text
    t1 = normalize_text(q1.get('question', ''))
    t2 = normalize_text(q2.get('question', ''))
    
    # Fuzzy match threshold for question text
    matcher = difflib.SequenceMatcher(None, t1, t2)
    if matcher.ratio() < 0.9: # 90% similarity
        return False
        
    # Compare choices if they exist (normalized strict match)
    c1 = get_choices_content(q1)
    c2 = get_choices_content(q2)
    
    if c1 != c2:
        return False 

    # Compare figure if they exist (normalized strict match)
    f1 = normalize_text(q1.get('figure', ''))
    f2 = normalize_text(q2.get('figure', ''))
    
    if f1 != f2:
        return False 
        
    return True


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
            filedata[f] = load(f, validate=False) 
        except QuizMLYamlSyntaxError as err:
            print(Panel(str(err),
                        title=f"QuizMLYaml Syntax Error in file {f}",
                        border_style="red"))
            return

    # checking for duplicate questions
    ref_yaml = filedata[files[0]]
    ref_questions = ref_yaml['questions']
    
    other_files = files[1:]

    qstats = []
    
    for i, qr in enumerate(ref_questions):

        lines = str(qr.get('question', '')).splitlines()
        long_excerpt = (lines[0] if lines else "") + (" […]" if len(lines)>1 else "")
        
        if 'choices' in qr and isinstance(qr['choices'], list):
            for ans in qr['choices']:
                val_str = ""
                if isinstance(ans, dict):
                    # Concatenate values of keys like x, o, true, false
                    val_str = " ".join([str(v) for v in ans.values()])
                else:
                    val_str = str(ans)
                
                lines = val_str.splitlines()
                if lines:
                    long_excerpt += f"\n  * {lines[0]}" + (" […]" if len(lines)>1 else "")
                       
        qstats.append({"type": qr['type'],
                       "excerpt": long_excerpt})
                
        for f in other_files:
            dst_questions = filedata[f]['questions']
            for j, qd in enumerate(dst_questions):
                if questions_are_similar(qr, qd):
                    qstats[i].setdefault('dups',[]).append(f)

    print_dups_table(qstats)

def print_dups_table(qstats):
    """
    prints a table with information about each question, including:
      * question id
      * question type
      * excerpt of the question statement
      * other files that match that question
    """

    has_dups = False
    
    console = Console()
  
    table = Table(box=box.SIMPLE,collapse_padding=True, show_footer=True)

    table.add_column("Q", no_wrap=True, justify="right")
    table.add_column("Type", no_wrap=True, justify="center")
    table.add_column("Question Statement", no_wrap=False, justify="left")
    table.add_column("Dups", no_wrap=False, justify="left")
    
    for i, q in enumerate(qstats):
        if 'dups' in q :
            has_dups = True
            table.add_row(f"{i+1}", q["type"], q["excerpt"], ', '.join(q.get('dups','')))

    if has_dups:
        console.print(table)
    else:
        print("no dups found")
        
                    
