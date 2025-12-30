import os
import shlex
import subprocess
import logging
import threading
import pathlib
from time import sleep

from rich import print
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from quizml.cli.errorhandler import print_error
import quizml.cli.filelocator as filelocator

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

# Imported from refactored modules
from quizml.cli.config import get_config, get_target_list
from quizml.cli.ui import (
    print_stats_table,
    print_table_ouputs,
    print_quiet_ouputs,
    add_hyperlinks
)
from quizml.cli.livereload import (
    start_livereload_server,
    get_livereload_port,
    update_timestamp
)

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
        port = get_livereload_port()
        if port:
            extra_context['livereload_port'] = port

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
    update_timestamp()

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