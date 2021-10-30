default_marks_handler = {
    'mc': 2.5,
    'ma': 2.5,
    'essay': 5,
    'header': 0,
    'matching': 2.5,
    'ordering': 2.5,
}

def latex_info_render(info):
    if info is None:
        info = {'programmeyear': '',
                'examyear': '',
                'examsemester': '',
                'examdate': '',
                'examtime': '',
                'examvenue': '',
                'modulename': '',
                'modulecode': '',
                'examiner': '',
                'instructions': '',
                'materials': '',
                'additionalinformation': ''}
   
    s = "%% passing header info"
    for k,v in info:
        s += "\\{" + k + "}{" + v + "}\n"

    return s

def latex_omr_answers(solutions):

    n = len(solutions)

    letter = ["A", "B", "C", "D", "E", "F", "G", "H"];

    s = ""
    
    for i, q in enumerate(solutions):
        s += "    \item[{\\bf\\textit Q."+str(i+1) + ".}] "

        if q['type'] == 'essay':
            s += "essay question"
        elif q['type'] == 'ma':
            for j, correct in enumerate(q['solutions']):
                checked   = "\\x" + letter[j]
                unchecked = "\\o" + letter[j]
                
                if correct:                
                    s += "\\ifmyflag" + checked \
                        + "\\else" + unchecked + "\\fi"
                else:
                    s += unchecked
                    
                s += "\n"


    
def latex_header(entry, md_dict, marks):
    return ""

def latex_multiple_choice(entry, md_dict, marks):        
    s = latex_multiple_answer(entry, md_dict, marks)
    return s

def latex_essay(entry, md_dict, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + md_dict[entry['question']] \
        + "\\end{bbquestion}\n" \
        + "\\begin{answer}\n" \
        + md_dict[entry['answer']] \
        + "\\end{answer}\n"    
    return s

def latex_ordering(entry, md_dict, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + md_dict[entry['question']] \
        + "\\end{bbquestion}\n"
    return s

def latex_matching(entry, md_dict, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + md_dict[entry['question']] \
        + "\\end{bbquestion}\n"
    return s

def latex_multiple_answer(entry, md_dict, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + md_dict[entry['question']] \
        + "  \\begin{enumerate}\\setcounter{enumii}{0}\n" \
        + "     \\setlength\\itemsep{0em}"
    for a in entry['answers']:
        s += "    \\item" + ("[\\iX]" if a['correct'] else "[\\iO]") \
            + md_dict[a['answer']] \
            + "\n" 
    s += "  \\end{enumerate}\n\\end{bbquestion}\n"
    return s


#########################################


def get_header_info(yaml_data):
    if yaml_data[0]['type'] == 'header':
        header = yaml_data[0]
    else:
        header = None        
    return header


def get_solutions(yaml_data):
    solutions = []
    for entry in yaml_data:
        if entry['type'] == 'essay':
            solutions.append({'type': 'essay'})
        if entry['type'] == 'ma':
            s = []
            for a in entry['answers']:
                s.append(a['correct'])
            solutions.append({'type': 'ma', 'solutions': s})

    return solutions


#########################################

def latex_questions_render():

    handlers = {
        'mc': latex_multiple_choice,
        'ma': latex_multiple_answer,
        'essay': latex_essay,
        'header': latex_header,
        'matching': latex_matching,
        'ordering': latex_ordering,
    }
    
    all_marks = []

    questions = ""
    for entry in yaml_data:
        if "marks" in entry:
            entry_marks = entry['marks']
        else:
            entry_marks = default_marks_handler[entry['type']]
        all_marks.append(entry_marks)        
        questions += handlers[entry['type']](entry, md_dict, entry_marks)


def render(yaml_data, md_dict):
   
    handlers = {
        'mc': latex_multiple_choice,
        'ma': latex_multiple_answer,
        'essay': latex_essay,
        'header': latex_header,
        'matching': latex_matching,
        'ordering': latex_ordering,
    }
   
    all_marks = []

    header_info = get_header_info(yaml_data)
    solutions = get_solutions(yaml_data)

    
    info_str = latex_info_render(info)
    questions_str = latex_questions_render(info)
        
    s += latex_postlude(all_marks)
    return s


