import os
import sys
import yaml
import argparse
import subprocess
import shlex

import logging
import threading
import http.server
import socketserver
import json
import socket
import time

from rich import print
from rich_argparse import *
from rich.table import Table
from rich.table import box
from rich.console import Console
from rich.panel import Panel
from rich.padding import Padding

from quizml.cli.errorhandler import print_error

from time import sleep
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from string import Template

from quizml.loader import load
from quizml.loader import QuizMLYamlSyntaxError
import quizml.markdown.markdown as md
from quizml import renderer
from quizml.exceptions import (
    QuizMLError,
    QuizMLConfigError,
    MarkdownError,
    LatexEqError,
    Jinja2SyntaxError,
)

import quizml.cli.filelocator as filelocator

import pathlib

from rich.markdown import Markdown, TableElement
from rich import box

class CustomTableElement(TableElement):
    def __rich_console__(self, console, options):
        for table in super().__rich_console__(console, options):
            # Check if the table has visible headers
            has_headers = any(col.header.plain.strip() for col in table.columns)
            
            if has_headers:
                # Main Question Table
                table.show_header = True
                table.box = box.SIMPLE_HEAVY # Adds the rule and header structure
                table.padding = (0, 0, 0, 1) # User preferred padding
                table.show_edge = False # Hide bottom line
            else:
                # Summary Table (frameless alignment)
                table.show_header = False
                table.box = None
                table.padding = (0, 0, 0, 1) # Align left, spacing between cols
                
            yield table

Markdown.elements["table_open"] = CustomTableElement

# Global state for the LiveReload server
LIVERELOAD_PORT = None
LIVERELOAD_TIMESTAMP = 0.0
SERVER_THREAD = None

class LiveReloadHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Silence logs

    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            data = json.dumps({'timestamp': LIVERELOAD_TIMESTAMP})
            self.wfile.write(data.encode())
        else:
            self.send_error(404)

def start_livereload_server():
    global LIVERELOAD_PORT, SERVER_THREAD
    if SERVER_THREAD is not None:
        return

    # Find a free port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            LIVERELOAD_PORT = s.getsockname()[1]

        def run_server():
            # Allow address reuse to prevent issues if we restart quickly
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("", LIVERELOAD_PORT), LiveReloadHandler) as httpd:
                httpd.serve_forever()

        SERVER_THREAD = threading.Thread(target=run_server, daemon=True)
        SERVER_THREAD.start()
        # print(f"[dim]LiveReload server started on port {LIVERELOAD_PORT}[/dim]")
    except Exception as e:
        print_error(f"Failed to start LiveReload server: {e}", title="Warning")


def get_config(args):
    """
    returns the yaml data of the config file
    """

    if args.config:
        config_file = os.path.realpath(os.path.expanduser(args.config))
    else:
        try:
            config_file = filelocator.locate.path('quizml.cfg')
        except FileNotFoundError:
            raise QuizMLConfigError("Could not find config file quizml.cfg")
   
    logging.info(f"using config file:{config_file}")
    
    try:
        with open(config_file) as f:            
            config = yaml.load(f, Loader=yaml.FullLoader)
    except yaml.YAMLError as err:
        s = f"Something went wrong while parsing the config file at:\n {config_file}\n\n {str(err)}"
        raise QuizMLConfigError(s)

    config['yaml_filename'] = args.yaml_filename
    
    return config
    

def print_target_list(args):
    try:
        config = get_config(args)
    except QuizMLConfigError as err:
        print_error(str(err), title="QuizML Config Error")
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

        # add preamble key if defined in the QuizMLYaml header
        if 'fmt' in target:
            target['user_pre'] = yaml_data['header'].get('_latexpreamble', '')

    return target_list

def add_hyperlinks(descr_str, filename):
    path = os.path.abspath(f"./{filename}")
    uri = f"[link=file://{path}]{filename}[/link]"
    return  descr_str.replace(filename, uri)


def print_stats_table(quiz, config):
    """
    prints a table with information about each question, using a user-defined jinja template.
    """
    
    try:
        template_name = config.get('stats_template', 'stats.jinja')
        template_path = filelocator.locate.path(template_name)
    except FileNotFoundError:
        print_error(f"Stats template '{template_name}' not found", title="Error")
        return

    try:
        #        rendered = renderer.render_template({'quiz': quiz}, template_path)
        rendered = renderer.render_template(quiz, template_path)

        # Padding arguments: (top, right, bottom, left)
        text_to_print = Padding(Markdown(rendered), (0, 0, 1, 4))
        print(text_to_print)
    except Jinja2SyntaxError as err:
        print_error(str(err), title="Jinja Template Error")


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
   
def print_quiet_ouputs(targets_quiet_output):

    for row in targets_quiet_output:
        if row[1]=="[FAIL]":
            print("[bold red]x " + row[0] + "[/bold red]")
        elif row[1]=="":
            print("[bold green]o[/bold green] " + row[0])
       
    
def compile_cmd_target(target):
    """execute command line scripts of the post compilation targets.

    """
    command = shlex.split(target["build_cmd"])
    
    try:
        output = subprocess.check_output(command)
        return True
    
    except subprocess.CalledProcessError as e:
        print_error(e.output.decode(), title="Failed to build command")
        
        return False    
    

    
def compile_target(target, transcoder, extra_context=None):
    """compiles one target

    """

    try:
        yaml_transcoded = transcoder.transcode_target(target)
        rendered_doc = renderer.render(yaml_transcoded,
                                       target['template'],
                                       extra_context)
        
        if isinstance(rendered_doc, bytes):
            pathlib.Path(target['out']).write_bytes(rendered_doc)
        else:
            pathlib.Path(target['out']).write_text(rendered_doc)
            
        success = True

    except LatexEqError as err:
        print_error(str(err), title="Latex Error")
        success = False
    except MarkdownError as err:
        print_error(str(err), title="Markdown Error")
        success = False
    except FileNotFoundError as err:
        print_error(str(err), title="FileNotFoundError Error")
        success = False
    except Jinja2SyntaxError as err:
        print_error(f"\n did not generate target because of template errors ! \n {err}",
                          title='Jinja Template Error')
        success = False
    except QuizMLError as err:
        print_error(str(err), title='QuizML Error')
        success = False
    except KeyboardInterrupt:
        print("[bold red] KeyboardInterrupt [/bold red]")
        success = False        
        
    return success


def compile(args):
    """compiles the targets of a yaml file

    """

    # read config file
    try:
        config = get_config(args)
    except QuizMLConfigError as err:
        print_error(str(err), title="QuizML Config Error")
        return

    # load Schema file
    try:
        schema_path = filelocator.locate.path(config["schema_path"])
    except FileNotFoundError as err:
        print_error("Schema file " + config["schema_path"] +
                          " not found, check the config file.",
                          title="Schema Error")
        return
    
    # load QuizMLYaml file
    try:
        yaml_data = load(args.yaml_filename, validate=True, schema_path=schema_path)
    except (QuizMLYamlSyntaxError, FileNotFoundError) as err:
        print_error(str(err), title="QuizMLYaml Syntax Error")
        return

    if logging.DEBUG:
        logging.debug(yaml_data)
    
    # load all markdown entries into a list
    # and build dictionaries of their HTML and LaTeX translations
    try:
        transcoder = md.MarkdownTranscoder(yaml_data)
    except (LatexEqError, MarkdownError, FileNotFoundError) as err:
        print_error(str(err), title="Error")
        return

    # diplay stats about the questions
    if not args.quiet:
        print_stats_table(yaml_data, config)

    # get target list from config file
    try:
        target_list = get_target_list(args, config, yaml_data)
    except FileNotFoundError as err:
        print_error(str(err), title="Template NotFoundError")
        return

    # Prepare LiveReload if watching
    extra_context = {}
    if args.watch:
        start_livereload_server()
        if LIVERELOAD_PORT:
            extra_context['livereload_port'] = LIVERELOAD_PORT

    # sets up list of the output for each build
    targets_output = []
    targets_quiet_output = []
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
                ("dep" in target and success_list.get(target['dep'], False))):
                success = compile_cmd_target(target)
            else:
                success = False

        # a template task that needs to be rendered
        if ("template" in target):
            success = compile_target(target, transcoder, extra_context)
            
        success_list[target['name']] = success
        
        targets_output.append(
            [ target['descr'] ,
              add_hyperlinks(target["descr_cmd"], target["out"]),
              "" if success else "[FAIL]" ])

        targets_quiet_output.append(
            [ add_hyperlinks(target["out"], target["out"]),
              "" if success else "[FAIL]" ])

        if not success:
            break
        
    # Update timestamp for LiveReload clients
    global LIVERELOAD_TIMESTAMP
    LIVERELOAD_TIMESTAMP = time.time()

    # diplay stats about the outputs
    if not args.quiet:
        print_table_ouputs(targets_output)

    if args.quiet:
        print_quiet_ouputs(targets_quiet_output)
        

def compile_on_change(args):
    """compiles the targets if input QuizMLYaml file has changed on disk

    """

    waitingtxt = ("\n...waiting for a file change "
                  "to re-compile the document...\n ")
    print(waitingtxt)
    
    full_yaml_path = os.path.abspath(args.yaml_filename)
    rebuild_event = threading.Event()

    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if os.path.abspath(event.src_path) == full_yaml_path:
                rebuild_event.set()
        
        def on_moved(self, event):
            # Support for editors that use atomic saves (write to tmp -> rename)
            if os.path.abspath(event.dest_path) == full_yaml_path:
                rebuild_event.set()
               
    observer = Observer()
    observer.schedule(Handler(), ".") # watch the local directory
    observer.start()

    try:
        while True:
            # Wait for the event, checking every 0.5s to allow KeyboardInterrupt
            if rebuild_event.wait(timeout=0.5):
                rebuild_event.clear()
                
                # Debounce: wait a brief moment for file operations to settle
                sleep(0.1)
                # Clear any events that occurred during the sleep
                rebuild_event.clear()

                print("[bold yellow]Change detected, re-compiling...[/bold yellow]")
                compile(args)
                print(waitingtxt)

    except KeyboardInterrupt:
        print("[bold red]Stopping watch mode...[/bold red]")
        observer.stop()

    observer.join()
