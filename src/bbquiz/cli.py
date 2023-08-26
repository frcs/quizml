#!/usr/bin/python

from rich.traceback import install
install(show_locals=False)

from rich import print
from rich.panel import Panel
from rich.table import Table
from rich.table import box
from rich.console import Console

from rich_argparse import *

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
from bbquiz.bbyaml.loader import BBYamlSyntaxError

#from bbquiz.markdown.html_dict_from_md_list import get_html_md_dict_from_yaml
from bbquiz.markdown.markdown import get_dicts_from_yaml
from bbquiz.markdown.exceptions import MarkdownError, LatexEqError
#from bbquiz.markdown.latex_dict_from_md_list import get_latex_md_dict_from_yaml

from bbquiz.render import to_jinja
from bbquiz.render.to_jinja import Jinja2SyntaxError

from time import sleep
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import appdirs
import pathlib


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



def jinja_render_file(out_filename, template_filename, yaml_code):
    with open(out_filename, "w") as f:
        try:
            content = to_jinja.render(yaml_code, template_filename)
            f.write(content)            
        except Jinja2SyntaxError as err:
            print(Panel(
                f"\n did not generate {out_filename} because of template errors  ! \n "
                + str(err), title='Jinja Template Error', border_style="red"))
            


def cfg_template_render(target, key, substitutions_dict, default_template):

    if (key not in target) or target["descr"] is None:
        val = default_template
    else:
        val = target[key]
       
    return Template(val).substitute(substitutions_dict)
            

def get_config(args):

    if args.config:
        config_file = os.path.realpath(os.path.expanduser(args.config))
    else:    
        pkg_dirname = os.path.dirname(__file__)
        pkg_template_dir = os.path.join(pkg_dirname, 'templates')
        
        config_dir = appdirs.user_config_dir(appname="bbquiz", appauthor='frcs')
        config_file = os.path.join(config_dir, 'bbquiz.cfg')
        
        for d in [os.getcwd(), config_dir, pkg_template_dir]:
            fname = os.path.join(d, 'bbquiz.cfg')
            config_file = os.path.realpath(os.path.expanduser(fname))
            if os.path.exists(config_file):
                break
                    
    try:
        with open(config_file) as f:            
            config = yaml.load(f, Loader=yaml.FullLoader)
    except yaml.YAMLError as exc:
        print ("Something went wrong while parsing the config file " + config_file)
        raise exception

    return config
    

def get_target_list(yaml_filename, config):

    (basename, _) = os.path.splitext(yaml_filename)
    pkg_dirname = os.path.dirname(__file__)
    pkg_template_dir = os.path.join(pkg_dirname, 'templates')
    
    config_dir = appdirs.user_config_dir(appname="bbquiz", appauthor='frcs')
        
    subs = {'inputbasename': basename}

    target_list = []
    
    for t in config['targets']:
        target = {}
        target["out"] = cfg_template_render(t, "out", subs, '')
        target["fmt"] = cfg_template_render(t, "fmt", subs, 'html')
        target["descr"] = cfg_template_render(t, "descr", subs, '')
        target["descr_cmd"] = cfg_template_render(t, "descr_cmd", subs, t['out'])

        for d in [os.getcwd(), config_dir, pkg_template_dir]:
            target["template"] = os.path.realpath(
                os.path.expanduser(os.path.join(d, t["template"])))
            if os.path.exists(target["template"]):
                break

        target_list.append(target)
    
    return target_list

def print_stats_table(stats):
    console = Console()

    table = Table(box=box.SIMPLE,collapse_padding=True, show_footer=True)
    table.add_column("Q", f"{stats['nb questions']}", no_wrap=True, justify="right")
    table.add_column("Type", "--", no_wrap=True, justify="center")
    table.add_column("Marks", f"{stats['total marks']:3.1f}",  no_wrap=True, justify="right")
    table.add_column("#", "-", no_wrap=True, justify="right")
    table.add_column("Exp", f"{stats['expected mark']:2.1f}" + "%", no_wrap=True, justify="right")
    table.add_column("Question Statement", no_wrap=False, justify="left")
    for i, q in enumerate(stats["questions"]):
        table.add_row(f"{i+1}", q["type"], f"{q['marks']:2.1f}",
                       f"{q['choices']}", f"{q['EM']:3.1f}", q["excerpt"] )

    console.print(table)


def compile(args):
    """
    compiles the targets of a bbyaml file
    """

    # read config file

    config = get_config(args)

    # load BBYaml file

    yaml_filename = args.yaml_filename
    
    if not os.path.exists(yaml_filename):
        print(Panel("File " + yaml_filename + " not found",
                    title="Error", border_style="red"))
        return
    try:
        yaml_data = load(yaml_filename)
    except BBYamlSyntaxError as err:
        print(Panel(str(err),
                    title="BByaml Syntax Error", border_style="red"))
        return
        
    # load all markdown entries into a list 
    # and build dictionaries of their HTML and LaTeX translations
    
    try:
        (latex_md_dict, html_md_dict) = get_dicts_from_yaml(yaml_data)
        yaml_latex = transcode_md_in_yaml(yaml_data, latex_md_dict)        
        yaml_html = transcode_md_in_yaml(yaml_data, html_md_dict)
    except LatexEqError as err:
        print(Panel(str(err), title="Latex Error", border_style="red"))
        return
    except MarkdownError as err:
        print(Panel(str(err), title="Markdown Error", border_style="red"))
        return

    # diplay stats about the questions

    print_stats_table(get_stats(yaml_data))
   
    # get target list from config file

    target_list = get_target_list(yaml_filename, config)
    
    # render each target
    # success_list = [False] * len(target_list)
    rows = []
    
    for i, target in enumerate(target_list):
        try:
            yaml_code = yaml_latex if target["fmt"] == "latex" else yaml_html
            render = to_jinja.render(yaml_code, target['template'])
            pathlib.Path(target['out']).write_text(render)
            rows.append([ target["descr"], target["descr_cmd"], "" ])

        except Jinja2SyntaxError as err:            
            print(Panel(
                f"\n did not generate {out_filename} because of template errors  ! \n "
                + str(err), title='Jinja Template Error', border_style="red"))
            rows.append([ target['descr'] , target["descr_cmd"], "[FAIL]" ])
            
    # print target outputs

    table_outputs = Table(box=box.SIMPLE, collapse_padding=True, show_footer=False, show_header=False)
    table_outputs.add_column("Descr", no_wrap=True, justify="left")
    table_outputs.add_column("Cmd", no_wrap=True, justify="left")
    table_outputs.add_column("Status", no_wrap=True, justify="left")

    for r in rows:
        if r[2]=="[FAIL]":
            table_outputs.add_row(*r, style="red")
        elif r[2]=="":
            table_outputs.add_row(*r)
       
    print(Panel(table_outputs, title="Target Ouputs", border_style="magenta"))
    
    

def compile_on_change(args):
    """
    compiles the targets if input bbyaml file has changed on disk
    """
    
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

    RichHelpFormatter.styles = {
        'argparse.args': 'cyan', 
        'argparse.groups': 'yellow',
        'argparse.help': 'grey50',
        'argparse.metavar': 'dark_cyan', 
        'argparse.prog': 'default', 
        'argparse.syntax': 'bold',
        'argparse.text': 'default',
        "argparse.pyproject": "green"
    }

    
    formatter = lambda prog: RawDescriptionRichHelpFormatter(
        prog, max_help_position=52)

    parser = argparse.ArgumentParser(
        formatter_class=formatter,
        description = "Converts a questions in a YAML/markdown format into"\
        +  " a Blackboard test or a Latex script")

    parser.add_argument("yaml_filename", nargs='?',
                        metavar="quiz.yaml", type=str, 
                        help = "path to the quiz in a yaml format")
    parser.add_argument("-w", "--watch", 
                        help="continuously compiles the document on file change",
                        action="store_true")

    default_config_dir = appdirs.user_config_dir(appname="bbquiz", appauthor='frcs')
    
    parser.add_argument("--config", 
                        metavar="CONFIGFILE",  
                        help=f"user config file. Default location is {default_config_dir}"
                        )
    parser.add_argument("--latextemplate", 
                        metavar="TEMPLATEFILE",  
                        help="Latex jinja2 template")
    parser.add_argument("--htmltemplate", 
                        metavar="TEMPLATEFILE",  
                        help="HTML jinja2 template")
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
        compile(args)
        compile_on_change(args)
    else:
        compile(args)




        
