#!/usr/bin/python

import logging
import argparse
import appdirs
import pathlib

from rich.traceback import install
install(show_locals=False)
from rich import print
from rich_argparse import *
from rich.logging import RichHandler

from importlib.metadata import version

import bbquiz.cli.diff
import bbquiz.cli.shellcompletion
import bbquiz.cli.compile

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
        type=str, #argparse.FileType('r'),
        help = "other yaml files [when using diff]")
    
    parser.add_argument(
        "-w", "--watch", 
        help="continuously compiles the document on file change",
        action="store_true")
    
    default_config_dir = appdirs.user_config_dir(
        appname="bbquiz", appauthor='frcs')

    parser.add_argument(
        "--target",
        action='append',
        type=str, #argparse.FileType('r'),
        help = "target names (e.g. 'pdf', 'html-preview')")
    
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
        "--bash",
        help="A helper command used for exporting the "
        "command completion code in bash",
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

    parser.add_argument(
        '--quiet',
        help="turn off info statements",
        action="store_true")

    parser.add_argument(
        '--target-list',
        help="list all targets in config file",
        action="store_true")
    
    args = parser.parse_args()


    logging.basicConfig(
        level=args.loglevel,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()]
    )

    if args.target_list:
        bbquiz.cli.compile.print_target_list(args)
        return
    
    if args.zsh:
        print(bbquiz.cli.shellcompletion.zsh())
        return

    if args.fish:
        print(bbquiz.cli.shellcompletion.fish())
        return
    
    if args.bash:
        print(bbquiz.cli.shellcompletion.bash())
        return
    
    if not args.yaml_filename:
        parser.error("a yaml file is required")

    if args.diff:
        bbquiz.cli.diff.diff(args)
        return
    
    if args.otherfiles:
        parser.error("only one yaml file is required")
    
    if args.watch:
        bbquiz.cli.compile.compile(args)
        bbquiz.cli.compile.compile_on_change(args)
    else:
        bbquiz.cli.compile.compile(args)
