#!/usr/bin/python
import os
import sys
import yaml
import argparse
import logging
from string import Template

from .utils import *

from bbquiz.bbyaml.loader import load
from bbquiz.bbyaml.utils import transcode_md_in_yaml
from bbquiz.bbyaml.stats import get_stats

from bbquiz.markdown_export.html_dict_from_md_list import get_html_md_dict_from_yaml
from bbquiz.markdown_export.html_dict_from_md_list import PandocError
from bbquiz.markdown_export.html_dict_from_md_list import LatexError

from bbquiz.markdown_export.latex_dict_from_md_list import get_latex_md_dict_from_yaml

from bbquiz.render import to_csv
from bbquiz.render import to_html
from bbquiz.render import to_latex
from bbquiz.render import to_jinja
from bbquiz.render.to_jinja import Jinja2SyntaxError

from rich.traceback import install
install(show_locals=False)

from rich import print
from rich.panel import Panel

from time import sleep
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def zsh_completion_script():
    return ( 
"""
function _bbquiz(){
  _arguments \\
    "-h[Show help information]"\\
    "--help[Show help information]"\\
    "-w[continuously watch for file updates and recompile on change]"\\
    "--watch[continuously watch for file updates and recompile on change]"\\
    "--latex-template [filename of the jinja2 latex template]"\\
    "--zsh[A helper command used for exporting the command completion code in zsh]"\\
    '*:yaml file:_files -g \\*.\\(yml\|yaml\\)'
}

compdef _bbquiz bbquiz
""")


targets =[
    {
        "filename": "${inputbasename}.txt",
        "descr"   : "BlackBoard",
        "fmt"     : "html",
        "cmd"     : "${inputbasename}.txt",
        "template": "${bbquiztemplates}/bb.jinja"
    },
    {
        "filename": "${inputbasename}.html",
        "descr"   : "html preview",
        "fmt"     : "html",
        "cmd"     : "${inputbasename}.html",
        "template": "${bbquiztemplates}/preview-html.jinja"
    },
    {
        "filename": "${inputbasename}.tex",
        "descr"   : "Latex",
        "fmt"     : "latex",
        "cmd"     : "latexmk -xelatex -pvc ${inputbasename}.tex",
        "template": "${bbquiztemplates}/tcd-eleceng-latex.jinja"
    }]
    # {
    #     filename  = "${basename}.solutions.tex",
    #     descr      = "Latex solutions",
    #     fmt       = "latex",
    #     cmd       = "latexmk -xelatex -pvc ${basename}.solutions.tex",
    #     template  = "${bbquiztemplates}/latex-solutions.jinja",
    # }


def jinja_render_file(out_filename, template_filename, yaml_code):
    with open(out_filename, "w") as f:
        try:
            content = to_jinja.render(yaml_code, template_filename)
            f.write(content)            
        except (Jinja2SyntaxError):
            print(f"\n {Fore.RED} did not generate {out_filename} because of template errors  ! {Fore.RESET}\n ")


def compile(args):

    yaml_filename = args.yaml_filename
    # latex_template_filename = args.latextemplate
    # html_template_filename = args.htmltemplate
    # csv_template_filename = args.htmltemplate

    dirname = os.path.dirname(__file__)
    (basename, _) = os.path.splitext(yaml_filename)

    if not os.path.exists(yaml_filename):
        logging.error("No file {} found".format(yaml_filename))

    try:
        yaml_data = load(yaml_filename)
    except:
        return


    try:
        html_md_dict = get_html_md_dict_from_yaml(yaml_data)  
        latex_md_dict = get_latex_md_dict_from_yaml(yaml_data)
    except (LatexError, PandocError):
        print("\nXXX compilation stopped because of errors !\n ")
        return

    yaml_html = transcode_md_in_yaml(yaml_data, html_md_dict)
    yaml_latex = transcode_md_in_yaml(yaml_data, latex_md_dict)

    print_box("Stats", get_stats(yaml_data), Fore.BLUE)

    descr_list = []
    cmd_list = []
    
    for tgt in targets:
        out_filename = Template(tgt["filename"]).substitute({'inputbasename': basename})
        cmd = Template(tgt["cmd"]).substitute({'inputbasename': basename})
        descr = tgt["descr"]
        template_ = Template(tgt["template"]).substitute({'bbquiztemplates':os.path.join(dirname, 'templates')})
        template_filename = os.path.realpath(os.path.expanduser(template_)) 
        jinja_render_file(out_filename,  template_filename, yaml_latex if tgt["fmt"] == "latex" else yaml_html )
        descr_list.append(descr)
        cmd_list.append(cmd)
    
    spacer = len(max(descr_list, key=len))
    results_fmt = "\n".join([f"{d:{spacer+1}}: {c}" for d, c in zip(descr_list, cmd_list)])
    
    
    # if not latex_template_filename:
    #     latex_template_filename = os.path.join(
    #         dirname, 'templates/tcd-eleceng-latex.jinja')

    # if not csv_template_filename:
    #     csv_template_filename = os.path.join(
    #         dirname, 'templates/bb.jinja')
        
    # if not html_template_filename:
    #     html_template_filename = os.path.join(
    #         dirname, 'templates/preview-html.jinja')

            
    # csv_filename = basename + ".txt"
    # html_filename = basename + ".html"
    # latex_filename = basename + ".tex"
    # latex_solutions_filename = basename + ".solutions.tex"

       
    # with open(latex_solutions_filename, "w") as latex_solutions_file:
    #     latex_solutions_content = "\\let\\ifmyflag\\iftrue\\input{" \
    #         + latex_filename + "}"
    #     latex_solutions_file.write(latex_solutions_content)
        
    # jinja_render_file(csv_filename, csv_template_filename, yaml_html)
    # jinja_render_file(html_filename, html_template_filename, yaml_html)
    # jinja_render_file(latex_filename, latex_template_filename, yaml_latex)
        
    # results_fmt = (
    #     f'HTML output     : {html_filename}\n'
    #     f'BB output       : {csv_filename}\n'
    #     f'Latex output    : {latex_filename}\n'
    #     f'Latex solutions : {latex_solutions_filename}\n'
    #     f'Latex cmd       : latexmk -xelatex -pvc {latex_filename}\n'
    #     f'Latex cmd       : latexmk -xelatex -pvc {latex_solutions_filename}\n'
    # )

    
    print(Panel(results_fmt, title="Results",border_style="magenta"))

#    print_box("Results", results_fmt)
    
    ###########################################################################

def compile_on_change(args):
    print("\n...waiting for a file change to re-compile the document...\n " )    
    full_yaml_path = os.path.abspath(args.yaml_filename)
    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path == full_yaml_path:
                compile(args)
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
    parser.add_argument("--latextemplate", 
                        metavar="latex-template.jinja2",  
                        help="Latex jinja2 template")
    parser.add_argument("--htmltemplate", 
                        metavar="html-template.jinja2",  
                        help="HTML jinja2 template")
    parser.add_argument("--zsh",
                        help="A helper command used for exporting the "
                        "command completion code in zsh",
                        action="store_true")
    
    args = parser.parse_args()

    #    if not args.latextemplate:
    
    if args.zsh:
        print(zsh_completion_script())
        return
    
    if not args.yaml_filename:
        parser.error("quiz.yaml is required")
        
    if args.watch:
        compile(args)
        compile_on_change(args)
    else:
        compile(args)

if __name__=="__main__":
    main()
