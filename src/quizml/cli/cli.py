#!/usr/bin/python

import logging
import argparse
import appdirs
import pathlib
import os
import sys

from rich.traceback import install
install(show_locals=False)
#from rich import print          
from rich_argparse import *
from rich.logging import RichHandler
from rich import print

from importlib.metadata import version

from ..exceptions import QuizMLError


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
        "otherfiles", nargs='*', 
        type=str, 
        help = "other yaml files (only used with diff command)")
    
    parser.add_argument(
        "-w", "--watch", 
        help="continuously compiles the document on file change",
        action="store_true")
    
    default_config_dir = appdirs.user_config_dir(
        appname="quizml", appauthor='frcs')

    parser.add_argument(
        "-t", "--target",
        action='append',
        type=str, #argparse.FileType('r'),
        help = "target names (e.g. 'pdf', 'html-preview')")

    parser.add_argument(
        '--target-list',
        help="list all targets in config file",
        action="store_true")

    parser.add_argument(
        '--init-local',
        help="create a local directory 'quizml-templates' with all config files",
        action="store_true")

    parser.add_argument(
        '--init-user',
        help="create the user app directory with all its config files",
        action="store_true")
    
    parser.add_argument(
        "--config", 
        metavar="CONFIGFILE",  
        help=f"user config file. Default location is {default_config_dir}")
   
    parser.add_argument(
        "--build",
        help="compiles all targets and run all post-compilation commands",
        action="store_true")

    parser.add_argument(
        "--diff",
        help="compares questions from first yaml file to rest of files",
        action="store_true")

    parser.add_argument(
        "-C", "--cleanup",
        help="deletes build artefacts from all yaml files in dir",
        action="store_true")
    
    parser.add_argument(
        "--info",
        help="print configuration info and paths as json",
        action="store_true")

    parser.add_argument(
        "--shell-completion",
        choices=['bash', 'zsh', 'fish'],
        help="print shell completion script for the specified shell"
    )

    parser.add_argument(
        '-v', '--version', action='version', version=version("quizml"))
    
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

    parser.add_argument(
        '--quiet',
        help="turn off info statements",
        action="store_true")
    
    args = parser.parse_args()

    try:
        logging.basicConfig(
            force=True,
            level=args.loglevel,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
        )

        if args.target_list:
            import quizml.cli.ui
            quizml.cli.ui.print_target_list(args)
            return

        if args.info:
            import json
            import quizml.cli.filelocator
            
            try:
                config_file = quizml.cli.filelocator.locate.path('quizml.cfg')
            except FileNotFoundError:
                config_file = "not found"

            info = {
                "version": version("quizml"),
                "cwd": quizml.cli.filelocator.locate.cw_dir,
                "local_templates": quizml.cli.filelocator.locate.local_template_dir,
                "user_config_dir": quizml.cli.filelocator.locate.app_dir,
                "user_templates": quizml.cli.filelocator.locate.user_template_dir,
                "package_templates": quizml.cli.filelocator.locate.pkg_template_dir,
                "search_paths": quizml.cli.filelocator.locate.dirlist,
                "config_file": config_file
            }
            sys.stdout.write(json.dumps(info, indent=4) + '\n')
            return

        if args.shell_completion:
            import quizml.cli.shellcompletion
            completion_func = getattr(quizml.cli.shellcompletion, args.shell_completion)
            sys.stdout.write(completion_func(parser) + '\n')
            return

        if args.cleanup:
            import quizml.cli.cleanup
            quizml.cli.cleanup.cleanup_yaml_files()
            return

        if args.init_user:
            import quizml.cli.init
            quizml.cli.init.init_user()
            return

        if args.init_local:
            import quizml.cli.init
            quizml.cli.init.init_local()
            return
        
        if not args.yaml_filename:
            parser.error("a yaml file is required")

        if args.diff:
            import quizml.cli.diff
            quizml.cli.diff.diff(args)
            return
        
        if args.otherfiles:
            parser.error("only one yaml file is required")
        
        import quizml.cli.compile
        if args.watch:
            quizml.cli.compile.compile(args)
            quizml.cli.compile.compile_on_change(args)
        else:
            quizml.cli.compile.compile(args)

    except QuizMLError as e:
        print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
