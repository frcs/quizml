"""CLI command handler for quiz compilation and watch mode."""

import logging
import os
import threading
from time import sleep

from rich import print
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from quizml.builder.scheduler import (
    compile_cmd_target as _builder_cmd_target,
    compile_render_target as _builder_render_target,
)
from quizml.cli.config import get_config, get_target_list
from quizml.cli.errorhandler import print_error
from quizml.cli.livereload import (
    get_livereload_port,
    start_livereload_server,
    update_timestamp,
)
from quizml.cli.ui import (
    add_hyperlinks,
    print_quiet_ouputs,
    print_stats_table,
    print_table_ouputs,
)
from quizml.exceptions import (
    LatexEqError,
    MarkdownError,
    QuizMLConfigError,
    QuizMLError,
)
from quizml.filelocator import locate
from quizml.quizmlyaml import QuizMLYamlSyntaxError, load
from quizml.transcoder import MarkdownTranscoder


def compile_cmd_target(target):
    """Executes command line scripts for post-compilation build targets."""
    success, err_msg = _builder_cmd_target(target)
    if not success and err_msg:
        print_error(err_msg, title="Failed to build command")
    return success


def compile_target(target, transcoder, extra_context=None):
    """Transcodes and renders one target template."""
    success, err_msg = _builder_render_target(target, transcoder, extra_context)
    if not success and err_msg:
        print_error(err_msg, title="Target Render Error")
    return success


def compile(args):
    """Compiles the targets of a YAML quiz file."""
    try:
        config = get_config(args)
    except QuizMLConfigError as err:
        print_error(str(err), title="QuizML Config Error")
        return

    try:
        schema_path = locate.path(config["schema_path"])
    except FileNotFoundError:
        print_error(
            f"Schema file {config['schema_path']} not found, check the config file.",
            title="Schema Error",
        )
        return

    try:
        yaml_data, schema = load(
            args.yaml_filename, validate=True, schema_path=schema_path
        )
    except (QuizMLYamlSyntaxError, FileNotFoundError) as err:
        print_error(str(err), title="QuizMLYaml Syntax Error")
        return

    if logging.DEBUG:
        logging.debug(yaml_data)

    try:
        base_dir = os.path.dirname(os.path.abspath(args.yaml_filename))
        transcoder = MarkdownTranscoder(yaml_data, schema, base_dir=base_dir)
    except (LatexEqError, MarkdownError, FileNotFoundError) as err:
        print_error(str(err), title="Error")
        return

    if not args.quiet:
        print_stats_table(yaml_data, config)

    try:
        target_list = get_target_list(args, config, yaml_data)
    except FileNotFoundError as err:
        print_error(str(err), title="Template NotFoundError")
        return

    extra_context = {}
    if args.watch:
        start_livereload_server()
        port = get_livereload_port()
        if port:
            extra_context["livereload_port"] = port

    targets_output = []
    targets_quiet_output = []
    success_list = {}

    for target in target_list:
        is_build_cmd = "build_cmd" in target
        is_targeted = bool(args.target)

        if is_build_cmd and not (args.build or is_targeted):
            continue

        if is_build_cmd and (args.build or is_targeted):
            if ("dep" not in target) or (
                "dep" in target and success_list.get(target["dep"], False)
            ):
                success = compile_cmd_target(target)
            else:
                success = False

        if "template" in target:
            success = compile_target(target, transcoder, extra_context)

        success_list[target["name"]] = success

        targets_output.append(
            [
                target["descr"],
                add_hyperlinks(target["descr_cmd"], target["out"]),
                "" if success else "[FAIL]",
            ]
        )

        targets_quiet_output.append(
            [add_hyperlinks(target["out"], target["out"]), "" if success else "[FAIL]"]
        )

        if not success:
            break

    update_timestamp()

    if args.quiet:
        print_quiet_ouputs(targets_quiet_output)
    else:
        print_table_ouputs(targets_output)


def compile_on_change(args):
    """Watches input YAML file on disk and recompiles targets on change."""
    waitingtxt = "\n...waiting for a file change to re-compile the document...\n "
    print(waitingtxt)

    full_yaml_path = os.path.abspath(args.yaml_filename)
    rebuild_event = threading.Event()

    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if os.path.abspath(event.src_path) == full_yaml_path:
                rebuild_event.set()

        def on_moved(self, event):
            if os.path.abspath(event.dest_path) == full_yaml_path:
                rebuild_event.set()

    observer = Observer()
    observer.schedule(Handler(), ".")
    observer.start()

    try:
        while True:
            if rebuild_event.wait(timeout=0.5):
                rebuild_event.clear()
                sleep(0.1)
                rebuild_event.clear()

                print("[bold yellow]Change detected, re-compiling...[/bold yellow]")
                compile(args)
                print(waitingtxt)

    except KeyboardInterrupt:
        print("[bold red]Stopping watch mode...[/bold red]")
        observer.stop()

    observer.join()
