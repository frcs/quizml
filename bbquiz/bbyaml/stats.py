from colorama import Fore, Back, Style
import os

def is_bbquestion(yaml_entry):
    return yaml_entry['type'] in ['mc', 'ma', 'essay', 'matching', 'ordering']

def get_marks(entry):

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
    question_id = 0
    expected_mark = 0

    w, _ = os.get_terminal_size(0)
       
    msg = f'{"Question":10s}{"Type":6s}{"Marks":7s}{"Choices":9s}{"ExpMark":9s}{"Text"}\n'
    msg = msg + f"{'─'*(w-4)}\n"
    
    for entry in yaml_data:
        if is_bbquestion(entry):
            nb_questions = nb_questions + 1
            question_id = question_id + 1
            question_marks = get_marks(entry)
            total_marks = total_marks + question_marks
            
            if entry['type']=='mc':
                question_expected_mark = question_marks / len(entry['answers'])
                
            elif entry['type']=='ma':
                question_expected_mark = question_marks / (2 ** (len(entry['answers'])-1))
                
            elif entry['type']=='essay':
                question_expected_mark = 0
            else:
                question_expected_mark = 0

            expected_mark = expected_mark + question_expected_mark

            msg = msg + f"{question_id:6d}   "
            msg = msg + f"{entry['type']:^6s}"
            msg = msg + f"{question_marks:6.1f}" + ("*" if 'marks' not in entry else " ")
            choices = (str(len(entry['answers']) if 'answers' in entry else '-'))
            msg = msg + f"{choices:^9s}"
            msg = msg + f"{question_expected_mark:6.1f}    "
            lines = entry['question'].splitlines()
             
            msg = msg + f"{lines[0]}" + (" […]" if len(lines)>1 else "") + "\n"


    msg = msg + f"{'─'*(w-4)}\n"
    msg = msg + f"{question_id:6d}   "
    msg = msg + f"  --  "
    msg = msg + f"{total_marks:6.1f}"
    msg = msg + f"    -    "
    msg = msg + f"{expected_mark/total_marks*100:7.1f}%\n"
    
    return msg

