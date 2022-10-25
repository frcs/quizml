import uuid
                
def correctness(a):
    if a['correct']:
        return 'correct'
    else:
        return 'incorrect'

def html_answers(answers, inputType):
    s = "<ol class='input' type='a'>"
    id = uuid.uuid4().hex
    for a in answers:
        s += "<li class='%s'>" % (correctness(a)) \
            + "<div class='block'>"  \
            + "<input name='%s' type='%s'>" % (id, inputType) \
            + a['answer'] \
            + "</div></li>" 
    s += "</ol>"
    return s
    
def html_multiple_answer(entry, marks):        
    s = "<li class='question'>" \
        + "<b>Multiple answer [" + str(marks) + " Marks]</b>"\
        + entry['question'] \
        + html_answers(entry['answers'], 'checkbox') \
        + "</li>\n"
    return s

def html_multiple_choice(entry, marks):
    s = "<li class='question'>"\
        + "<b>Multiple choice [" + str(marks) + " Marks]</b>"   \
        + entry['question']                                  \
        + html_answers(entry['answers'], 'radio') \
        + "</li>\n"
    return s

def html_essay(entry, marks):
    
    s = "<li class='question'><b>Essay [" + str(marks) + " Marks]</b>" \
        + entry['question'] \
        + "<div style='background:#eee; max-width: 34.5em; "\
        + "padding: 1em; margin-bottom:1em; margin-top:1em'>\n" \
        + "<p style='margin:0 0 1em 0'><b>indicative answer:</b></p>" \
        + (entry['answer'] if 'answer' in entry else '<no answer given>') \
        + "</div></li>\n"
    return s

def html_header(entry, marks):

    title = entry['title'] if 'title' in entry else 'test'
    author = entry['author'] if 'author' in entry else 'author'
    date = entry['date'] if 'date' in entry else 'date'
    
    return "<h1>" + title + "</h1>" \
        + "<p>" + date + "</p>" \
        + "<p>" + author + "</p>"

def html_prelude():

    s = """
    <!DOCTYPE html>
    <style>
    p {max-width: 40em;   page-break-before: avoid;}
    .correct { background: #bfb; max-width: 34em }
    .incorrect { background: #fbb; max-width: 34em }
    .question {  }
    ol.input input {
      display: none;
      float: left;
      position: relative;
      left: -2em;
      top: 1ex;
      page-break-before: avoid;
    }
    ol { max-width: 40em; page-break-before: avoid; }
    li { max-width: 40em; page-break-before: avoid; }
    div.block { }
    </style>
    <ol>
    """
    return s
    
def html_postlude(marks):
    return "<br><p><b>Total Marks " + str(sum(marks)) + "</b></p><br>" \
        + "</ol>"


def html_ordering(entry, marks):
    s = "<li class='question' style='vertical-align: top;'>"\
        "<b>Ordering [" + str(marks) + " Marks]</b>"   \
        + entry['question'] \
        + "<ol>"
    for a in entry['answers']:
        s += "<li><div class='block' style='border-left:2px solid; "\
            + "padding-left:1em; border-color: #f2f;max-width: 30.25em;'>"\
            + a['answer'] \
            + "</div></li>" 
    s += "</ol></li>\n"
    return s

def html_matching(entry, marks):
    s = "<li class='question'><b>Matching [" + str(marks) + " Marks]</b>"   \
        + entry['question']

    s += "<ol class='input' type='a'>"
    id = uuid.uuid4().hex
    for a in entry['answers']:
        s += "<li><ol><li>"\
            + "<div class='block' style='border-left:2px solid; "\
            + "padding-left:1em; border-color: #f2f;max-width: 30.25em;'>"\
            + a['answer'] \
            + "</div></li>" \
            + "<li><div class='block' "\
            + "style='border-left:2px solid; border-color: #2ff; "\
            + "padding-left:1em; max-width: 30.25em;'>"\
            + a['correct'] \
            + "</div></li></ol></li>" 
    s += "</ol></li>"
    return s


def render(yaml_data):

    handlers = {
        'mc': html_multiple_choice,
        'ma': html_multiple_answer,
        'essay': html_essay,
        'header': html_header,
        'matching': html_matching,
        'ordering': html_ordering,
    }

    default_marks = {
        'mc': 2.5,
        'ma': 2.5,
        'essay': 5,
        'header': 0,
        'matching': 2.5,
        'ordering': 2.5,
    }
    
    all_marks = []
    s = html_prelude()    
    for entry in yaml_data:
        entry_marks = entry.get('marks', default_marks[entry['type']])        
        all_marks.append(entry_marks)
        s += handlers[entry['type']](entry, entry_marks)
        
    s += html_postlude(all_marks)
    return s

