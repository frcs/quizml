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
    if a.get('correct', 'incorrect'):
        return 'correct'
    else:
        return 'incorrect'

def csv_matching(entry):
    seq = ['MAT', entry.get('question','')]
    for a in entry.get('answers', None):
        seq.append(a.get('answer',''))
        seq.append(a.get('correct'))
    return "\t".join(seq) + "\n" 

def csv_ordering(entry):
    seq = ['ORD', entry.get('question', '')]
    for a in entry.get('answers', None):
        seq.append(a.get('answer', ''))
    return "\t".join(seq) + "\n" 

def csv_multiple_choice(entry):
    seq = ['MC', entry.get('question', '')]
    for a in entry.get('answers', None):
        seq.append(a.get('answer', ''))
        seq.append(correctness(a))
    return "\t".join(seq) + "\n" 

def csv_multiple_answer(entry):
    seq = ['MA', entry.get('question', '')]
    for a in entry.get('answers', None):
        seq.append(a.get('answer', ''))
        seq.append(correctness(a))
    return "\t".join(seq) + "\n" 
  
def csv_essay(entry):
    seq = ['ESS', entry.get('question', ''), entry.get('answer', '')]
    return "\t".join(seq) + "\n" 

def csv_header(entry):
    return ""

def render(yaml_data):

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
        s += handlers[entry['type']](entry)       
    return s


