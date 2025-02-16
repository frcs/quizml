import os
import sys
import yaml
import argparse
import subprocess
import shlex

import logging

from rich import print
from rich_argparse import *
from rich.panel import Panel
from rich.table import Table
from rich.table import box
from rich.console import Console

from time import sleep
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from string import Template

from bbquiz.bbyaml.loader import load
from bbquiz.bbyaml.stats import get_stats
from bbquiz.bbyaml.loader import BBYamlSyntaxError
import bbquiz.markdown.markdown as md
from bbquiz.markdown.exceptions import MarkdownError, LatexEqError
from bbquiz.render import to_jinja
from bbquiz.render.to_jinja import Jinja2SyntaxError

import bbquiz.cli.filelocator as filelocator

import pathlib

class BBQuizConfigError(Exception):
    pass



def get_config(args):
    """
    returns the yaml data of the config file
    """

    if args.config:
        config_file = os.path.realpath(os.path.expanduser(args.config))
    else:
        config_file = filelocator.locate.path('bbquiz.cfg')
   
    logging.info(f"using config file:{config_file}")
    
    try:
        with open(config_file) as f:            
            config = yaml.load(f, Loader=yaml.FullLoader)
    except yaml.YAMLError as err:
        s = f"Something went wrong while parsing the config file at:\n {config_file}\n\n {str(err)}"
        raise BBQuizConfigError(s)

    config['yaml_filename'] = args.yaml_filename
    
    return config
    

def print_target_list(args):
    try:
        config = get_config(args)
    except BBQuizConfigError as err:
        print(Panel(str(err),
                    title="BBQuiz Config Error",
                    border_style="red"))
        return

    table = Table(box=box.SIMPLE,
                  collapse_padding=True,
                  show_footer=False,
                  show_header=False)
    
    table.add_column("Name", no_wrap=True, justify="left")
    table.add_column("Descr", no_wrap=True, justify="left")
   
    for t in config['targets']:
        table.add_row(t['name'], t['descr'])
       
    print(table)
    
    


def get_required_target_names_set(name, targets):
    """resolves the set of the names of the required targets
    """
    if not name:
        return {}
    
    if isinstance(name, list):
        input_set = set(name)
    else:
        input_set = {name}
    required_set = input_set
    for target in targets:
        if (target.get('name', '') in input_set) and ('dep' in target):
            dep_set = get_required_target_names_set(
                target['dep'], targets)
            required_set = required_set.union(dep_set)
            
    return required_set


def get_target_list(args, config, yaml_data):
    """
    gets the list of target templates from config['targets'] and
      * resolves the absolute path of each template
      * also resolves $inputbasename 
    """
    
    (basename, _) = os.path.splitext(config['yaml_filename'])
    
    subs = {'inputbasename': basename}
    filenames_to_resolve = ['template', 'html_css', 'html_pre', 'latex_pre']
    files_to_read_now = ['html_css', 'html_pre', 'latex_pre']

    # if CLI provided specific list of required target names
    # we compile a list of all the required target names
    required_target_names_set = get_required_target_names_set(
        args.target, config['targets'])
   
    if args.target:
        logging.info(f"requested target list:{args.target}")
        logging.info(f"required target list:{required_target_names_set}")

    target_list = []
    
    for t in config['targets']:
        t_name = t.get('name', '')
        dep_name = t.get('dep', '')
        
        if (required_target_names_set and t_name not in required_target_names_set):
            continue

        target = {}

        # resolves $inputbasename
        for key, val in t.items():
            target[key] = Template(val).substitute(subs)

        # resolves relative path for all files
        for key in filenames_to_resolve:        
            if key in target:
                target[key] = filelocator.locate.path(t[key])
                logging.info(f"'{target['descr']}:{key}'"
                             f" expands as '{target[key]}'")

        # replaces values with actual file content for some keys
        for key in files_to_read_now:
            if key in target:
                file_path = target[key]
                contents = pathlib.Path(file_path).read_text()
                target[key] = contents
        
        # add target to list
        target_list.append(target)

        # add preamble key if defined in the bbyaml header
        if 'fmt' in target:
            target['user_pre'] = yaml_data['header'].get('pre_latexpreamble', '')

    return target_list

def add_hyperlinks(descr_str, filename):
    path = os.path.abspath(f"./{filename}")
    uri = f"[link=file://{path}]{filename}[/link]"
    return  descr_str.replace(filename, uri)


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

    table = Table(box=box.SIMPLE,
                  collapse_padding=True,
                  show_footer=True)
    
    table.add_column(
        "Q", f"{stats['nb questions']}",
        min_width=3,
        no_wrap=True,
        justify="right")
    table.add_column(
        "Type", "--",
        min_width=2,        
        no_wrap=True,
        justify="center")
    table.add_column(
        "Marks", f"{stats['total marks']:3.1f}",
        min_width=3,                
        no_wrap=True,
        justify="right")
    table.add_column(
        "#", "-",
        no_wrap=True,
        justify="right")
    table.add_column(
        "Exp", f"{stats['expected mark']:2.1f}" + "%",
        no_wrap=True,
        justify="right")
    table.add_column(
        "Question Statement",
        max_width=60,
        no_wrap=True,
        justify="left",
        overflow="ellipsis")
    
    for i, q in enumerate(stats["questions"]):
        table.add_row(f"{i+1}",
                      q["type"],
                      f"{q['marks']:2.1f}",
                      f"{q['choices']}",
                      f"{q['EM']:3.1f}",
                      q["excerpt"])

    console.print(table)


def print_table_ouputs(targets_output):
    # print to terminal a table of all targets outputs.
    table = Table(box=box.SIMPLE,
                  collapse_padding=True,
                  show_footer=False,
                  show_header=False)
    
    table.add_column("Descr", no_wrap=True, justify="left")
    table.add_column("Cmd", no_wrap=True, justify="left")
    table.add_column("Status", no_wrap=True, justify="left")

    for row in targets_output:
        if row[2]=="[FAIL]":
            table.add_row(*row, style="red")
        elif row[2]=="":
            table.add_row(*row)
       
    print(Panel(table,
                title="Target Ouputs",
                border_style="magenta"))
   

    
def compile_cmd_target(target):
    """execute command line scripts of the post compilation targets.

    """
    command = shlex.split(target["build_cmd"])
    
    try:
        output = subprocess.check_output(command)
        return True
    
    except subprocess.CalledProcessError as e:
        print(Panel(e.output.decode(),
                    title = f"\n failed to build command ",
                    border_style="red"))
        
        return False    
    

    
def compile_target(target, bbyamltranscoder):

    try:
        yaml_transcoded = bbyamltranscoder.transcode_target(target)
        rendered_doc = to_jinja.render(yaml_transcoded,
                                       target['template'])
        pathlib.Path(target['out']).write_text(rendered_doc)
        success = True

    except LatexEqError as err:
        print(Panel(str(err),
                    title="Latex Error",
                    border_style="red"))
        success = False
    except MarkdownError as err:
        print(Panel(str(err),
                    title="Markdown Error",
                    border_style="red"))
        success = False
    except FileNotFoundError as err:
        print(Panel(str(err),
                    title="FileNotFoundError Error",
                    border_style="red"))
        success = False
    except Jinja2SyntaxError as err:
        print(Panel((f"\n did not generate {out_filename} " +
                     "because of template errors ! \n " + str(err)),
                    title='Jinja Template Error',
                    border_style="red"))
        success = False

    return success
        
  

def compile(args):
    """compiles the targets of a bbyaml file

    """

    # read config file
    try:
        config = get_config(args)
    except BBQuizConfigError as err:
        print(Panel(str(err),
                    title="BBQuiz Config Error",
                    border_style="red"))
        return
        

    # load BBYaml file

    yaml_filename = args.yaml_filename
    
    if not os.path.exists(yaml_filename):
        print(Panel("File " + yaml_filename + " not found",
                    title="Error",
                    border_style="red"))
        return
    try:
        yaml_data = load(yaml_filename, schema=True)
    except BBYamlSyntaxError as err:
        print(Panel(str(err),
                    title="BByaml Syntax Error",
                    border_style="red"))
        return
        
    # load all markdown entries into a list 
    # and build dictionaries of their HTML and LaTeX translations
    
    try:
        bbyamltranscoder = md.BBYAMLMarkdownTranscoder(yaml_data)
    except LatexEqError as err:
        print(Panel(str(err),
                    title="Latex Error",
                    border_style="red"))
        return
    except MarkdownError as err:
        print(Panel(str(err),
                    title="Markdown Error",
                    border_style="red"))
        return
    except FileNotFoundError as err:
        print(Panel(str(err),
                    title="FileNotFoundError Error",
                    border_style="red"))
        return
       
    # diplay stats about the questions
    if not args.quiet:
        print_stats_table(get_stats(yaml_data))
   
    # get target list from config file
    try:
        target_list = get_target_list(args, config, yaml_data)        
    except FileNotFoundError as err:
        print(Panel(str(err),
                    title="FileNotFoundError Error",
                    border_style="red"))
        return
    
    # sets up list of the output for each build
    targets_output = []

    # if args.build:
    #     print("building post commands")
    success_list = {}
    
    for i, target in enumerate(target_list):

        # skipping build target if build option is not on
        if ("build_cmd" in target) and not (args.build or args.target):
            continue

        # a build target (eg. compile pdf of generated latex) a build
        # target only requires the execution of an external command,
        # ie. no python code required
        #
        if ("build_cmd" in target) and (args.build or args.target):
            # need to check if there is a dependency,
            # and if this dependency compiled successfully
            
            if (("dep" not in target) or
                ("dep" in target and success_list[target['dep']])):
                success = compile_cmd_target(target)
            else:
                success = False

        # a template task that needs to be rendered
        if ("template" in target):
            success = compile_target(target, bbyamltranscoder)
            
        success_list[target['name']] = success
        
        targets_output.append(
            [ target['descr'] ,
              add_hyperlinks(target["descr_cmd"], target["out"]),
              "" if success else "[FAIL]" ])
            
    # diplay stats about the outputs
    if not args.quiet:
        print_table_ouputs(targets_output)
    

def compile_on_change(args):
    """compiles the targets if input bbyaml file has changed on disk

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
