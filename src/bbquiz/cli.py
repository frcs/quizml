#!/usr/bin/python

from importlib.metadata import version

from rich.traceback import install
install(show_locals=False)

from rich import print
from rich.panel import Panel
from rich.table import Table
from rich.table import box
from rich.console import Console

from rich_argparse import *

import logging
from rich.logging import RichHandler

import os
import sys
import yaml
import argparse
from string import Template

from .utils import *

from bbquiz.bbyaml.loader import load
from bbquiz.bbyaml.utils import transcode_md_in_yaml
from bbquiz.bbyaml.stats import get_stats
from bbquiz.bbyaml.loader import BBYamlSyntaxError

from bbquiz.markdown.markdown import get_dicts_from_yaml
from bbquiz.markdown.exceptions import MarkdownError, LatexEqError
from bbquiz.render import to_jinja
from bbquiz.render.to_jinja import Jinja2SyntaxError

from time import sleep
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import appdirs
import pathlib

import bbquiz.shellcompletion 
import subprocess
import shlex

class FileLocator:
    """
    Config file and templates are defined as a relative path, and searched in:
    1. the local directory from which BBQuiz is called 
    2. the default application config dir 
    3. the install package templates dir
    """

    def __init__(self):
        """
        sets up default directories to search
        """
        
        pkg_template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        app_dir = appdirs.user_config_dir(appname="bbquiz", appauthor='frcs')
        user_config_dir = os.path.join(app_dir, 'templates')
        self.dirlist = [ os.getcwd(), user_config_dir, pkg_template_dir ]

    def locate_in_default_dirs(self, path):
        """
        finds file in list of directories to search. returns None
        """
        
        if os.path.isabs(path):
            if os.path.exists(path):
                return path
        else:
            for d in self.dirlist:
                abspath = os.path.realpath(
                    os.path.expanduser(os.path.join(d, path)))
                if os.path.exists(abspath):
                    return abspath
        return FileNotFoundError(f"{path} was not found")

locator = FileLocator()

def jinja_render_file(out_filename, template_filename, yaml_code):
    """
    renders the jinja template
    """

    with open(out_filename, "w") as f:
        try:
            content = to_jinja.render(yaml_code, template_filename)
            f.write(content)            
        except Jinja2SyntaxError as err:
            print(Panel(
                f"\n did not generate {out_filename} because of template errors  ! \n "
                + str(err), title='Jinja Template Error', border_style="red"))
           

def get_config(args):
    """
    returns the yaml data of the config file
    """

    if args.config:
        config_file = os.path.realpath(os.path.expanduser(args.config))
    else:
        config_file = locator.locate_in_default_dirs('bbquiz.cfg')
   
    logging.info(f"using config file:{config_file}")
    
    try:
        with open(config_file) as f:            
            config = yaml.load(f, Loader=yaml.FullLoader)
    except yaml.YAMLError as exc:
        print ("Something went wrong while parsing the config file " + config_file)
        raise exception

    return config
    
    

def get_target_list(yaml_filename, config):
    """
    gets the list of target templates from config['targets'] and
      * resolves the absolute path of each template
      * also resolves $inputbasename 
    """
    
    (basename, _) = os.path.splitext(yaml_filename)
    
    subs = {'inputbasename': basename}   
    target_list = []
    for t in config['targets']:
        target = {}
        # resolves $inputbasename
        for key, val in t.items():
            target[key] = Template(val).substitute(subs)
        # resolves relative path for template
        if 'template' in target:
            target['template'] = locator.locate_in_default_dirs(t['template'])
            logging.info(f"using template file:{target['template']}")
            
        target_list.append(target)
    
    return target_list

def print_stats_table(stats):
    """
    prints a table with information about each question, including:
      * question id
      * question type
      * marks for the question
      * nb of possible solutions
      * expected mark if answering at random
      * excerpt of the question statement
    """
    
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


def compile_build_task(target):
    command = shlex.split(target["build_cmd"])
    try:
        output = subprocess.check_output(command)
        return True
    
    except subprocess.CalledProcessError as e:
        print(Panel(e.output.decode(),
                    title = f"\n failed to build command ",
                    border_style="red"))
        
        return False
    
    
def compile_template_task(target, yaml_dict):

    if target["fmt"] not in yaml_dict:
        print(Panel(
            f"\n did not generate {out_filename} because {target['fmt']} is "
            + "not a valid format for a template (only 'html' and 'latex' "
            + "are valid). Check your target definition in your config file.",
            title='Config Error', border_style="red"))
        return False

    try:
        rendered_doc = to_jinja.render(yaml_dict[target["fmt"]],
                                           target['template'])        
        # write rendered_doc to output file
        pathlib.Path(target['out']).write_text(rendered_doc)
        
        return True
    
    except Jinja2SyntaxError as err:
        print(Panel(
            f"\n did not generate {out_filename} because of template errors  ! \n "
            + str(err), title='Jinja Template Error', border_style="red"))
        return False

    
    
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
        yaml_dict = {}
        (latex_md_dict, html_md_dict) = get_dicts_from_yaml(yaml_data)
        yaml_dict['latex'] = transcode_md_in_yaml(yaml_data, latex_md_dict)        
        yaml_dict['html'] = transcode_md_in_yaml(yaml_data, html_md_dict)
    except LatexEqError as err:
        print(Panel(str(err), title="Latex Error", border_style="red"))
        return
    except MarkdownError as err:
        print(Panel(str(err), title="Markdown Error", border_style="red"))
        return
    except FileNotFoundError as err:
        print(Panel(str(err), title="FileNotFoundError Error", border_style="red"))
        return
       
    # diplay stats about the questions
    print_stats_table(get_stats(yaml_data))
   
    # get target list from config file
    target_list = get_target_list(yaml_filename, config)
    
    # sets up list of the output for each build
    targets_output = []

    # if args.build:
    #     print("building post commands")
    success_list = {}
    
    for i, target in enumerate(target_list):

        # skipping build target if build option is not on
        if ("build_cmd" in target) and not args.build:
            continue

        # a build target (eg. compile pdf of generated latex)
        if ("build_cmd" in target) and args.build:
            # need to check if there is a dependency,
            # and if this dependency compiled fine
            if (("dep" not in target) or
                ("dep" in target and success_list[target['dep']])):
                success = compile_build_task(target)
            else:
                success = False

        # a template task that needs to be rendered
        if ("template" in target):
            success = compile_template_task(target, yaml_dict)

        success_list[target['out']] = success
        
        targets_output.append(
            [ target['descr'] ,
              target["descr_cmd"],
              "" if success else "[FAIL]" ])
            
    # print to terminal a table of all targets outputs.
    table_outputs = Table(box=box.SIMPLE,
                          collapse_padding=True,
                          show_footer=False,
                          show_header=False)
    
    table_outputs.add_column("Descr", no_wrap=True, justify="left")
    table_outputs.add_column("Cmd", no_wrap=True, justify="left")
    table_outputs.add_column("Status", no_wrap=True, justify="left")

    for row in targets_output:
        if row[2]=="[FAIL]":
            table_outputs.add_row(*row, style="red")
        elif row[2]=="":
            table_outputs.add_row(*row)
       
    print(Panel(table_outputs, title="Target Ouputs", border_style="magenta"))
    
    

def compile_on_change(args):
    """
    compiles the targets if input bbyaml file has changed on disk
    """

    waitingtxt = ("\n...waiting for a file change"
                  "to re-compile the document...\n ")
    print(waitingtxt)
    full_yaml_path = os.path.abspath(args.yaml_filename)
    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path == full_yaml_path:
                compile(args)
                print(waitingtxt)
               
    observer = Observer()
    observer.schedule(Handler(), ".") # watch the local directory
    observer.start()

    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()

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
        +  " a Blackboard test or a LaTeX script")

    parser.add_argument(
        "yaml_filename", nargs='?',
        metavar="quiz.yaml", type=str, 
        help = "path to the quiz in a yaml format")
   
    parser.add_argument(
        "-w", "--watch", 
        help="continuously compiles the document on file change",
        action="store_true")
    
    default_config_dir = appdirs.user_config_dir(
        appname="bbquiz", appauthor='frcs')
    
    parser.add_argument(
        "--config", 
        metavar="CONFIGFILE",  
        help=f"user config file. Default location is {default_config_dir}")

    parser.add_argument(
        "--build",
        help="compiles all targets and run all post-compilation commands",
        action="store_true")
    
    parser.add_argument(
        "--zsh",
        help="A helper command used for exporting the "
        "command completion code in zsh",
        action="store_true")

    parser.add_argument(
        "--fish",
        help="A helper command used for exporting the "
        "command completion code in fish",
        action="store_true")
    
    parser.add_argument(
        '-v', '--version', action='version', version=version("bbquiz"))
    
    parser.add_argument(
        '--debug',
        help="Print lots of debugging statements",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING)

    parser.add_argument(
        '--verbose',
        help="set verbose on",
        action="store_const",
        dest="loglevel",
        const=logging.INFO)
    
    args = parser.parse_args()
    
    FORMAT = "%(message)s"
    logging.basicConfig(
        level=args.loglevel,
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler()]
    )
    
    if args.zsh:
        print(bbquiz.shellcompletion.zsh())
        return

    if args.fish:
        print(bbquiz.shellcompletion.fish())
        return

    # if args.bash:
    #     print(bbquiz.shellcompletion.bash())
    #     return

    
    if not args.yaml_filename:
        parser.error("quiz.yaml is required")
        
    if args.watch:
        compile(args)
        compile_on_change(args)
    else:
        compile(args)


        
