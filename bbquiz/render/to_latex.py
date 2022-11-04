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

def latex_render_info(info):
    if info is None:
        info = {}

    s = "%% passing header info\n"
    for k,v in info.items():
        if k != 'type':                   
            s += "\\def \\info" + k + " {" + str(v) + "}\n"
            

    return s

def latex_render_omr_answers(solutions):

    n = len(solutions)

    letter = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"];

    s = "\\begin{enumerate}"
    
    for i, q in enumerate(solutions):
        s += "\n    \item[{\\bf\\textit Q."+str(i+1) + ".}] "

        if q['type'] == 'essay':
            s += "essay question"
        elif q['type'] in ['ma', 'mc']:
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

    
def latex_render_header(entry, marks):
    return ""

def latex_render_multiple_choice(entry, marks):        
    s = latex_render_multiple_answer(entry, marks)
    return s

def latex_render_essay(entry, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + entry['question'] \
        + "\\end{bbquestion}\n" \
        + "\\begin{answer}\n" \
        + (entry['answer'] if 'answer' in entry else 'no answer given')\
        + "\\end{answer}\n"    
    return s

def latex_render_ordering(entry, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + entry['question'] \
        + "\\end{bbquestion}\n"
    return s

def latex_render_matching(entry, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + entry['question'] \
        + "\\end{bbquestion}\n"
    return s

def latex_render_multiple_answer(entry, marks):        
    s = "\\begin{bbquestion}[" + str(marks) + "]\n" \
        + entry['question'] \
        + "\n\n  \\vspace{1em}\n" \
        + "  \\begin{enumerate}\\setcounter{enumii}{0}\n" \
        + "     \\setlength\\itemsep{0em}"
    for a in entry['answers']:
        s += "    \\item" + ("[\\iX]" if a['correct'] else "[\\iO]") \
            + a['answer'] \
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
        if entry['type'] in 'ma':
            s = []
            for a in entry['answers']:
                s.append(a['correct'])
            solutions.append({'type': 'ma', 'solutions': s})
        if entry['type'] in 'mc':
            s = []
            for a in entry['answers']:
                s.append(a['correct'])
            solutions.append({'type': 'mc', 'solutions': s})

    return solutions


#########################################

def latex_render_questions(yaml_data):

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
        questions += handlers[entry['type']](entry, entry_marks)
    return questions

def render(yaml_data):
      
    header_info = get_header_info(yaml_data)
    solutions = get_solutions(yaml_data)
    
    info_str = latex_render_info(header_info)
    questions_str = latex_render_questions(yaml_data)

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


