import math

from rich.table import box
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

import os

def is_bbquestion(yaml_entry):
    return yaml_entry['type'] in ['mc', 'ma', 'essay', 'matching', 'ordering']

def get_total_marks(yaml_data):
    total_marks = 0
    for entry in yaml_data:
        if is_bbquestion(entry):
            total_marks = total_marks + get_entry_marks(entry)
    return total_marks

def get_entry_marks(entry):

    default_marks = {
        'mc': 2.5,
        'ma': 2.5,
        'essay': 5,
        'header': 0,
        'matching': 2.5,
        'ordering': 2.5,
    }

    if 'marks' in entry:
        return entry['marks']
    elif entry['type'] in default_marks:
        return default_marks[entry['type']]
    else:
        return 0



def get_stats(yaml_data):
    total_marks = 0
    nb_questions = 0
    expected_mark = 0

    w, _ = os.get_terminal_size(0)
       
    stats = {"questions": []}
    
    for entry in yaml_data:
        if is_bbquestion(entry):
            nb_questions = nb_questions + 1
            question_marks = get_entry_marks(entry)
            total_marks = total_marks + question_marks
            
            if entry['type']=='mc':
                question_expected_mark = question_marks / len(entry['answers'])                
            elif entry['type']=='ma':
                question_expected_mark = question_marks / (2 ** (len(entry['answers'])-1))
            elif entry['type']=='matching':
                question_expected_mark =  question_marks / math.factorial(len(entry['answers']))
            elif entry['type']=='essay':
                question_expected_mark = 0
            else:
                question_expected_mark = 0

            expected_mark = expected_mark + question_expected_mark
            choices = (str(len(entry['answers']) if 'answers' in entry else '-'))
            lines = entry['question'].splitlines()
            excerpt = f"{lines[0]}" + (" […]" if len(lines)>1 else "")
            
            stats["questions"].append({"type":  entry['type'],
                                       "marks": question_marks,
                                       "choices": choices,
                                       "EM": question_expected_mark, 
                                       "excerpt": excerpt})

    stats["total marks"] = total_marks
    stats["expected mark"] = expected_mark/total_marks*100
    stats["nb questions"] = nb_questions
    return stats

    
