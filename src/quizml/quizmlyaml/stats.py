"""helper functions for gathering statistics about the test



"""

import math
import os

def is_question(yaml_entry):
    """tests if an entry is an actual question

    """
    
    return yaml_entry['type'] in ['tf', 'mc', 'ma', 'essay', 'matching', 'ordering']

def get_questions(yaml_data):
    """returns a list of all the entries that are actual questions 

    """
    
    return list(filter(lambda entry: is_question(entry), yaml_data['questions']))

def get_total_marks(yaml_data):
    """computes the maximum possible total marks for a test.

    """

    total_marks = 0
    questions = get_questions(yaml_data)
    for entry in questions:
        total_marks = total_marks + get_entry_marks(entry)
    return total_marks

def get_entry_marks(entry):
    """returns the marks of an entry. Applying default marks if the
    'marks' key is missing.

    """

    default_marks = {
        'mc': 2.5,
        'ma': 2.5,
        'tf': 2.5,
        'essay': 5,
        'matching': 2.5,
        'ordering': 2.5,
    }

    if 'marks' in entry:
        try:
            return float(entry['marks'])
        except (ValueError, TypeError):
            # If 'marks' cannot be converted to float, treat it as 0
            return 0.0
    elif entry['type'] in default_marks:
        return default_marks[entry['type']]
    else:
        return 0

def question_success_probability(entry):
    """returns the probability of successfully answering a question at
    random.

    """
    
    if entry['type']=='mc':
         return 1.0 / len(entry['choices'])                
    elif entry['type']=='ma':
        return 1.0 / (2 ** (len(entry['choices'])-1))
    elif entry['type']=='tf':
        return 1.0 / 2
    elif entry['type']=='matching':
        return 1.0 / math.factorial(len(entry['choices']))
    elif entry['type']=='essay':
        return 0.0
    else:
        return 0.0

def question_number_choices(entry):
    """returns the number of options for a question

    """
    
    if entry['type']=='mc':
         return str(len(entry['choices']))
    elif entry['type']=='ma':
        return str(len(entry['choices']))
    elif entry['type']=='tf':
        return str(2)
    elif entry['type']=='matching':
        return str(len(entry['choices']))
    elif entry['type']=='essay':
        return "-"
    else:
        return "-"

    
def get_stats(yaml_data):
    """returns a dictionary of statistics about the questions in a QuizMLYaml test.

    Output structure looks something like this:

    stats = { "total marks": 15.0,
              "nb questions": 2,
              "expected mark": 0.5,
              "questions": [ { "type": "ma",
                               "marks": "10.0",
                               "choices": "4",
                               "EM": "0.1",
                               "excerpt": "Choose all answers that..." },
                             { "type": "mc",
                               "marks": "5.0",
                               "choices": "4",
                               "EM": "0.4",
                               "excerpt": "Choose the best solution for..." },
                           ]
            }

    """

    total_marks = 0
    expected_mark = 0
       
    stats = {"questions": []}

    questions = get_questions(yaml_data)
    for entry in questions:
        question_marks = get_entry_marks(entry)
        total_marks = total_marks + question_marks        
        question_expected_mark = question_marks*question_success_probability(entry)
        expected_mark = expected_mark + question_expected_mark
        choices = question_number_choices(entry)
        lines = entry['question'].strip().splitlines()
        excerpt = f"{lines[0]}" + ("…" if len(lines)>1 else "")

        stat_entry = {"type"    : entry['type'],
                      "marks"   : question_marks,
                      "choices" : choices,
                      "EM"      : question_expected_mark, 
                      "excerpt" : excerpt}
        stats["questions"].append(stat_entry)

    stats["total marks"] = total_marks
    stats["expected mark"] = expected_mark/total_marks*100
    stats["nb questions"] = len(questions)
    return stats

    
