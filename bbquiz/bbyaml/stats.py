from colorama import Fore, Back, Style

def is_bbquestion(yaml_entry):
    return yaml_entry['type'] in ['mc', 'ma', 'essay', 'matching', 'ordering']




def get_stats(yaml_data):
    total_marks = 0
    nb_questions = 0
    question_id = 0
    expected_mark = 0

    default_marks = {
        'mc': 2.5,
        'ma': 2.5,
        'essay': 5,
        'header': 0,
        'matching': 2.5,
        'ordering': 2.5,
    }

    
    msg = f'{"Question":10s}{"Type":6s}{"Marks":7s}{"Choices":9s}{"ExpMark":9s}{" Text"}\n'
    msg = msg + f"{'─'*40}\n"
    
    for entry in yaml_data:
        if is_bbquestion(entry):
            nb_questions = nb_questions + 1
            question_id = question_id + 1
            question_marks = entry['marks'] if ('marks' in entry) else default_marks[entry['type']]
            total_marks = total_marks + question_marks
            
            if entry['type']=='mc':
                question_expected_mark = question_marks / len(entry['answers'])
                
            elif entry['type']=='ma':
                question_expected_mark = question_marks / (2 ** len(entry['answers']))
                
            elif entry['type']=='essay':
                question_expected_mark = 0
            else:
                question_expected_mark = 0
            expected_mark = expected_mark + question_expected_mark

            msg = msg + f"{question_id:6d}   "
            msg = msg + f"{entry['type']:^6s}"
            msg = msg + f"{question_marks:6.1f}" + ("*" if 'marks' not in entry else " ")
            msg = msg + f"{len(entry['answers']):6d}    "
            msg = msg + f"{question_expected_mark:5.1f}      "
            msg = msg + f"{entry['question'].splitlines()[0] + '...':33}\n"

    msg = msg + f"{'─'*40}\n"            
    msg = msg + f"{question_id:6d}   "
    msg = msg + f"  --  "
    msg = msg + f"{total_marks:6.1f}"
    msg = msg + f"      -   "
    msg = msg + f"{expected_mark/total_marks*100:6.1f}%\n"
    # msg = msg + f"{'─'*40}\n"            
    # msg = msg + f"Nb of Questions          : {nb_questions}\n"
    # msg = msg + f"Total Mark               : {total_marks}\n"
    # msg = msg + f"Expected Score (random)  : {expected_mark/total_marks*100:.1f}/100\n"
    
    return msg

