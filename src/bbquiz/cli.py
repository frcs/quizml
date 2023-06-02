#!/usr/bin/python

from rich.traceback import install
install(show_locals=False)

from rich import print
from rich.panel import Panel
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
from bbquiz.bbyaml.stats import print_stats
from bbquiz.bbyaml.loader import BBYamlSyntaxError

from bbquiz.markdown.html_dict_from_md_list import get_html_md_dict_from_yaml
from bbquiz.markdown.html_dict_from_md_list import MarkdownError
from bbquiz.markdown.html_dict_from_md_list import LatexError

from bbquiz.markdown.latex_dict_from_md_list import get_latex_md_dict_from_yaml

from bbquiz.render import to_jinja
from bbquiz.render.to_jinja import Jinja2SyntaxError

from time import sleep
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import appdirs


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
        except (Jinja2SyntaxError):
            print(f"\n {Fore.RED} did not generate {out_filename} because of template errors  ! {Fore.RESET}\n ")


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
            
def compile(args):
   
    yaml_filename = args.yaml_filename

    if not os.path.exists(yaml_filename):
        logging.error("No file {} found".format(yaml_filename))
    try:
        yaml_data = load(yaml_filename)
    except BBYamlSyntaxError as err:
        print(Panel(str(err), title="BByaml Syntax Error", border_style="red"))
        return 

    config = get_config(args)
    
    # transcode markdown to html and latex
    
    try:
        html_md_dict = get_html_md_dict_from_yaml(yaml_data)
        yaml_html = transcode_md_in_yaml(yaml_data, html_md_dict)
        
        latex_md_dict = get_latex_md_dict_from_yaml(yaml_data)
        yaml_latex = transcode_md_in_yaml(yaml_data, latex_md_dict)        
    except (LatexError, MarkdownError):
        print("\nXXX compilation stopped because of errors !\n ")
        return

    print_stats(yaml_data)

    descr_list = []
    descr_cmd_list = []
   
    target_list = get_target_list(yaml_filename, config)
    
    for target in target_list:
        jinja_render_file(
            target['out'],
            target['template'],
            yaml_latex if target["fmt"] == "latex" else yaml_html )
        
        descr_list.append(target['descr'])
        descr_cmd_list.append(target['descr_cmd'])
       
    spacer = len(max(descr_list, key=len))
    results_fmt = "\n".join([f"{d:{spacer+1}}: {c}"
                             for d, c in zip(descr_list, descr_cmd_list)])
      
    print(Panel(results_fmt, title="Results",border_style="magenta"))
    

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




        
