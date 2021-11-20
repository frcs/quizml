import os
from string import Template

default_marks = {
    'mc': 2.5,
    'ma': 2.5,
    'essay': 5,
    'header': 0,
    'matching': 2.5,
    'ordering': 2.5,
}

def latex_render_info(info, md_dict):
    if info is None:
        info = {}

    print(md_dict)
    s = "%% passing header info\n"
    for k,v in info.items():
        if k != 'type':                   
            s += "\\def \\info" + k + " {" + str(md_dict[str(v)]) + "}\n"
            

    return s

def latex_render_omr_answers(solutions):

    n = len(solutions)

    letter = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"];

    s = "\\begin{enumerate}"
    
    for i, q in enumerate(solutions):
        s += "\n    \item[{\\bf\\textit Q."+str(i+1) + ".}] "

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
                    
                s += ""
    s += "\n\\end{enumerate}"
                
    return s

    
def latex_render_header(entry, md_dict, marks):
    return ""

def latex_render_multiple_choice(entry, md_dict, marks):        
    s = latex_render_multiple_answer(entry, md_dict, marks)
    return s

def latex_render_essay(entry, md_dict, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + md_dict[entry['question']] \
        + "\\end{bbquestion}\n" \
        + "\\begin{answer}\n" \
        + (md_dict[entry['answer']] if 'answer' in entry else 'no answer given')\
        + "\\end{answer}\n"    
    return s

def latex_render_ordering(entry, md_dict, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + md_dict[entry['question']] \
        + "\\end{bbquestion}\n"
    return s

def latex_render_matching(entry, md_dict, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + md_dict[entry['question']] \
        + "\\end{bbquestion}\n"
    return s

def latex_render_multiple_answer(entry, md_dict, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + md_dict[entry['question']] \
        + "\n\n  \\vspace{1em}\n" \
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
    header = None
    for entry in yaml_data:
        if entry['type'] == 'header':
            header = yaml_data[0]
            break
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

def latex_render_questions(yaml_data, md_dict):

    handlers = {
        'mc': latex_render_multiple_choice,
        'ma': latex_render_multiple_answer,
        'essay': latex_render_essay,
        'header': latex_render_header,
        'matching': latex_render_matching,
        'ordering': latex_render_ordering,
    }
    
    all_marks = []

    questions = ""
    for entry in yaml_data:
        entry_marks = entry.get('marks', default_marks[entry['type']])        
        all_marks.append(entry_marks)        
        questions += handlers[entry['type']](entry, md_dict, entry_marks)
    return questions

def render(yaml_data, md_dict):
      
    header_info = get_header_info(yaml_data)
    solutions = get_solutions(yaml_data)
    
    info_str = latex_render_info(header_info, md_dict)
    questions_str = latex_render_questions(yaml_data, md_dict)

    omranswers_str = latex_render_omr_answers(solutions)

    
    dirname = os.path.dirname(__file__)
    template_filename = os.path.join(
        dirname, '../templates/tcd-eleceng-exam.tex')

    
    with open(template_filename, 'r') as template_file:
        template = Template(template_file.read())
    latex_content = template.substitute(
        info=info_str,
        omranswers=omranswers_str,
        questions=questions_str)
    
    return latex_content


