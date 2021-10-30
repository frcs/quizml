#########################################

#     - tab-delimited text file, don't use quotes to delimit text fields.
# ***** Multiple choice
#       - MC, question, Choice1, correct/incorrect, Choice2, c/i, Choice3, c/i
#       - TF, question, TRUE/FALSE
#       - MA, question, Choice1, correct/incorrect, Choice2, c/i, Choice3, c/i
#         (multiple answer)
#       - ORD = ordering
#       - ESS = essay
#       - MAT = matching
#       - FIB = fill in blanks
#       - FIL = fill
#       - NUM = numeric
#       - SR = short response
#       - FIB_PLUS = multiple fill in blanks

def correctness(a):
    if a['correct']:
        return 'correct'
    else:
        return 'incorrect'

def csv_matching(entry, md_dict):
    seq = ['MAT', md_dict[entry['question']]]
    for a in entry['answers']:
        seq.append(md_dict[a['answer']])
        seq.append(md_dict[a['correct']])
    return "\t".join(seq) + "\n" 

def csv_ordering(entry, md_dict):
    seq = ['ORD', md_dict[entry['question']]]
    for a in entry['answers']:
        seq.append(md_dict[a['answer']])
    return "\t".join(seq) + "\n" 

def csv_multiple_choice(entry, md_dict):
    seq = ['MC', md_dict[entry['question']]]
    for a in entry['answers']:
        seq.append(md_dict[a['answer']])
        seq.append(correctness(a))
    return "\t".join(seq) + "\n" 

def csv_multiple_answer(entry, md_dict):
    seq = ['MA', md_dict[entry['question']]]
    for a in entry['answers']:
        seq.append(md_dict[a['answer']])
        seq.append(correctness(a))
    return "\t".join(seq) + "\n" 
  
def csv_essay(entry, md_dict):
    seq = ['ESS', md_dict[entry['question']], md_dict[entry['answer']]]
    return "\t".join(seq) + "\n" 

def csv_header(entry, md_dict):
    return ""

def render(yaml_data, md_dict):

    handlers = {
        'mc': csv_multiple_choice,
        'ma': csv_multiple_answer,
        'essay': csv_essay,
        'matching': csv_matching,
        'header': csv_header,
        'ordering': csv_ordering,
    }
    
    s = ""
    for entry in yaml_data:
        s += handlers[entry['type']](entry, md_dict)       
    return s

