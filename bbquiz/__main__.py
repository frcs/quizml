#!/usr/bin/python
import os
import sys
import yaml
import argparse
import logging

from bbquiz.bbyaml.loader import load
from bbquiz.markdown_export.html_dict_from_md_list import get_html_md_dict_from_yaml
from bbquiz.markdown_export.latex_dict_from_md_list import get_latex_md_dict_from_yaml
from bbquiz.render import to_csv
from bbquiz.render import to_html
from bbquiz.render import to_latex

from rich.traceback import install
install(show_locals=False)

from time import sleep
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def parse_args():
    parser = argparse.ArgumentParser(
        description = "Converts a questions in a YAML/markdown format into"\
        +  "a Blackboard test or a Latex script")

    parser.add_argument("yaml_filename", metavar="quiz.yaml", type=str, 
                        help = "path to the quiz in a yaml format")
    parser.add_argument("-w", "--watch",
                        help="continuously compiles the document on file change",
                        action="store_true")

    return parser.parse_args()


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
    
    html_md_dict = get_html_md_dict_from_yaml(yaml_data)  
    latex_md_dict = get_latex_md_dict_from_yaml(yaml_data)  

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
        
        
    print("-- results --")
    print("HTML output       : " + html_filename)
    print("BlackBoard output : " + csv_filename)
    print("Latex output      : " + latex_filename)
    print("Latex Solutions   : " + latex_solutions_filename)
    print("Latex cmd         : latexmk -xelatex -pvc " + latex_filename)
    print("Latex cmd         : latexmk -xelatex -pvc " \
          + latex_solutions_filename)

    ###########################################################################

def compile_on_change(yaml_filename):
    print("\n...waiting for a file change to re-compile the document...\n " \
    
    full_yaml_path = os.path.abspath(yaml_filename)
    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path == full_yaml_path:
                compile(yaml_filename)
                print("\n...waiting for a file change to re-compile the document...\n " \
                

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

    args = parse_args()
    yaml_filename = args.yaml_filename

    if args.watch:
        compile(yaml_filename)        
        compile_on_change(yaml_filename)
    else:
        compile(yaml_filename)
        
main()
