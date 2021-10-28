#!/usr/bin/python
import subprocess
import os
import sys
import uuid
import yaml
import markdown
import re
import html
import hashlib

import json
import struct

import argparse

from subprocess import call
import tempfile
import base64
from collections import defaultdict


def get_md_list_from_yaml(yaml_data):
    def get_md_list_from_yaml_rec(yaml_data, md_list):
        # keys that with a string value that should not be converted to markdown
        non_md_keys = ['type']
        for i in yaml_data:
            for key, val in i.items():
                if isinstance(val, list):
                    get_md_list_from_yaml_rec(val, md_list)
                elif isinstance(val, str) and key not in non_md_keys:
                    if val not in md_list:
                        md_list.append(val)

    md_list = []
    get_md_list_from_yaml_rec(yaml_data, md_list);
    return md_list
    
                 
def get_hash(txt):
    return hashlib.md5(txt.encode('utf-8')).hexdigest()
 
def md_combine_list(md_list):
    txt = ""
    for md_entry in md_list:
        txt = txt + "\n\n# " + get_hash(md_entry) + "\n\n" + md_entry
    return txt


def join_unique(alist, blist):
    for b in blist:
        if b not in alist:
            alist.append(b)
    return alist


def parse_json(json_data):
    eq_list = []
    if isinstance(json_data, dict):
        for key, val in json_data.items():
            if key == 't' and val == 'Math':
                join_unique(eq_list, [json_data["c"]])
            if isinstance(val, list):
                for i in val:
                    eq_list = join_unique(eq_list, parse_json(i))
    if isinstance(json_data, list):
        for i in json_data:
            eq_list = join_unique(eq_list, parse_json(i))
                    
    return eq_list


def replace_with_image(c, eq_dict):
    [w, h, base64] = eq_dict[c[0]['t'] + c[1]]
    return {
        "t":
            "Image",
        "c": [[
            "", ["math", "inline"],
            [["width", str(w / 2)], ["height", str(h / 2)]]
        ], [], [base64, c[1]]]
    }

def parse_json_replace_maths(json_data, eq_dict):
    if isinstance(json_data, dict):
        for key, val in json_data.items():
            if key == 't' and val == 'Math':
                return replace_with_image(json_data["c"], eq_dict)
            if isinstance(val, list):
                new_val = []
                for i in val:
                    new_val.append(parse_json_replace_maths(i, eq_dict))
                json_data[key] = new_val
    if isinstance(json_data, list):
        new_json_data = []
        for i in json_data:
            new_json_data.append(parse_json_replace_maths(i, eq_dict))
        json_data = new_json_data
    return json_data

def get_image_info(data):
    w, h = struct.unpack('>LL', data[16:24])
    width = int(w)
    height = int(h)
    return width, height

def png_file_to_base64(pngfile):
    with open(pngfile, "rb") as image_file:
        data = image_file.read()
        [w, h] = get_image_info(data)
        data64 = "data:image/png;base64," + \
            base64.b64encode(data).decode('ascii')
    return (w, h, data64)


def pandoc_md_to_json(md_content):
    cmd = ['pandoc', '-f', 'markdown', '-t', 'json']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    result = proc.communicate(input=bytes(md_content, 'utf-8'))[0]
    return json.loads(result)

def get_html_dict_from_md_list(html_result, md_list):
    md_dict = {}
    i = 0
    for txt in md_list:
        i = i + 1
        h = get_hash(txt)
        html_h1 = h + "</h1>"
        start = html_result.find(html_h1) + len(html_h1)
        end = html_result.find("<h1 id", start + 1)
        html_content = html_result[start:end]

        regex = r"([\n]*)([ ]*<[/]?[a-zA-Z \'=\"]+>[ ]*)([\n]*)"
        subst = "\\2"
        html_content = re.sub(regex, subst, html_content, 0, re.MULTILINE)
        html_content = html_content.replace('\n', '<br>').replace(
            'class="math inline"',
            'class="math inline" style="vertical-align:middle"')
        html_content = html_content.replace(
            '<code>',
            '<code style="font-family:\'Courier New\'">')
        html_content = html_content.replace(
            '<pre>',
            '<pre style="background:#eee; padding: 1em; max-width: 80em;">')
        md_dict[txt] = html_content
    return md_dict

def pandoc_json_to_sefcontained_html(json_data):
    cmd = [ 'pandoc', '-f', 'json', '-t', 'html', '--self-contained',
            '--metadata', 'title="temp"']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    
    result = proc.communicate(input=bytes(json.dumps(json_data), 'utf-8'))[0]
    return result.decode('utf-8')

def convert_latex_eqs(data_json):

    eq_list = parse_json(data_json)
    
    latex_preamble = \
        "\\documentclass[multi={mymath1,mymath2},border=1pt]{standalone}\n" + \
        "\\usepackage{amsmath}\n"+ \
        "\\newenvironment{mymath1}{$\displaystyle}{$}\n" +\
        "\\newenvironment{mymath2}{$}{$}\n" +\
        "\\begin{document}\n"

    tmpdir = tempfile.mkdtemp()
    olddir = os.getcwd()
    os.chdir(tmpdir)

    latex_filename = "eq_list.tex"
    pdf_filename = "eq_list.pdf"
    png_base = "eq_img_"

    f = open(latex_filename, 'w')
    f.write(latex_preamble)

    for eq in eq_list:
        if eq[0]['t'] == 'InlineMath':
            f.write("\\begin{mymath2}" + eq[1] + "\\end{mymath2}\n")
        if eq[0]['t'] == 'DisplayMath':
            f.write("\\begin{mymath1}" + eq[1] + "\\end{mymath1}\n")

    f.write("\\end{document}\n")
    f.close()

    call(["pdflatex", latex_filename], stdout=sys.stderr)
    call(["gs", "-dBATCH", '-q', "-dNOPAUSE", "-sDEVICE=pngalpha", "-r250",
          "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
          "-sOutputFile=" + png_base + "%05d.png", pdf_filename])

    it = 0
    eq_dict = {}
    for eq in eq_list:
        it = it + 1
        [w, h, data64] = png_file_to_base64(png_base + "%05d.png" % it)
        eq_dict[eq[0]['t'] + eq[1]] = (w, h, data64)

    os.chdir(olddir)

    json_out = parse_json_replace_maths(data_json, eq_dict)
    return json_out


def get_html_md_dict_from_yaml(yaml_data):

    md_list = get_md_list_from_yaml(yaml_data)

    md_combined = md_combine_list(md_list)

    data_json = pandoc_md_to_json(md_combined)

    data_json = convert_latex_eqs(data_json)
    
    html_result = pandoc_json_to_sefcontained_html(data_json)
    
    md_dict = get_html_dict_from_md_list(html_result, md_list)

    return md_dict



def pandoc_md_to_latex(md_content):
    cmd = ['pandoc', '-f', 'markdown', '-t', 'latex', '--listings']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    result = proc.communicate(input=bytes(md_content, 'utf-8'))[0]
    return result.decode('utf8')


def get_latex_dict_from_md_list(latex_result, md_list):
    
    md_dict = {}
    i = 0
    for txt in md_list:
        i = i + 1
        h = get_hash(txt)

        latex_section = "\\section{" + h + "}"
        
        start = latex_result.find(latex_section)
        if (start < 0):
            print("couldn't find hash in md_list. This shouldn't happen."
                  + "I'm quitting.\n")
            quit()
        else:
            start = latex_result.find("}}\n", start) + 3
            
        end = latex_result.find("\\hypertarget{", start + 1) 
        
        latex_content = latex_result[start:end]        
        latex_content = latex_content.replace('.svg}', '.pdf}')
        latex_content = latex_content.replace(',height=\\textheight', '')
        latex_content = latex_content.replace('\\passthrough', '')

        
#        latex_content = latex_content.replace('\\begin{lstlisting}', '\\begin{lstlisting}\\begin{verbatim}')

        md_dict[txt] = latex_content

    return md_dict


def get_latex_md_dict_from_yaml(yaml_data):

    md_list = get_md_list_from_yaml(yaml_data)

    md_combined = md_combine_list(md_list)

    latex_result = pandoc_md_to_latex(md_combined)  
    
    md_dict = get_latex_dict_from_md_list(latex_result, md_list)

    return md_dict



###########################################################################

def correctness(a):
    if a['correct']:
        return 'correct'
    else:
        return 'incorrect'

def html_answers(answers, inputType, md_dict):
    s = "<ol class='input' type='a'>"
    id = uuid.uuid4().hex
    for a in answers:
        s += "<li class='%s'>" % (correctness(a)) \
            + "<div class='block'>"  \
            + "<input name='%s' type='%s'>" % (id, inputType) \
            + md_dict[a['answer']] \
            + "</div></li>" 
    s += "</ol>"
    return s
    
def html_multiple_answer(entry, md_dict, marks):        
    s = "<li class='question'>" \
        + "<b>Multiple answer [" + str(marks) + " Marks]</b>"\
        + md_dict[entry['question']] \
        + html_answers(entry['answers'], 'checkbox', md_dict) \
        + "</li>\n"
    return s

def html_multiple_choice(entry, md_dict, marks):
    s = "<li class='question'>"\
        + "<b>Multiple choice [" + str(marks) + " Marks]</b>"   \
        + md_dict[entry['question']]                                  \
        + html_answers(entry['answers'], 'radio', md_dict) \
        + "</li>\n"
    return s

def html_ordering(entry, md_dict, marks):
    s = "<li class='question' style='vertical-align: top;'>" \
        + "<b>Ordering [" + str(marks) + " Marks]</b>"   \
        + md_dict[entry['question']] \
        + "<ol>"
    for a in entry['answers']:
        s += "<li><div class='block' style='border-left:2px solid; "\
            + "padding-left:1em; border-color: #f2f;max-width: 30.25em;'>"\
            + md_dict[a['answer']] \
            + "</div></li>" 
    s += "</ol></li>\n"
    return s


def html_matching(entry, md_dict, marks):
    s = "<li class='question'>"\
        + "<b>Matching [" + str(marks) + " Marks]</b>"   \
        + md_dict[entry['question']]

    s += "<ol class='input' type='a'>"
    id = uuid.uuid4().hex
    for a in entry['answers']:
        s += "<li><ol><li><div class='block' "\
            + "style='border-left:2px solid; "\
            + "padding-left:1em; border-color: #f2f;max-width: 30.25em;'>"\
            + md_dict[a['answer']] \
            + "</div></li>" \
            + "<li><div class='block' " \
            + "style='border-left:2px solid; border-color: #2ff; "\
            + "padding-left:1em; max-width: 30.25em;'>"\
            + md_dict[a['correct']] \
            + "</div></li></ol></li>" 
    s += "</ol></li>"
    return s


def html_essay(entry, md_dict, marks):
    s = "<li class='question'><b>Essay [" + str(marks) + " Marks]</b>" \
        + md_dict[entry['question']] \
        + "<div style='background:#eee; max-width: 34.5em; "\
        + "padding: 1em; margin-bottom:1em; margin-top:1em'>\n" \
        + "<p style='margin:0 0 1em 0'><b>indicative answer:</b></p>" \
        + md_dict[entry['answer']] \
        + "</div></li>\n"
    return s

def html_header(entry, md_dict, marks):
    title = md_dict[entry['title']]
    date = md_dict[entry['date']]
    author = md_dict[entry['author']]

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



###############################################################

def latex_prelude(info, solutions):

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
   
    preamble = "\\documentclass{tcdexams}\n" \
    + "\\providecommand{\\tightlist}" \
    + "{\\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}}" \
    + "\\programmeyearname{" + info.get('programmeyear','') + "}\n" \
    + "\\examsemester{" + info.get('examsemester','') + "}\n" \
    + "\\examyear{" + str(info.get('examyear',2100)) + "}\n" \
    + "\\examdate{" + info.get('examdate','') + "}\n" \
    + "\\examtime{" + info.get('examtime','') + "}\n" \
    + "\\examvenue{" + info.get('examvenue','') + "}\n" \
    + "\\modulename{" + info.get('modulename','') + "}\n" \
    + "\\modulecode{" + info.get('modulecode','') + "}\n" \
    + "\\examiner{" + info.get('examiner','') + "}\n" \
    + "\\instructions{" + info.get('instructions','') + "}\n" \
    + "\\materials{" + info.get('materials','') + "}\n" \
    + "\\additionalinformation{" + info.get('additionalinformation','') + "}\n" \
    + "\\usepackage[totalmarks]{examquestions}\n" \
    + "\\usepackage{listings}\n" \
    + "\\lstset{frame=l,language=python,basicstyle=\\ttfamily\\scriptsize,numbers=left,numberstyle=\\tiny\\color{gray},keywordstyle=\\color{blue},commentstyle=\\color{green}\\ttfamily,stringstyle=\\color{red},texcl=false}" \
    + "\\newcounter{bbquestion}\n" \
    + "\\newenvironment{bbquestion}[1][]{\\sbox\\qmarks{\\bfseries #1 marks}"\
    + "\\refstepcounter{bbquestion}\\par\\medskip\\textbf{Q.\\thebbquestion.}"\
    + "\\hfill\\begin{minipage}[t]{0.92\\textwidth}}{\\hspace*{0em plus 1fill}"\
    + "\\makebox{\\bfseries [\\usebox{\\qmarks}]}\\end{minipage}"\
    + "\\vspace{\\subquestionskip}}\n" \
    + "\\usepackage{amsmath}\n" \
    + "\\usepackage{amssymb}\n"


    omr_preamble = \
"""
\\usepackage{tikz,pgfplots,environ}
\\usetikzlibrary{matrix,chains,positioning,decorations.pathreplacing,arrows,backgrounds}

\\usepackage{parskip,setspace,xspace}
\\onehalfspacing

\\usepackage{etoolbox}
\\usepackage{ifxetex}
\\usepackage{ifluatex}

\\ifboolexpr{bool {xetex} or bool {luatex}}{
  \\usepackage{fontspec}
  \\defaultfontfeatures{Ligatures=TeX}

  \\newcounter{fontsnotfound}
  \\newcommand{\\checkfont}[1]{%
    \\suppressfontnotfounderror=1%
    \\font\\x = "#1" at 10pt
    \\selectfont
    \\ifx\\x\\nullfont%
      \\stepcounter{fontsnotfound}%
    \\fi%
    \\suppressfontnotfounderror=0%
  }
  \\newcommand{\\iffontsexist}[3]{%
    \\setcounter{fontsnotfound}{0}%
    \\expandafter\\forcsvlist\\expandafter%
    \\checkfont\\expandafter{#1}%
    \\ifnum\\value{fontsnotfound}=0%
      #2%
    \\else%
      #3%
    \\fi%
  }
}{
  \\typeout{%
    You need to compile with XeLaTeX or LuaLaTeX to use the Fira fonts.%
  }
}

\\newcommand{\\btVFill}{\\vskip0pt plus 1filll}

\\usepackage{nccmath}
\\usepackage{empheq}
\\usepackage[many]{tcolorbox}
\\usepackage{ragged2e}
\\justifying

\\usepackage{subfig}
\\usepackage{changepage}
\\usepackage{booktabs}
\\usepackage[scale=2]{ccicons}
\\usepackage{verbatim}
\\usepackage[percent]{overpic}
\\usepackage[absolute,overlay]{textpos}

\\usepackage{array,booktabs}
\\usepackage{multirow}
\\usepackage{xspace}

\\usepackage{adjustbox}
\\captionsetup[subfigure]{labelformat=empty}

\\usepackage{fancyhdr}

\\newcommand{\\omrSIZE}{}
\\newcommand{\\omrSKIP}{.7em}
%%\\newcommand{\\omrFONT}{\\fontspec{[OMRBubbles.ttf]}}
\\newcommand{\\omrFONT}{\\fontspec{OMR}}

\\newcommand{\\omrDIGITS}{{\\omrSIZE \\omrFONT \\XeTeXglyph 17\\hspace{\\omrSKIP}\\XeTeXglyph 18\\hspace{\\omrSKIP}\\XeTeXglyph 19\\hspace{\\omrSKIP}\\XeTeXglyph 20\\hspace{\\omrSKIP}\\XeTeXglyph 21\\hspace{\\omrSKIP}\\XeTeXglyph 22\\hspace{\\omrSKIP}\\XeTeXglyph 23\\hspace{\\omrSKIP}\\XeTeXglyph 24\\hspace{\\omrSKIP}\\XeTeXglyph 25\\hspace{\\omrSKIP}\\XeTeXglyph 26}}

\\newcommand{\\omrCHECK}[1]{\\raisebox{-6pt}{\\scalebox{1}{\\tikz{\\filldraw[fill=black!57, draw=none] (0, 0) circle (0.25); \\node (x1) at (0, 0) {\\omrFONT #1};}}}}

\\newcommand{\\omrNOCHECK}[1]{\\raisebox{-6pt}{\\scalebox{1}{\\tikz{\\filldraw[fill=black!0, draw=none] (0, 0) circle (0.25); \\node (x1) at (0, 0) {\\omrFONT #1};}}}}

\\ifcsname ifmyflag\\endcsname\\else
  \\expandafter\\let\\csname ifmyflag\\expandafter\\endcsname
                  \\csname iffalse\\endcsname
                  \\fi


\\ifmyflag
\\newcommand{\\iO}{\\refstepcounter{enumii}\\omrNOCHECK{\\alph{enumii}}}
\\newcommand{\\iX}{\\refstepcounter{enumii}\\omrCHECK{\\alph{enumii}}}
\\else
\\newcommand{\\iO}{\\refstepcounter{enumii}\\omrNOCHECK{\\alph{enumii}}}
\\newcommand{\\iX}{\\refstepcounter{enumii}\\omrNOCHECK{\\alph{enumii}}}
\\fi


\\newcommand{\\xA}{{\\omrCHECK{\\XeTeXglyph 66}}}
\\newcommand{\\xB}{{\\omrCHECK{\\XeTeXglyph 67}}}
\\newcommand{\\xC}{{\\omrCHECK{\\XeTeXglyph 68}}}
\\newcommand{\\xD}{{\\omrCHECK{\\XeTeXglyph 69}}}
\\newcommand{\\xE}{{\\omrCHECK{\\XeTeXglyph 70}}}
\\newcommand{\\xF}{{\\omrCHECK{\\XeTeXglyph 71}}}
\\newcommand{\\xG}{{\\omrCHECK{\\XeTeXglyph 72}}}
\\newcommand{\\xH}{{\\omrCHECK{\\XeTeXglyph 73}}}
\\newcommand{\\xI}{{\\omrCHECK{\\XeTeXglyph 74}}}

\\newcommand{\\oA}{{\\omrNOCHECK{\\XeTeXglyph 66}}}
\\newcommand{\\oB}{{\\omrNOCHECK{\\XeTeXglyph 67}}}
\\newcommand{\\oC}{{\\omrNOCHECK{\\XeTeXglyph 68}}}
\\newcommand{\\oD}{{\\omrNOCHECK{\\XeTeXglyph 69}}}
\\newcommand{\\oE}{{\\omrNOCHECK{\\XeTeXglyph 70}}}
\\newcommand{\\oF}{{\\omrNOCHECK{\\XeTeXglyph 71}}}
\\newcommand{\\oG}{{\\omrNOCHECK{\\XeTeXglyph 72}}}
\\newcommand{\\oH}{{\\omrNOCHECK{\\XeTeXglyph 73}}}
\\newcommand{\\oI}{{\\omrNOCHECK{\\XeTeXglyph 74}}}

\\newcommand{\\oT}{{\\omrNOCHECK{\\XeTeXglyph 85}}}
\\newcommand{\\xT}{{\\omrCHECK{\\XeTeXglyph 85}}}

\\newcommand{\\Q}[1]{{\\\\[1em]{\\bf\\textit Q#1. }}}


\\ifmyflag
     \\newenvironment{answer}[1][]
     {\\par\\medskip 
      \\noindent \\color{red} }
     { \\medskip }
\\else
\\usepackage{environ}

\\NewEnviron{answer}{%
\\par  \\medskip   \\medskip

}

\\fi


\\usepackage{tabto}
\\usepackage{multicol}

"""

    omr_answer_sheet = """
\\vspace*{-5em}
\\begin{minipage}[t]{.6\\linewidth}
Student Name: \\tabto{3cm} \\underline{\\hspace{6cm}}

Student Number : \\tabto{3.5cm} \\underline{\\hspace{5.5cm}}
\\end{minipage}
\\begin{minipage}[t]{.4\\linewidth}
  Mark your student number below

  \\omrDIGITS

  \\omrDIGITS

  \\omrDIGITS

  \\omrDIGITS

  \\omrDIGITS

  \\omrDIGITS

  \\omrDIGITS

  \\omrDIGITS
      
\\end{minipage}

\\vspace{1em}
{\\bf 
  All your MCQ answers must be filled in on this answer page. 
}

For {\\bf True} or {\\bf False} questions, mark \\oT or \\oF. For
questions with multiple choices, mark all solutions that are correct
(for instance \\xA\\xB\\oC\\xD).

\\vspace{0.5em}

\\begin{multicols}{3}
  \\begin{enumerate}
"""
    n = len(solutions)

    letter = ["A", "B", "C", "D", "E", "F", "G", "H"];
    
    for i, q in enumerate(solutions):
        omr_answer_sheet += "    \item[{\\bf\\textit Q."+str(i+1) + ".}] "

        if q['type'] == 'essay':
            omr_answer_sheet += "essay question"
        elif q['type'] == 'ma':
            for j, correct in enumerate(q['solutions']):
                checked   = "\\x" + letter[j]
                unchecked = "\\o" + letter[j]
                
                if correct:                
                    omr_answer_sheet += "\\ifmyflag" + checked \
                        + "\\else" + unchecked + "\\fi"
                else:
                    omr_answer_sheet += unchecked
                    
                omr_answer_sheet += "\n"
    
    omr_answer_sheet += \
"""        
  \\end{enumerate}
\\end{multicols}


\\pagebreak

\\vspace*{7cm}

\\begin{center}
This page is intentionally left blank.
\\end{center}

\\pagebreak

"""    
    s = preamble + omr_preamble \
        + "\\begin{document}\n" \
        + "\\pagestyle{plain}\n" \
        + "\\maketitle\n"

    s += omr_answer_sheet   
    
    return s
    
def latex_header(entry, md_dict, marks):
    return ""

def latex_postlude(marks):
    return "\\end{document}\n "

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

def html_ordering(entry, md_dict, marks):
    s = "<li class='question' style='vertical-align: top;'>"\
        "<b>Ordering [" + str(marks) + " Marks]</b>"   \
        + md_dict[entry['question']] \
        + "<ol>"
    for a in entry['answers']:
        s += "<li><div class='block' style='border-left:2px solid; "\
            + "padding-left:1em; border-color: #f2f;max-width: 30.25em;'>"\
            + md_dict[a['answer']] \
            + "</div></li>" 
    s += "</ol></li>\n"
    return s

def html_matching(entry, md_dict, marks):
    s = "<li class='question'><b>Matching [" + str(marks) + " Marks]</b>"   \
        + md_dict[entry['question']]

    s += "<ol class='input' type='a'>"
    id = uuid.uuid4().hex
    for a in entry['answers']:
        s += "<li><ol><li>"\
            + "<div class='block' style='border-left:2px solid; "\
            + "padding-left:1em; border-color: #f2f;max-width: 30.25em;'>"\
            + md_dict[a['answer']] \
            + "</div></li>" \
            + "<li><div class='block' "\
            + "style='border-left:2px solid; border-color: #2ff; "\
            + "padding-left:1em; max-width: 30.25em;'>"\
            + md_dict[a['correct']] \
            + "</div></li></ol></li>" 
    s += "</ol></li>"
    return s


def html_essay(entry, md_dict, marks):
    s = "<li class='question'><b>Essay [" + str(marks) + " Marks]</b>" \
        + md_dict[entry['question']] \
        + "<div style='background:#eee; max-width: 34.5em; "\
        + "padding: 1em; margin-bottom:1em; margin-top:1em'>\n" \
        + "<p style='margin:0 0 1em 0'><b>indicative answer:</b></p>" \
        + md_dict[entry['answer']] \
        + "</div></li>\n"
    return s

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

#########################################


def html_parse(yaml_data, md_dict):

    handlers = {
        'mc': html_multiple_choice,
        'ma': html_multiple_answer,
        'essay': html_essay,
        'header': html_header,
        'matching': html_matching,
        'ordering': html_ordering,
    }

    default_marks_handler = {
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
        if "marks" in entry:
            entry_marks = entry['marks']
        else:
            entry_marks = default_marks_handler[entry['type']]
        all_marks.append(entry_marks)
        s += handlers[entry['type']](entry, md_dict, entry_marks)
        
    s += html_postlude(all_marks)
    return s

########################################

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

def latex_parse(yaml_data, md_dict):
   
    handlers = {
        'mc': latex_multiple_choice,
        'ma': latex_multiple_answer,
        'essay': latex_essay,
        'header': latex_header,
        'matching': latex_matching,
        'ordering': latex_ordering,
    }

    default_marks_handler = {
        'mc': 2.5,
        'ma': 2.5,
        'essay': 5,
        'header': 0,
        'matching': 2.5,
        'ordering': 2.5,
    }
    
    all_marks = []

    header_info = get_header_info(yaml_data)
    solutions = get_solutions(yaml_data)
    print(solutions)
    s = latex_prelude(header_info, solutions);
    
    for entry in yaml_data:
        if "marks" in entry:
            entry_marks = entry['marks']
        else:
            entry_marks = default_marks_handler[entry['type']]
        all_marks.append(entry_marks)        
        s += handlers[entry['type']](entry, md_dict, entry_marks)
        
    s += latex_postlude(all_marks)
    return s



def csv_parse(yaml_data, md_dict):

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

###########################################################################

def parse():
    parser = argparse.ArgumentParser(description = "Converts a questions in a YAML/markdown format into"\
                        +  "a Blackboard test or a Latex script")

    parser.add_argument("yaml_filename", metavar="quiz.yaml", type=str, 
                        help = "path to the quiz in a yaml format")
    
    return parser.parse_args()


def main():

    args = parse()
    yaml_filename = args.yaml_filename
    
    try:
        my_name = sys.argv[0]
        yaml_filename = sys.argv[1]
    except IndexError:
        print("Usage: %s INPUT.yaml" % os.path.basename(MY_NAME))
        exit(1)

    (basename, _) = os.path.splitext(yaml_filename)
    csv_filename = basename + ".txt"
    html_filename = basename + ".html"
    latex_filename = basename + ".tex"
    latex_solutions_filename = basename + ".solutions.tex"
    
    with open(yaml_filename) as yaml_file:
        yaml_data = yaml.load(yaml_file, Loader=yaml.FullLoader)

    html_md_dict = get_html_md_dict_from_yaml(yaml_data)  
    latex_md_dict = get_latex_md_dict_from_yaml(yaml_data)  
    
    with open(csv_filename, "w") as csv_file:
        csv_content = csv_parse(yaml_data, html_md_dict)
        csv_file.write(csv_content)
        
    with open(html_filename, "w") as html_file:
        html_content = html_parse(yaml_data, html_md_dict)
        html_file.write(html_content)

    with open(latex_filename, "w") as latex_file:
        latex_content = latex_parse(yaml_data, latex_md_dict)
        latex_file.write(latex_content)

    with open(latex_solutions_filename, "w") as latex_solutions_file:
        latex_solutions_content = "\\let\\ifmyflag\\iftrue\\input{" \
            + latex_filename + "}"
        latex_solutions_file.write(latex_solutions_content)
        
        
    print("HTML output       : " + html_filename)
    print("BlackBoard output : " + csv_filename)
    print("Latex output      : " + latex_filename)
    print("Latex Solutions   : " + latex_solutions_filename)
    print("Latex cmd         : latexmk -xelatex -pvc " + latex_filename)
    print("Latex cmd         : latexmk -xelatex -pvc " \
          + latex_solutions_filename)

    ###########################################################################
        
main()
