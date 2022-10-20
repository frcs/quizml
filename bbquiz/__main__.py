#!/usr/bin/python
import os
import sys
import yaml
import argparse
import logging

from bbquiz.bbyaml.loader import load
from bbquiz.markdown_export.html_dict_from_md_list import get_html_md_dict_from_yaml
from bbquiz.markdown_export.html_dict_from_md_list import PandocError
from bbquiz.markdown_export.html_dict_from_md_list import LatexError

from bbquiz.markdown_export.latex_dict_from_md_list import get_latex_md_dict_from_yaml

from bbquiz.render import to_csv
from bbquiz.render import to_html
from bbquiz.render import to_latex

from rich.traceback import install
install(show_locals=False)

from time import sleep
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .utils import *


def zsh_completion_script():
    return ( 
"""
function _bbquiz(){
  _arguments \\
    "-h[Show help information]"\\
    "--help[Show help information]"\\
    "-w[continuously watch for file updates and recompile on change]"\\
    "--watch[continuously watch for file updates and recompile on change]"\\
    "--zsh[A helper command used for exporting the command completion code in zsh]"\\
    '*:yaml file:_files -g \\*.\\(yml\|yaml\\)'
}

compdef _bbquiz bbquiz
""")


# def parse_args():
    

#     return parser.parse_args()

def is_bbquestion(yaml_entry):
    return yaml_entry['type'] in ['mc', 'ma', 'essay', 'matching', 'ordering']


# print(f'{"My Grocery List":^30s}')
# print(f'{"="*30}')
# print(f'{strApples:10s}{numApples:10d}\t${prcApples:>5.2f}')
# print(f'{strBread:10s}{numBread:10d}\t${prcBread:>5.2f}')
# print(f'{strCheese:10s}{numCheese:10d}\t${prcCheese:>5.2f}')
# print(f'{"Total:":>20s}\t${total:>5.2f}')


def get_info(yaml_data):
    total_marks = 0
    nb_questions = 0
    question_id = 0
    expected_mark = 0


    print(f"Question \t marks, choices, expected mark")
    print(f"{'='*30}")

    for entry in yaml_data:
        if is_bbquestion(entry):
            nb_questions = nb_questions + 1
            question_id = question_id + 1
            if 'marks' in entry:
                question_marks = entry['marks']
            else:
                question_marks = 5
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

            print(f"{question_id:2d} mark={question_marks:1.1f}, choices={len(entry['answers']):2d}, expected mark={question_expected_mark:2.1f}")

            
    print(f"Nb questions = {nb_questions}")
    print(f"Total = {total_marks}")
    print(f"total expected mark = {expected_mark}")
    


# msg = (f'{"Question":10s}{"marks":7s}{"choices":8s}{"expected-mark":13s}\n')
# msg = msg + f'{"─"*40}\n'
    
# for i in range(10):
#     question_id = i
#     question_marks = 5
#     question_expected_mark = 1
#     choices = 10
#     msg = msg + f"{question_id:^10d}{question_marks:^5.1f}{choices:^8d}{question_expected_mark:^13.1f}\n"

# print_box("info", msg, color=Fore.BLUE)

    
def compile(yaml_filename):

    if not os.path.exists(yaml_filename):
        logging.error("No file {} found".format(yaml_filename))

    try:
        yaml_data = load(yaml_filename)
    except:
        return
        
    
    (basename, _) = os.path.splitext(yaml_filename)
    csv_filename = basename + ".txt"
    html_filename = basename + ".html"
    latex_filename = basename + ".tex"
    latex_solutions_filename = basename + ".solutions.tex"

    try:
        html_md_dict = get_html_md_dict_from_yaml(yaml_data)  
        latex_md_dict = get_latex_md_dict_from_yaml(yaml_data)
    except (LatexError, PandocError):
        print("\nXXX compilation stopped because of errors !\n ")
        return

    get_info(yaml_data)

    with open(csv_filename, "w") as csv_file:
        csv_content = to_csv.render(yaml_data, html_md_dict)
        csv_file.write(csv_content)
        
    with open(html_filename, "w") as html_file:
        html_content = to_html.render(yaml_data, html_md_dict)
        html_file.write(html_content)

    with open(latex_filename, "w") as latex_file:
        latex_content = to_latex.render(yaml_data, latex_md_dict)
        latex_file.write(latex_content)

    with open(latex_solutions_filename, "w") as latex_solutions_file:
        latex_solutions_content = "\\let\\ifmyflag\\iftrue\\input{" \
            + latex_filename + "}"
        latex_solutions_file.write(latex_solutions_content)
        

    results_fmt = (
        f'HTML output     : {html_filename}\n'
        f'BB output       : {csv_filename}\n'
        f'Latex output    : {latex_filename}\n'
        f'Latex solutions : {latex_solutions_filename}\n'
        f'Latex cmd       : latexmk -xelatex -pvc {latex_filename}\n'
        f'Latex cmd       : latexmk -xelatex -pvc {latex_solutions_filename}\n'
    )
                   
    print_box("Results", results_fmt)
    
    ###########################################################################

def compile_on_change(yaml_filename):
    print("\n...waiting for a file change to re-compile the document...\n " )    
    full_yaml_path = os.path.abspath(yaml_filename)
    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path == full_yaml_path:
                compile(yaml_filename)
                print("\n...waiting for a file change to re-compile the document...\n ")
                

    observer = Observer()
    observer.schedule(Handler(), ".") # watch the local directory
    observer.start()

    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        quit()

    observer.join()


def main():

    parser = argparse.ArgumentParser(
        description = "Converts a questions in a YAML/markdown format into"\
        +  "a Blackboard test or a Latex script")

    parser.add_argument("yaml_filename", nargs='?',
                        metavar="quiz.yaml", type=str, 
                        help = "path to the quiz in a yaml format")
    parser.add_argument("-w", "--watch",
                        help="continuously compiles the document on file change",
                        action="store_true")
    parser.add_argument("--zsh",
                        help="A helper command used for exporting the "
                        "command completion code in zsh",
                        action="store_true")
    
    args = parser.parse_args()

    if args.zsh:
        print(zsh_completion_script())
        return
    
    if not args.yaml_filename:
        parser.error("quiz.yaml is required")
        
    if args.watch:
        compile(args.yaml_filename)
        compile_on_change(args.yaml_filename)
    else:
        compile(args.yaml_filename)

if __name__=="__main__":
    main()
